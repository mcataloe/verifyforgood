from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from charity_status.auth.oauth import StoredOAuthClientRecord, build_oauth_client_record
from charity_status.auth.service import StoredApiKeyRecord, build_api_key_record

from .models import Account, ManagedApiKey, ManagedOAuthClient


class ControlPlaneError(ValueError):
    status_code = 400


class ControlPlaneNotFound(ControlPlaneError):
    status_code = 404


class InMemoryControlPlaneStore:
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.api_keys: dict[str, tuple[ManagedApiKey, StoredApiKeyRecord]] = {}
        self.oauth_clients: dict[str, tuple[ManagedOAuthClient, StoredOAuthClientRecord]] = {}


@dataclass
class ControlPlaneService:
    store: InMemoryControlPlaneStore

    def list_accounts(self) -> list[dict[str, Any]]:
        return [account.to_dict() for account in self.store.accounts.values()]

    def get_account(self, account_id: str) -> dict[str, Any]:
        return self._get_account(account_id).to_dict()

    def create_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ControlPlaneError("name is required")
        account = Account(
            id=str(payload.get("id") or f"acct_{uuid4().hex[:12]}"),
            name=name,
            status="active",
            created_at=_utcnow(),
        )
        self.store.accounts[account.id] = account
        return account.to_dict()

    def update_account(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        account = self._get_account(account_id)
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name:
                raise ControlPlaneError("name must be a non-empty string")
            account.name = name
        if "status" in payload:
            status = str(payload.get("status") or "").strip().lower()
            if status not in {"active", "suspended"}:
                raise ControlPlaneError("status must be active or suspended")
            account.status = status
        return account.to_dict()

    def suspend_account(self, account_id: str) -> dict[str, Any]:
        account = self._get_account(account_id)
        account.status = "suspended"
        return account.to_dict()

    def activate_account(self, account_id: str) -> dict[str, Any]:
        account = self._get_account(account_id)
        account.status = "active"
        return account.to_dict()

    def create_api_key(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._get_account(account_id)
        scopes = _scopes(payload.get("scopes"), default=("verify:read",))
        plan = str(payload.get("plan") or "developer")
        key_id = str(payload.get("key_id") or f"key_{uuid4().hex[:12]}")
        plaintext, record = build_api_key_record(
            key_id=key_id,
            secret=None,
            account_id=account_id,
            workspace_id=str(payload.get("workspace_id") or account_id),
            scopes=list(scopes),
            plan_id=plan,
            rate_limit_profile=str(payload.get("rate_limit_profile") or plan),
        )
        model = ManagedApiKey(
            key_id=record.key_id,
            account_id=account_id,
            status="active",
            created_at=_utcnow(),
            plan=record.plan_id,
            scopes=record.scopes,
            rate_limit_profile=record.rate_limit_profile,
        )
        self.store.api_keys[key_id] = (model, record)
        return {"api_key": model.to_dict(), "secret": plaintext}

    def list_api_keys(self, account_id: str) -> list[dict[str, Any]]:
        self._get_account(account_id)
        return [model.to_dict() for model, _record in self.store.api_keys.values() if model.account_id == account_id]

    def delete_api_key(self, account_id: str, key_id: str) -> dict[str, Any]:
        model, record = self._get_api_key(account_id, key_id)
        updated_record = StoredApiKeyRecord(
            key_id=record.key_id,
            secret_hash=record.secret_hash,
            account_id=record.account_id,
            workspace_id=record.workspace_id,
            scopes=record.scopes,
            revoked=True,
            plan_id=record.plan_id,
            rate_limit_profile=record.rate_limit_profile,
        )
        model.status = "revoked"
        self.store.api_keys[key_id] = (model, updated_record)
        return model.to_dict()

    def rotate_api_key(self, account_id: str, key_id: str) -> dict[str, Any]:
        model, record = self._get_api_key(account_id, key_id)
        plaintext, updated_record = build_api_key_record(
            key_id=record.key_id,
            secret=None,
            account_id=record.account_id,
            workspace_id=record.workspace_id,
            scopes=list(record.scopes),
            plan_id=record.plan_id,
            rate_limit_profile=record.rate_limit_profile,
        )
        model.created_at = _utcnow()
        model.status = "active"
        self.store.api_keys[key_id] = (model, updated_record)
        return {"api_key": model.to_dict(), "secret": plaintext}

    def api_key_records(self) -> list[StoredApiKeyRecord]:
        return [record for _model, record in self.store.api_keys.values() if not record.revoked]

    def create_oauth_client(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._get_account(account_id)
        scopes = _scopes(payload.get("scopes"), default=("oauth:token", "verify:read"))
        plan = str(payload.get("plan") or "developer")
        client_id = str(payload.get("client_id") or f"client_{uuid4().hex[:12]}")
        plaintext, record = build_oauth_client_record(
            client_id=client_id,
            client_secret=None,
            account_id=account_id,
            workspace_id=str(payload.get("workspace_id") or account_id),
            scopes=list(scopes),
            plan_id=plan,
            rate_limit_profile=str(payload.get("rate_limit_profile") or plan),
        )
        model = ManagedOAuthClient(
            client_id=record.client_id,
            account_id=account_id,
            status="active",
            created_at=_utcnow(),
            plan=record.plan_id,
            scopes=record.scopes,
            rate_limit_profile=record.rate_limit_profile,
        )
        self.store.oauth_clients[client_id] = (model, record)
        return {"oauth_client": model.to_dict(), "client_secret": plaintext}

    def list_oauth_clients(self, account_id: str) -> list[dict[str, Any]]:
        self._get_account(account_id)
        return [model.to_dict() for model, _record in self.store.oauth_clients.values() if model.account_id == account_id]

    def delete_oauth_client(self, account_id: str, client_id: str) -> dict[str, Any]:
        model, record = self._get_oauth_client(account_id, client_id)
        updated_record = StoredOAuthClientRecord(
            client_id=record.client_id,
            client_secret_hash=record.client_secret_hash,
            account_id=record.account_id,
            workspace_id=record.workspace_id,
            scopes=record.scopes,
            revoked=True,
            plan_id=record.plan_id,
            rate_limit_profile=record.rate_limit_profile,
        )
        model.status = "revoked"
        self.store.oauth_clients[client_id] = (model, updated_record)
        return model.to_dict()

    def oauth_client_records(self) -> list[StoredOAuthClientRecord]:
        return [record for _model, record in self.store.oauth_clients.values() if not record.revoked]

    def _get_account(self, account_id: str) -> Account:
        account = self.store.accounts.get(account_id)
        if account is None:
            raise ControlPlaneNotFound("Account not found")
        return account

    def _get_api_key(self, account_id: str, key_id: str) -> tuple[ManagedApiKey, StoredApiKeyRecord]:
        candidate = self.store.api_keys.get(key_id)
        if candidate is None or candidate[0].account_id != account_id:
            raise ControlPlaneNotFound("API key not found")
        return candidate

    def _get_oauth_client(self, account_id: str, client_id: str) -> tuple[ManagedOAuthClient, StoredOAuthClientRecord]:
        candidate = self.store.oauth_clients.get(client_id)
        if candidate is None or candidate[0].account_id != account_id:
            raise ControlPlaneNotFound("OAuth client not found")
        return candidate


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scopes(value: Any, *, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list):
        raise ControlPlaneError("scopes must be an array")
    resolved = [str(item).strip() for item in value if str(item).strip()]
    if not resolved:
        raise ControlPlaneError("scopes must include at least one value")
    return tuple(resolved)
