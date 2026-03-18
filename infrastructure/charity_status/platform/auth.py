from __future__ import annotations

import json
from typing import Any

from charity_status.api import normalize_route_key
from charity_status.auth import (
    DEFAULT_OAUTH_TOKEN_TTL_SECONDS,
    DEFAULT_PLAN_LIMITS,
    InMemoryUsageStore,
    StaticApiKeyStore,
    StaticOAuthClientStore,
    StaticOAuthTokenStore,
    authenticate_api_key,
    authenticate_bearer_token,
    authenticate_oauth_client_credentials,
    enforce_quota_and_scope,
)
from charity_status.auth.models import AuthenticatedPrincipal
from charity_status.billing import EntitlementService
from charity_status.billing.service import DEFAULT_PLANS, check_quota_and_calculate, monthly_period_for
from charity_status.core.models import AuthContext


class ApiKeyAuthContextProvider:
    def __init__(
        self,
        store: StaticApiKeyStore,
        plan_limits: dict[str, int] | None = None,
        entitlement_service: EntitlementService | None = None,
    ):
        self._store = store
        self._plan_limits = plan_limits or DEFAULT_PLAN_LIMITS
        self._entitlement_service = entitlement_service or EntitlementService()

    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        principal = authenticate_api_key(event.get("headers") or {}, self._store, self._plan_limits)
        context = _to_context(principal, self._entitlement_service)
        _attach_context(event, context)
        return context


class ApiKeyOrOAuthAuthContextProvider:
    def __init__(
        self,
        api_key_store: StaticApiKeyStore,
        oauth_token_store: StaticOAuthTokenStore | None = None,
        oauth_client_store: StaticOAuthClientStore | None = None,
        plan_limits: dict[str, int] | None = None,
        entitlement_service: EntitlementService | None = None,
    ):
        self._entitlement_service = entitlement_service or EntitlementService()
        self._api_key_provider = ApiKeyAuthContextProvider(
            api_key_store,
            plan_limits=plan_limits,
            entitlement_service=self._entitlement_service,
        )
        self._oauth_token_store = oauth_token_store
        self._oauth_client_store = oauth_client_store

    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        headers = event.get("headers") or {}
        auth_value = _get_header(headers, "authorization")
        if auth_value and str(auth_value).lower().startswith("bearer "):
            principal = authenticate_bearer_token(
                headers,
                token_store=self._oauth_token_store,
                client_store=self._oauth_client_store,
            )
            context = _to_context(principal, self._entitlement_service)
            _attach_context(event, context)
            return context
        return self._api_key_provider.extract_context(event)


class OAuthClientCredentialsService:
    def __init__(
        self,
        client_store: StaticOAuthClientStore,
        *,
        token_ttl_seconds: int = DEFAULT_OAUTH_TOKEN_TTL_SECONDS,
        entitlement_service: EntitlementService | None = None,
    ):
        self._client_store = client_store
        self._token_ttl_seconds = token_ttl_seconds
        self._entitlement_service = entitlement_service or EntitlementService()

    def issue_token(self, client_id: str, client_secret: str) -> tuple[AuthContext, dict[str, Any]]:
        principal = authenticate_oauth_client_credentials(client_id, client_secret, self._client_store)
        from charity_status.auth.oauth import issue_client_access_token

        token_payload = issue_client_access_token(
            principal,
            self._client_store,
            ttl_seconds=self._token_ttl_seconds,
        )
        return _to_context(principal, self._entitlement_service), token_payload


class ApiKeyQuotaMeteringHook:
    def __init__(self, usage_store: InMemoryUsageStore, entitlement_service: EntitlementService | None = None):
        self._usage_store = usage_store
        self._entitlement_service = entitlement_service or EntitlementService()

    def on_request(self, auth_context: AuthContext, route_key: str) -> None:
        if not auth_context.account_id or not auth_context.plan:
            return
        principal = _from_context(auth_context)
        month_key, _, _ = enforce_quota_and_scope(principal, route_key, self._usage_store, self._entitlement_service)
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
        entitlement = auth_context.entitlements or DEFAULT_PLANS.get(str(auth_context.plan), DEFAULT_PLANS["free"]).entitlements
        current = self._usage_store.get_usage(str(auth_context.account_id), month_key)
        decision = check_quota_and_calculate(plan=entitlement, used_units=current, consumed_units=billable_units, period_key=month_key)
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
                plan_id=str(item.get("plan_id") or "free"),
                rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
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
                plan_id=str(item.get("plan_id") or "free"),
                rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
            )
        )
    return StaticOAuthTokenStore(records)


def load_oauth_client_store(raw_json: str) -> StaticOAuthClientStore:
    if not raw_json.strip():
        return StaticOAuthClientStore([])
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("OAUTH_CLIENT_RECORDS_JSON must be a JSON array")
    records = []
    from charity_status.auth.oauth import StoredOAuthClientRecord

    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            StoredOAuthClientRecord(
                client_id=str(item.get("client_id") or ""),
                client_secret_hash=str(item.get("client_secret_hash") or ""),
                account_id=str(item.get("account_id") or ""),
                workspace_id=str(item.get("workspace_id") or ""),
                scopes=tuple(item.get("scopes") or ()),
                revoked=bool(item.get("revoked", False)),
                plan_id=str(item.get("plan_id") or "free"),
                rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
            )
        )
    return StaticOAuthClientStore(records)


def _to_context(principal: AuthenticatedPrincipal, entitlement_service: EntitlementService | None = None) -> AuthContext:
    service = entitlement_service or EntitlementService()
    resolved = service.resolve(
        account_id=principal.account_id,
        fallback_plan_code=principal.plan.plan_id,
        subscription=principal.subscription,
    )
    subject = f"{principal.auth_method}:{principal.credential_id}"
    return AuthContext(
        account_id=principal.account_id,
        credential_id=principal.credential_id,
        auth_method=principal.auth_method,
        plan=resolved.subscription.plan_code,
        scopes=principal.scopes,
        rate_limit_profile=principal.rate_limit_profile,
        workspace_id=principal.workspace_id,
        subject=subject,
        subscription=resolved.subscription,
        entitlements=resolved.entitlements,
        metadata={
            "principal_type": principal.auth_method,
            "subscription_status": resolved.subscription.status,
            "requests_per_minute": str(resolved.entitlements.requests_per_minute),
            "monthly_request_limit": str(resolved.entitlements.monthly_request_limit),
        },
    )


def _from_context(auth_context: AuthContext) -> AuthenticatedPrincipal:
    from charity_status.auth.models import AuthenticatedPrincipal, ApiPlan

    entitlements = auth_context.entitlements or DEFAULT_PLANS.get(str(auth_context.plan), DEFAULT_PLANS["free"]).entitlements
    return AuthenticatedPrincipal(
        credential_id=str(auth_context.credential_id or ""),
        account_id=str(auth_context.account_id or ""),
        workspace_id=str(auth_context.workspace_id or ""),
        plan=ApiPlan(
            plan_id=str(auth_context.plan),
            monthly_limit=entitlements.monthly_request_limit,
            entitlements=entitlements,
        ),
        scopes=auth_context.scopes,
        auth_method=str(auth_context.auth_method or "anonymous"),
        rate_limit_profile=str(auth_context.rate_limit_profile or auth_context.plan or "free"),
        subscription=auth_context.subscription,
        entitlements=entitlements,
    )


def _attach_context(event: dict[str, Any], auth_context: AuthContext) -> None:
    if isinstance(event, dict):
        event["_auth_context"] = auth_context


def _billable_units(route_key: str, metadata: dict[str, str]) -> int:
    route_key = normalize_route_key(route_key)
    if route_key == "POST /v1/verify/batch":
        total = metadata.get("batch_items_count")
        if total and str(total).isdigit():
            return max(1, int(total))
    if route_key.startswith("GET /v1/nonprofits/{ein}/sources"):
        return 2
    return 1


def _get_header(headers: dict[str, Any], name: str) -> str | None:
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None
