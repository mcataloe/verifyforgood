from __future__ import annotations

import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Any

from charity_status.auth.errors import AuthenticationError
from charity_status.auth.service import hash_secret


@dataclass(frozen=True)
class StoredAdminKeyRecord:
    admin_id: str
    secret_hash: str
    revoked: bool


class StaticAdminKeyStore:
    def __init__(self, records: list[StoredAdminKeyRecord]):
        self._by_id = {record.admin_id: record for record in records}

    def get(self, admin_id: str) -> StoredAdminKeyRecord | None:
        return self._by_id.get(admin_id)


def build_admin_key_record(admin_id: str, secret: str | None = None, *, revoked: bool = False) -> tuple[str, StoredAdminKeyRecord]:
    secret_value = secret or secrets.token_urlsafe(24)
    display_key = f"cak_{admin_id}.{secret_value}"
    return display_key, StoredAdminKeyRecord(
        admin_id=admin_id,
        secret_hash=hash_secret(secret_value),
        revoked=revoked,
    )


def authenticate_admin_key(headers: dict[str, Any] | None, store: StaticAdminKeyStore) -> str:
    key = _extract_admin_key(headers or {})
    if not key.startswith("cak_") or "." not in key:
        raise AuthenticationError("Invalid admin key format")
    admin_id, secret = key[4:].split(".", 1)
    record = store.get(admin_id)
    if record is None:
        raise AuthenticationError("Invalid admin key")
    if record.revoked:
        raise AuthenticationError("Admin key revoked")
    if not hmac.compare_digest(record.secret_hash, hash_secret(secret)):
        raise AuthenticationError("Invalid admin key")
    return admin_id


def load_admin_key_store(raw_json: str) -> StaticAdminKeyStore:
    if not raw_json.strip():
        return StaticAdminKeyStore([])
    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("ADMIN_KEY_RECORDS_JSON must be a JSON array")
    records = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        records.append(
            StoredAdminKeyRecord(
                admin_id=str(item.get("admin_id") or ""),
                secret_hash=str(item.get("secret_hash") or ""),
                revoked=bool(item.get("revoked", False)),
            )
        )
    return StaticAdminKeyStore(records)


def _extract_admin_key(headers: dict[str, Any]) -> str:
    for key, value in headers.items():
        if str(key).lower() == "x-admin-key" and isinstance(value, str) and value.strip():
            return value.strip()
    raise AuthenticationError("Missing admin key")
