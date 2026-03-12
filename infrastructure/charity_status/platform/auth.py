from __future__ import annotations

import json
from typing import Any

from charity_status.auth import (
    DEFAULT_PLAN_LIMITS,
    InMemoryUsageStore,
    StaticApiKeyStore,
    authenticate_api_key,
    enforce_quota_and_scope,
)
from charity_status.auth.models import ApiKeyPrincipal
from charity_status.core.models import AuthContext


class ApiKeyAuthContextProvider:
    def __init__(self, store: StaticApiKeyStore, plan_limits: dict[str, int] | None = None):
        self._store = store
        self._plan_limits = plan_limits or DEFAULT_PLAN_LIMITS

    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        principal = authenticate_api_key(event.get("headers") or {}, self._store, self._plan_limits)
        return _to_context(principal)


class ApiKeyQuotaMeteringHook:
    def __init__(self, usage_store: InMemoryUsageStore):
        self._usage_store = usage_store

    def on_request(self, auth_context: AuthContext, route_key: str) -> None:
        if not auth_context.account_id or not auth_context.plan_id:
            return
        principal = _from_context(auth_context)
        month_key, _, _ = enforce_quota_and_scope(principal, route_key, self._usage_store)
        auth_context.metadata["quota_month"] = month_key

    def on_response(self, auth_context: AuthContext, route_key: str, status_code: int) -> None:
        del route_key
        if not auth_context.account_id:
            return
        if status_code >= 500:
            return
        month_key = auth_context.metadata.get("quota_month")
        if not month_key:
            return
        self._usage_store.increment(auth_context.account_id, month_key)


def load_api_key_store(raw_json: str) -> StaticApiKeyStore:
    if not raw_json.strip():
        return StaticApiKeyStore([])
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("API_KEY_RECORDS_JSON must be a JSON array")
    records = []
    from charity_status.auth.service import StoredApiKeyRecord

    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            StoredApiKeyRecord(
                key_id=str(item.get("key_id") or ""),
                secret_hash=str(item.get("secret_hash") or ""),
                account_id=str(item.get("account_id") or ""),
                workspace_id=str(item.get("workspace_id") or ""),
                scopes=tuple(item.get("scopes") or ()),
                revoked=bool(item.get("revoked", False)),
                plan_id=str(item.get("plan_id") or "developer"),
            )
        )
    return StaticApiKeyStore(records)


def _to_context(principal: ApiKeyPrincipal) -> AuthContext:
    return AuthContext(
        subject=f"apikey:{principal.key_id}",
        scopes=principal.scopes,
        metadata={"principal_type": "api_key"},
        account_id=principal.account_id,
        workspace_id=principal.workspace_id,
        api_key_id=principal.key_id,
        plan_id=principal.plan.plan_id,
    )


def _from_context(auth_context: AuthContext) -> ApiKeyPrincipal:
    from charity_status.auth.models import ApiPlan

    return ApiKeyPrincipal(
        key_id=str(auth_context.api_key_id),
        account_id=str(auth_context.account_id),
        workspace_id=str(auth_context.workspace_id),
        plan=ApiPlan(plan_id=str(auth_context.plan_id), monthly_limit=DEFAULT_PLAN_LIMITS.get(str(auth_context.plan_id), 250)),
        scopes=auth_context.scopes,
    )
