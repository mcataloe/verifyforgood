from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from verification.auth.errors import AuthenticationError
from verification.auth.models import ApiPlan, OAuthClientPrincipal
from verification.auth.service import hash_secret
from verification.billing import EntitlementService, Subscription
from verification.billing.service import DEFAULT_PLANS


DEFAULT_OAUTH_TOKEN_TTL_SECONDS = 3600


@dataclass(frozen=True)
class StoredOAuthTokenRecord:
    client_id: str
    token_hash: str
    account_id: str
    workspace_id: str
    scopes: tuple[str, ...]
    revoked: bool
    plan_id: str
    rate_limit_profile: str


@dataclass(frozen=True)
class StoredOAuthClientRecord:
    client_id: str
    client_secret_hash: str
    account_id: str
    workspace_id: str
    scopes: tuple[str, ...]
    revoked: bool
    plan_id: str
    rate_limit_profile: str


class StaticOAuthTokenStore:
    def __init__(self, records: list[StoredOAuthTokenRecord]):
        self._records = records

    def find_by_token(self, token: str) -> StoredOAuthTokenRecord | None:
        digest = hash_secret(token)
        for record in self._records:
            if hmac.compare_digest(record.token_hash, digest):
                return record
        return None


class StaticOAuthClientStore:
    def __init__(self, records: list[StoredOAuthClientRecord]):
        self._by_id = {record.client_id: record for record in records}

    def get(self, client_id: str) -> StoredOAuthClientRecord | None:
        return self._by_id.get(client_id)


def build_oauth_token_record(
    client_id: str,
    token: str | None,
    account_id: str,
    workspace_id: str,
    scopes: list[str] | None = None,
    plan_id: str = "free",
    revoked: bool = False,
    rate_limit_profile: str | None = None,
) -> tuple[str, StoredOAuthTokenRecord]:
    token_value = token or _generate_secret()
    record = StoredOAuthTokenRecord(
        client_id=client_id,
        token_hash=hash_secret(token_value),
        account_id=account_id,
        workspace_id=workspace_id,
        scopes=tuple(scopes or ("verify:read",)),
        revoked=revoked,
        plan_id=plan_id,
        rate_limit_profile=rate_limit_profile or plan_id,
    )
    return token_value, record


def build_oauth_client_record(
    client_id: str,
    client_secret: str | None,
    account_id: str,
    workspace_id: str,
    scopes: list[str] | None = None,
    plan_id: str = "free",
    revoked: bool = False,
    rate_limit_profile: str | None = None,
) -> tuple[str, StoredOAuthClientRecord]:
    secret_value = client_secret or _generate_secret()
    record = StoredOAuthClientRecord(
        client_id=client_id,
        client_secret_hash=hash_secret(secret_value),
        account_id=account_id,
        workspace_id=workspace_id,
        scopes=tuple(scopes or ("oauth:token", "verify:read")),
        revoked=revoked,
        plan_id=plan_id,
        rate_limit_profile=rate_limit_profile or plan_id,
    )
    return secret_value, record


def authenticate_oauth_client_credentials(
    client_id: str,
    client_secret: str,
    store: StaticOAuthClientStore,
) -> OAuthClientPrincipal:
    record = store.get(client_id)
    if record is None:
        raise AuthenticationError("Invalid OAuth client credentials")
    if record.revoked:
        raise AuthenticationError("OAuth client revoked")
    if not hmac.compare_digest(hash_secret(client_secret), record.client_secret_hash):
        raise AuthenticationError("Invalid OAuth client credentials")
    return _client_record_to_principal(record)


def issue_client_access_token(
    principal: OAuthClientPrincipal,
    client_store: StaticOAuthClientStore,
    *,
    ttl_seconds: int = DEFAULT_OAUTH_TOKEN_TTL_SECONDS,
    now_epoch: int | None = None,
) -> dict[str, Any]:
    issued_at = int(now_epoch if now_epoch is not None else time.time())
    expires_at = issued_at + max(1, int(ttl_seconds))
    record = client_store.get(principal.client_id)
    if record is None:
        raise AuthenticationError("OAuth client is not configured")

    payload = {
        "sub": principal.client_id,
        "iat": issued_at,
        "exp": expires_at,
        "scp": list(principal.scopes),
    }
    payload_segment = _base64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(
        record.client_secret_hash.encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    token = f"oct_{payload_segment}.{_base64url_encode(signature)}"
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_at - issued_at,
        "scope": " ".join(principal.scopes),
    }


def authenticate_bearer_token(
    headers: dict[str, Any] | None,
    token_store: StaticOAuthTokenStore | None = None,
    client_store: StaticOAuthClientStore | None = None,
    *,
    now_epoch: int | None = None,
) -> OAuthClientPrincipal:
    token = _extract_bearer_token(headers or {})
    if client_store is not None and token.startswith("oct_"):
        return authenticate_signed_access_token(token, client_store, now_epoch=now_epoch)
    if token_store is None:
        raise AuthenticationError("Invalid bearer token")
    record = token_store.find_by_token(token)
    if record is None:
        raise AuthenticationError("Invalid bearer token")
    if record.revoked:
        raise AuthenticationError("Bearer token revoked")
    return _token_record_to_principal(record)


def authenticate_signed_access_token(
    token: str,
    client_store: StaticOAuthClientStore,
    *,
    now_epoch: int | None = None,
) -> OAuthClientPrincipal:
    payload_segment, signature_segment = _split_signed_token(token)
    payload_bytes = _base64url_decode(payload_segment)
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthenticationError("Invalid bearer token") from exc

    client_id = str(payload.get("sub") or "")
    if not client_id:
        raise AuthenticationError("Invalid bearer token")
    record = client_store.get(client_id)
    if record is None:
        raise AuthenticationError("Invalid bearer token")
    if record.revoked:
        raise AuthenticationError("Bearer token revoked")

    expected_signature = hmac.new(
        record.client_secret_hash.encode("utf-8"),
        payload_segment.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    presented_signature = _base64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, presented_signature):
        raise AuthenticationError("Invalid bearer token")

    current_epoch = int(now_epoch if now_epoch is not None else time.time())
    expires_at = int(payload.get("exp") or 0)
    if expires_at <= current_epoch:
        raise AuthenticationError("Bearer token expired")
    return _client_record_to_principal(record)


def _token_record_to_principal(record: StoredOAuthTokenRecord) -> OAuthClientPrincipal:
    normalized_plan_id = EntitlementService().normalize_plan_code(record.plan_id)
    plan = DEFAULT_PLANS.get(normalized_plan_id, DEFAULT_PLANS["free"])
    subscription = Subscription(account_id=record.account_id, plan_code=normalized_plan_id, status="active")
    return OAuthClientPrincipal(
        credential_id=record.client_id,
        account_id=record.account_id,
        workspace_id=record.workspace_id,
        plan=ApiPlan(plan_id=plan.plan_id, monthly_limit=plan.monthly_request_limit, entitlements=plan.entitlements),
        scopes=record.scopes,
        auth_method="oauth_client_credentials",
        rate_limit_profile=record.rate_limit_profile,
        subscription=subscription,
        entitlements=plan.entitlements,
    )


def _client_record_to_principal(record: StoredOAuthClientRecord) -> OAuthClientPrincipal:
    normalized_plan_id = EntitlementService().normalize_plan_code(record.plan_id)
    plan = DEFAULT_PLANS.get(normalized_plan_id, DEFAULT_PLANS["free"])
    subscription = Subscription(account_id=record.account_id, plan_code=normalized_plan_id, status="active")
    return OAuthClientPrincipal(
        credential_id=record.client_id,
        account_id=record.account_id,
        workspace_id=record.workspace_id,
        plan=ApiPlan(plan_id=plan.plan_id, monthly_limit=plan.monthly_request_limit, entitlements=plan.entitlements),
        scopes=record.scopes,
        auth_method="oauth_client_credentials",
        rate_limit_profile=record.rate_limit_profile,
        subscription=subscription,
        entitlements=plan.entitlements,
    )


def _extract_bearer_token(headers: dict[str, Any]) -> str:
    for key, value in headers.items():
        if str(key).lower() != "authorization":
            continue
        candidate = str(value).strip()
        if candidate.lower().startswith("bearer ") and len(candidate) > 7:
            return candidate[7:].strip()
    raise AuthenticationError("Missing bearer token")


def _split_signed_token(token: str) -> tuple[str, str]:
    if not token.startswith("oct_") or "." not in token:
        raise AuthenticationError("Invalid bearer token")
    payload_segment, signature_segment = token[4:].split(".", 1)
    if not payload_segment or not signature_segment:
        raise AuthenticationError("Invalid bearer token")
    return payload_segment, signature_segment


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("utf-8"))
    except Exception as exc:
        raise AuthenticationError("Invalid bearer token") from exc


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)

