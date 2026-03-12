from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from typing import Any

from charity_status.auth.errors import AuthenticationError
from charity_status.auth.models import ApiPlan, OAuthClientPrincipal
from charity_status.billing.service import DEFAULT_PLANS


@dataclass(frozen=True)
class StoredOAuthTokenRecord:
    client_id: str
    token_hash: str
    account_id: str
    workspace_id: str
    scopes: tuple[str, ...]
    revoked: bool
    plan_id: str


class StaticOAuthTokenStore:
    def __init__(self, records: list[StoredOAuthTokenRecord]):
        self._records = records

    def find_by_token(self, token: str) -> StoredOAuthTokenRecord | None:
        digest = _hash_secret(token)
        for record in self._records:
            if hmac.compare_digest(record.token_hash, digest):
                return record
        return None


def build_oauth_token_record(
    client_id: str,
    token: str | None,
    account_id: str,
    workspace_id: str,
    scopes: list[str] | None = None,
    plan_id: str = "developer",
    revoked: bool = False,
) -> tuple[str, StoredOAuthTokenRecord]:
    token_value = token or _generate_secret()
    record = StoredOAuthTokenRecord(
        client_id=client_id,
        token_hash=_hash_secret(token_value),
        account_id=account_id,
        workspace_id=workspace_id,
        scopes=tuple(scopes or ("verify:read",)),
        revoked=revoked,
        plan_id=plan_id,
    )
    return token_value, record


def authenticate_bearer_token(headers: dict[str, Any] | None, store: StaticOAuthTokenStore) -> OAuthClientPrincipal:
    token = _extract_bearer_token(headers or {})
    record = store.find_by_token(token)
    if record is None:
        raise AuthenticationError("Invalid bearer token")
    if record.revoked:
        raise AuthenticationError("Bearer token revoked")
    plan = DEFAULT_PLANS.get(record.plan_id, DEFAULT_PLANS["developer"])
    return OAuthClientPrincipal(
        client_id=record.client_id,
        account_id=record.account_id,
        workspace_id=record.workspace_id,
        plan=ApiPlan(plan_id=plan.plan_id, monthly_limit=plan.monthly_request_limit, entitlements=plan.entitlements),
        scopes=record.scopes,
    )


def _extract_bearer_token(headers: dict[str, Any]) -> str:
    for key, value in headers.items():
        if str(key).lower() != "authorization":
            continue
        candidate = str(value).strip()
        if candidate.lower().startswith("bearer ") and len(candidate) > 7:
            return candidate[7:].strip()
    raise AuthenticationError("Missing bearer token")


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _generate_secret() -> str:
    return secrets.token_urlsafe(32)
