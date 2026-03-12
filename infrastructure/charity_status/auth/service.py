from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any

from charity_status.auth.errors import AuthenticationError, AuthorizationError, QuotaExceededError
from charity_status.auth.models import ApiKeyPrincipal, ApiPlan
from charity_status.billing.service import DEFAULT_PLANS, check_feature_entitlement, check_quota_and_calculate, monthly_period_for

DEFAULT_PLAN_LIMITS: dict[str, int] = {
    key: plan.monthly_request_limit for key, plan in DEFAULT_PLANS.items()
}

ROUTE_SCOPE_REQUIREMENTS: dict[str, str] = {
    "POST /verify": "verify:write",
    "POST /verify/batch": "verify:write",
    "GET /nonprofit/{ein}": "verify:read",
    "GET /nonprofit/{ein}/filings": "verify:read",
    "GET /nonprofits/search": "nonprofits:read",
    "GET /nonprofits/{ein}/sources": "sources:read",
    "GET /nonprofits/{ein}/sources/{source_name}": "sources:read",
    "GET /nonprofits/{ein}/compliance": "compliance:read",
    "GET /nonprofits/{ein}/federal-awards": "federal_awards:read",
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


class StaticApiKeyStore:
    def __init__(self, records: list[StoredApiKeyRecord]):
        self._by_id = {record.key_id: record for record in records}

    def get(self, key_id: str) -> StoredApiKeyRecord | None:
        return self._by_id.get(key_id)


class InMemoryUsageStore:
    def __init__(self):
        self._usage: dict[tuple[str, str], int] = {}

    def get_usage(self, account_id: str, month_key: str) -> int:
        return self._usage.get((account_id, month_key), 0)

    def increment(self, account_id: str, month_key: str) -> None:
        key = (account_id, month_key)
        self._usage[key] = self._usage.get(key, 0) + 1


def build_api_key_record(
    key_id: str,
    secret: str | None,
    account_id: str,
    workspace_id: str,
    scopes: list[str] | None = None,
    plan_id: str = "developer",
    revoked: bool = False,
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
    resolved = DEFAULT_PLANS.get(record.plan_id, DEFAULT_PLANS["developer"])
    monthly_limit = limits.get(record.plan_id, resolved.monthly_request_limit)
    return ApiKeyPrincipal(
        key_id=record.key_id,
        account_id=record.account_id,
        workspace_id=record.workspace_id,
        plan=ApiPlan(plan_id=record.plan_id, monthly_limit=monthly_limit, entitlements=resolved.entitlements),
        scopes=record.scopes,
    )


def enforce_quota_and_scope(
    principal: ApiKeyPrincipal,
    route_key: str,
    usage_store: InMemoryUsageStore,
) -> tuple[str, int, int]:
    required_scope = ROUTE_SCOPE_REQUIREMENTS.get(route_key)
    if required_scope and required_scope not in principal.scopes:
        raise AuthorizationError("Insufficient scope for endpoint")

    if not check_feature_entitlement(DEFAULT_PLANS.get(principal.plan.plan_id, DEFAULT_PLANS["developer"]), route_key):
        raise AuthorizationError("Plan entitlement does not allow this endpoint")
    month_key = monthly_period_for()
    used = usage_store.get_usage(principal.account_id, month_key)
    decision = check_quota_and_calculate(
        plan=DEFAULT_PLANS.get(principal.plan.plan_id, DEFAULT_PLANS["developer"]),
        used_units=used,
        consumed_units=1,
        period_key=month_key,
    )
    if decision.projected_usage > decision.limit_units:
        raise QuotaExceededError("Monthly request quota exceeded")
    return month_key, used, principal.plan.monthly_limit


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
