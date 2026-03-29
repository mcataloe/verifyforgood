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
    UsageStore,
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
        touch_last_used = getattr(self._store, "touch_last_used", None)
        if callable(touch_last_used):
            try:
                touch_last_used(principal.credential_id)
            except Exception:  # noqa: BLE001
                pass
        context = _to_context(principal, self._entitlement_service)
        get_organization_id = getattr(self._store, "get_organization_id", None)
        if callable(get_organization_id):
            try:
                organization_id = get_organization_id(principal.credential_id)
            except Exception:  # noqa: BLE001
                organization_id = None
            if organization_id:
                context.metadata["organization_id"] = str(organization_id)
                context.metadata["organization_api_key"] = "true"
                context.metadata["tenant_scoped_request"] = "true"
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
    def __init__(
        self,
        usage_store: UsageStore,
        entitlement_service: EntitlementService | None = None,
        billing_settings_resolver: Any | None = None,
        trial_lifecycle_service: Any | None = None,
        organization_usage_tracker: Any | None = None,
        organization_feature_service: Any | None = None,
    ):
        self._usage_store = usage_store
        self._entitlement_service = entitlement_service or EntitlementService()
        self._billing_settings_resolver = billing_settings_resolver
        self._trial_lifecycle_service = trial_lifecycle_service
        self._organization_usage_tracker = organization_usage_tracker
        self._organization_feature_service = organization_feature_service

    def on_request(self, auth_context: AuthContext, route_key: str) -> None:
        if not auth_context.account_id or not auth_context.plan:
            return
        normalized_route_key = normalize_route_key(route_key)
        updated_subscription = auth_context.subscription
        if self._trial_lifecycle_service is not None:
            updated_subscription = self._trial_lifecycle_service.maybe_activate_trial(
                account_id=str(auth_context.account_id),
                trigger_event=normalized_route_key,
            ) or updated_subscription
        resolved = self._entitlement_service.resolve(
            account_id=str(auth_context.account_id),
            fallback_plan_code=str(auth_context.plan or "free"),
            subscription=updated_subscription,
        )
        auth_context.subscription = resolved.subscription
        auth_context.entitlements = resolved.entitlements
        auth_context.plan = resolved.entitlements.plan_code
        auth_context.metadata["billing_plan_code"] = resolved.subscription.plan_code
        auth_context.metadata["subscription_status"] = resolved.subscription.status
        auth_context.metadata["billing_status"] = str(resolved.subscription.billing_status or resolved.subscription.status or "")
        auth_context.metadata["requests_per_minute"] = str(resolved.entitlements.requests_per_minute)
        auth_context.metadata["monthly_request_limit"] = str(
            self._monthly_request_limit(
                str(auth_context.account_id),
                resolved.entitlements.monthly_request_limit,
            )
        )
        effective_entitlements = resolved.entitlements
        organization_id = auth_context.metadata.get("organization_id")
        if (
            self._organization_feature_service is not None
            and auth_context.metadata.get("tenant_scoped_request") == "true"
            and organization_id
        ):
            apply_overrides = getattr(self._organization_feature_service, "apply_entitlement_overrides", None)
            if callable(apply_overrides):
                try:
                    effective_entitlements = apply_overrides(
                        organization_id=str(organization_id),
                        entitlements=resolved.entitlements,
                    )
                except Exception:  # noqa: BLE001
                    effective_entitlements = resolved.entitlements
        auth_context.entitlements = effective_entitlements
        if resolved.subscription.trial_status:
            auth_context.metadata["trial_status"] = resolved.subscription.trial_status
        if resolved.subscription.trial_ends_at:
            auth_context.metadata["trial_ends_at"] = resolved.subscription.trial_ends_at
        principal = _from_context(auth_context)
        billable_units = _billable_units(normalized_route_key, auth_context.metadata)
        month_key, _, _ = enforce_quota_and_scope(
            principal,
            normalized_route_key,
            self._usage_store,
            self._entitlement_service,
            self._billing_settings_resolver,
            consumed_units=billable_units,
            feature_entitlements=effective_entitlements,
        )
        auth_context.metadata["quota_month"] = month_key
        auth_context.metadata["billing_allow_overage"] = "true" if self._allow_overage(str(auth_context.account_id)) else "false"

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
        monthly_request_limit = self._monthly_request_limit(
            str(auth_context.account_id),
            entitlement.monthly_request_limit,
        )
        if decision.projected_usage > monthly_request_limit and not self._allow_overage(str(auth_context.account_id), metadata=auth_context.metadata):
            return
        increment_usage = getattr(self._usage_store, "increment_usage", None)
        if callable(increment_usage):
            increment_usage(str(auth_context.account_id), month_key, billable_units)
        else:
            for _ in range(billable_units):
                self._usage_store.increment(str(auth_context.account_id), month_key)
        self._track_organization_usage(auth_context, route_key, billable_units, month_key)

    def _track_organization_usage(self, auth_context: AuthContext, route_key: str, billable_units: int, month_key: str) -> None:
        if self._organization_usage_tracker is None or billable_units <= 0:
            return
        organization_id = auth_context.metadata.get("organization_id")
        if not organization_id or auth_context.metadata.get("tenant_scoped_request") != "true":
            return
        record_usage = getattr(self._organization_usage_tracker, "record_usage", None)
        if not callable(record_usage):
            return
        try:
            record_usage(
                organization_id=str(organization_id),
                route_key=normalize_route_key(route_key),
                billable_units=billable_units,
                period_month=month_key,
            )
        except Exception:  # noqa: BLE001
            return

    def _allow_overage(self, account_id: str, *, metadata: dict[str, str] | None = None) -> bool:
        cached = (metadata or {}).get("billing_allow_overage")
        if cached == "true":
            return True
        if cached == "false":
            return False
        if self._billing_settings_resolver is None:
            return True
        return bool(self._billing_settings_resolver.allow_overage(account_id))

    def _monthly_request_limit(self, account_id: str, default_limit: int) -> int:
        if self._billing_settings_resolver is None:
            return default_limit
        resolver = getattr(self._billing_settings_resolver, "monthly_request_limit", None)
        if not callable(resolver):
            return default_limit
        return max(
            1,
            int(
                resolver(
                    account_id,
                    default_limit,
                )
            ),
        )


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
        plan=resolved.entitlements.plan_code,
        scopes=principal.scopes,
        rate_limit_profile=principal.rate_limit_profile,
        workspace_id=principal.workspace_id,
        subject=subject,
        subscription=resolved.subscription,
        entitlements=resolved.entitlements,
        metadata={
            "principal_type": principal.auth_method,
            "billing_plan_code": resolved.subscription.plan_code,
            "subscription_status": resolved.subscription.status,
            "billing_status": str(resolved.subscription.billing_status or resolved.subscription.status or ""),
            "requests_per_minute": str(resolved.entitlements.requests_per_minute),
            "monthly_request_limit": str(resolved.entitlements.monthly_request_limit),
            "trial_status": str(resolved.subscription.trial_status or ""),
            "trial_ends_at": str(resolved.subscription.trial_ends_at or ""),
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
    if route_key in {
        "POST /v1/organization/billing/checkout-session",
        "POST /v1/organization/billing/plan-change",
        "POST /v1/organization/billing/portal-session",
        "GET /v1/organization/billing/subscription",
    }:
        return 0
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
