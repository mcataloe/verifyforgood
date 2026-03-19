from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any, Protocol

from charity_status.api import normalize_route_key
from charity_status.auth.errors import AuthenticationError, AuthorizationError, FeatureUnavailableError, QuotaExceededError
from charity_status.auth.models import ApiKeyPrincipal, ApiPlan, AuthenticatedPrincipal
from charity_status.billing import EntitlementService, Subscription, missing_route_requirement, recommended_upgrade_plan
from charity_status.billing.service import DEFAULT_PLANS, check_feature_entitlement, check_quota_and_calculate, monthly_period_for

DEFAULT_PLAN_LIMITS: dict[str, int] = {
    key: plan.monthly_request_limit for key, plan in DEFAULT_PLANS.items()
}

ROUTE_SCOPE_REQUIREMENTS: dict[str, str] = {
    "POST /v1/oauth/token": "oauth:token",
    "POST /v1/verify": "verify:write",
    "POST /v1/nonprofits/verify": "verify:write",
    "POST /v1/verify/batch": "verify:write",
    "GET /v1/nonprofit/{ein}": "verify:read",
    "GET /v1/nonprofits/{ein}": "verify:read",
    "GET /v1/nonprofit/{ein}/filings": "verify:read",
    "GET /v1/nonprofits/search": "nonprofits:read",
    "GET /v1/nonprofits/{ein}/sources": "sources:read",
    "GET /v1/nonprofits/{ein}/sources/{source_name}": "sources:read",
    "GET /v1/nonprofits/{ein}/compliance": "compliance:read",
    "GET /v1/nonprofits/{ein}/federal-awards": "federal_awards:read",
    "GET /v1/organization/settings": "verify:read",
    "PUT /v1/organization/settings": "verify:write",
}


@dataclass(frozen=True)
class StoredApiKeyRecord:
    key_id: str
    secret_hash: str
    account_id: str
    workspace_id: str
    scopes: tuple[str, ...]
    revoked: bool
    plan_id: str
    rate_limit_profile: str


class StaticApiKeyStore:
    def __init__(self, records: list[StoredApiKeyRecord]):
        self._by_id = {record.key_id: record for record in records}

    def get(self, key_id: str) -> StoredApiKeyRecord | None:
        return self._by_id.get(key_id)


class UsageStore(Protocol):
    def get_usage(self, account_id: str, month_key: str) -> int:
        ...

    def increment(self, account_id: str, month_key: str) -> None:
        ...

    def increment_usage(self, account_id: str, month_key: str, units: int = 1) -> int:
        ...


class BillingSettingsResolver(Protocol):
    def allow_overage(self, account_id: str) -> bool:
        ...


class InMemoryUsageStore:
    def __init__(self):
        self._usage: dict[tuple[str, str], int] = {}

    def get_usage(self, account_id: str, month_key: str) -> int:
        return self._usage.get((account_id, month_key), 0)

    def increment(self, account_id: str, month_key: str) -> None:
        key = (account_id, month_key)
        self._usage[key] = self._usage.get(key, 0) + 1

    def increment_usage(self, account_id: str, month_key: str, units: int = 1) -> int:
        key = (account_id, month_key)
        self._usage[key] = self._usage.get(key, 0) + max(0, units)
        return self._usage[key]


def build_api_key_record(
    key_id: str,
    secret: str | None,
    account_id: str,
    workspace_id: str,
    scopes: list[str] | None = None,
    plan_id: str = "free",
    revoked: bool = False,
    rate_limit_profile: str | None = None,
) -> tuple[str, StoredApiKeyRecord]:
    secret_value = secret or _generate_secret()
    display_key = f"csk_{key_id}.{secret_value}"
    record = StoredApiKeyRecord(
        key_id=key_id,
        secret_hash=_hash_secret(secret_value),
        account_id=account_id,
        workspace_id=workspace_id,
        scopes=tuple(scopes or ("verify:read",)),
        revoked=revoked,
        plan_id=plan_id,
        rate_limit_profile=rate_limit_profile or plan_id,
    )
    return display_key, record


def authenticate_api_key(headers: dict[str, Any] | None, store: StaticApiKeyStore, plan_limits: dict[str, int] | None = None) -> ApiKeyPrincipal:
    presented = _extract_api_key(headers or {})
    key_id, secret = _parse_presented_key(presented)
    record = store.get(key_id)
    if record is None:
        raise AuthenticationError("Invalid API key")
    if record.revoked:
        raise AuthenticationError("API key revoked")
    if not hmac.compare_digest(_hash_secret(secret), record.secret_hash):
        raise AuthenticationError("Invalid API key")

    limits = plan_limits or DEFAULT_PLAN_LIMITS
    normalized_plan_id = EntitlementService().normalize_plan_code(record.plan_id)
    resolved = DEFAULT_PLANS.get(normalized_plan_id, DEFAULT_PLANS["free"])
    monthly_limit = limits.get(normalized_plan_id, resolved.monthly_request_limit)
    subscription = Subscription(account_id=record.account_id, plan_code=normalized_plan_id, status="active")
    return ApiKeyPrincipal(
        credential_id=record.key_id,
        account_id=record.account_id,
        workspace_id=record.workspace_id,
        plan=ApiPlan(plan_id=normalized_plan_id, monthly_limit=monthly_limit, entitlements=resolved.entitlements),
        scopes=record.scopes,
        auth_method="api_key",
        rate_limit_profile=record.rate_limit_profile,
        subscription=subscription,
        entitlements=resolved.entitlements,
    )


def enforce_quota_and_scope(
    principal: AuthenticatedPrincipal,
    route_key: str,
    usage_store: UsageStore,
    entitlement_service: EntitlementService | None = None,
    billing_settings_resolver: BillingSettingsResolver | None = None,
    consumed_units: int = 1,
) -> tuple[str, int, int]:
    route_key = normalize_route_key(route_key)
    required_scope = ROUTE_SCOPE_REQUIREMENTS.get(route_key)
    if required_scope and required_scope not in principal.scopes:
        raise AuthorizationError("Insufficient scope for endpoint")

    service = entitlement_service or EntitlementService()
    resolved = service.resolve(
        account_id=principal.account_id,
        fallback_plan_code=principal.plan.plan_id,
        subscription=principal.subscription,
    )
    missing_requirement = missing_route_requirement(resolved.entitlements, route_key)
    if missing_requirement is not None:
        requirement_type, requirement_name = missing_requirement
        raise FeatureUnavailableError(
            "Plan entitlement does not allow this endpoint",
            feature_flag=requirement_name if requirement_type == "feature_flag" else None,
            capability=requirement_name if requirement_type == "capability" else None,
            upgrade_plan=recommended_upgrade_plan(
                feature_flag=requirement_name if requirement_type == "feature_flag" else None,
                capability=requirement_name if requirement_type == "capability" else None,
            ),
        )
    month_key = monthly_period_for()
    used = usage_store.get_usage(principal.account_id, month_key)
    decision = check_quota_and_calculate(
        plan=resolved.entitlements,
        used_units=used,
        consumed_units=consumed_units,
        period_key=month_key,
    )
    allow_overage = billing_settings_resolver.allow_overage(principal.account_id) if billing_settings_resolver is not None else True
    if decision.projected_usage > decision.limit_units and not allow_overage:
        raise QuotaExceededError(
            "Monthly request limit reached. Upgrade your subscription or enable pay per request to continue.",
            code="quota_exceeded_hard_stop",
        )
    return month_key, used, resolved.entitlements.monthly_request_limit


def hash_secret(secret: str) -> str:
    return _hash_secret(secret)


def _extract_api_key(headers: dict[str, Any]) -> str:
    for key, value in headers.items():
        if str(key).lower() == "x-api-key" and isinstance(value, str) and value.strip():
            return value.strip()
    raise AuthenticationError("Missing API key")


def _parse_presented_key(value: str) -> tuple[str, str]:
    if not value.startswith("csk_") or "." not in value:
        raise AuthenticationError("Invalid API key format")
    key_id, secret = value[4:].split(".", 1)
    if not key_id or not secret:
        raise AuthenticationError("Invalid API key format")
    return key_id, secret


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _generate_secret() -> str:
    return secrets.token_urlsafe(24)
