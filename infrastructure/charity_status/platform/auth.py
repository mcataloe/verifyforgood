from __future__ import annotations

import json
from typing import Any

from charity_status.auth import (
    DEFAULT_PLAN_LIMITS,
    InMemoryUsageStore,
    StaticApiKeyStore,
    StaticOAuthTokenStore,
    authenticate_api_key,
    authenticate_bearer_token,
    enforce_quota_and_scope,
)
from charity_status.auth.models import ApiKeyPrincipal, OAuthClientPrincipal
from charity_status.billing.service import DEFAULT_PLANS, check_quota_and_calculate, monthly_period_for
from charity_status.core.models import AuthContext


class ApiKeyAuthContextProvider:
    def __init__(self, store: StaticApiKeyStore, plan_limits: dict[str, int] | None = None):
        self._store = store
        self._plan_limits = plan_limits or DEFAULT_PLAN_LIMITS

    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        principal = authenticate_api_key(event.get("headers") or {}, self._store, self._plan_limits)
        return _to_context(principal)


class ApiKeyOrOAuthAuthContextProvider:
    def __init__(self, api_key_store: StaticApiKeyStore, oauth_store: StaticOAuthTokenStore, plan_limits: dict[str, int] | None = None):
        self._api_key_provider = ApiKeyAuthContextProvider(api_key_store, plan_limits=plan_limits)
        self._oauth_store = oauth_store

    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        headers = event.get("headers") or {}
        auth_value = _get_header(headers, "authorization")
        if auth_value and str(auth_value).lower().startswith("bearer "):
            principal = authenticate_bearer_token(headers, self._oauth_store)
            return _to_context(principal)
        return self._api_key_provider.extract_context(event)


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
        if not auth_context.account_id:
            return
        if status_code >= 500:
            return
        month_key = auth_context.metadata.get("quota_month") or monthly_period_for()
        if not month_key:
            return
        billable_units = _billable_units(route_key, auth_context.metadata)
        if billable_units <= 0:
            return
        plan = DEFAULT_PLANS.get(str(auth_context.plan_id), DEFAULT_PLANS["developer"])
        current = self._usage_store.get_usage(str(auth_context.account_id), month_key)
        decision = check_quota_and_calculate(plan=plan, used_units=current, consumed_units=billable_units, period_key=month_key)
        if decision.projected_usage > decision.limit_units:
            return
        for _ in range(billable_units):
            self._usage_store.increment(str(auth_context.account_id), month_key)


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


def load_oauth_token_store(raw_json: str) -> StaticOAuthTokenStore:
    if not raw_json.strip():
        return StaticOAuthTokenStore([])
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("OAUTH_TOKEN_RECORDS_JSON must be a JSON array")
    records = []
    from charity_status.auth.oauth import StoredOAuthTokenRecord

    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            StoredOAuthTokenRecord(
                client_id=str(item.get("client_id") or ""),
                token_hash=str(item.get("token_hash") or ""),
                account_id=str(item.get("account_id") or ""),
                workspace_id=str(item.get("workspace_id") or ""),
                scopes=tuple(item.get("scopes") or ()),
                revoked=bool(item.get("revoked", False)),
                plan_id=str(item.get("plan_id") or "developer"),
            )
        )
    return StaticOAuthTokenStore(records)


def _to_context(principal: ApiKeyPrincipal | OAuthClientPrincipal) -> AuthContext:
    principal_type = "oauth_client" if isinstance(principal, OAuthClientPrincipal) else "api_key"
    subject = f"oauth:{principal.client_id}" if isinstance(principal, OAuthClientPrincipal) else f"apikey:{principal.key_id}"
    api_key_id = None if isinstance(principal, OAuthClientPrincipal) else principal.key_id
    return AuthContext(
        subject=subject,
        scopes=principal.scopes,
        metadata={"principal_type": principal_type},
        account_id=principal.account_id,
        workspace_id=principal.workspace_id,
        api_key_id=api_key_id,
        plan_id=principal.plan.plan_id,
    )


def _from_context(auth_context: AuthContext) -> ApiKeyPrincipal:
    from charity_status.auth.models import ApiPlan

    return ApiKeyPrincipal(
        key_id=str(auth_context.api_key_id),
        account_id=str(auth_context.account_id),
        workspace_id=str(auth_context.workspace_id),
        plan=ApiPlan(
            plan_id=str(auth_context.plan_id),
            monthly_limit=DEFAULT_PLAN_LIMITS.get(str(auth_context.plan_id), 250),
            entitlements=DEFAULT_PLANS.get(str(auth_context.plan_id), DEFAULT_PLANS["developer"]).entitlements,
        ),
        scopes=auth_context.scopes,
    )


def _billable_units(route_key: str, metadata: dict[str, str]) -> int:
    if route_key == "POST /verify/batch":
        total = metadata.get("batch_items_count")
        if total and str(total).isdigit():
            return max(1, int(total))
    if route_key.startswith("GET /nonprofits/{ein}/sources"):
        return 2
    return 1


def _get_header(headers: dict[str, Any], name: str) -> str | None:
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None
