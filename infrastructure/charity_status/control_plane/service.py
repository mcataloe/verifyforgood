from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Protocol
from uuid import uuid4

from charity_status.auth.oauth import StoredOAuthClientRecord, build_oauth_client_record
from charity_status.auth.service import StoredApiKeyRecord, build_api_key_record
from charity_status.billing import EntitlementService, Subscription

from .models import Account, ManagedApiKey, ManagedBillingEvent, ManagedOAuthClient, ManagedSubscription, ManagedTrialHistory


class ControlPlaneError(ValueError):
    status_code = 400


class ControlPlaneNotFound(ControlPlaneError):
    status_code = 404


class ControlPlaneStore(Protocol):
    def list_accounts(self) -> list[Account]:
        ...

    def get_account(self, account_id: str) -> Account | None:
        ...

    def put_account(self, account: Account) -> None:
        ...

    def get_subscription(self, account_id: str) -> ManagedSubscription | None:
        ...

    def put_subscription(self, subscription: ManagedSubscription) -> None:
        ...

    def get_subscription_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedSubscription | None:
        ...

    def get_subscription_by_stripe_subscription_id(self, stripe_subscription_id: str) -> ManagedSubscription | None:
        ...

    def get_billing_event(self, event_id: str) -> ManagedBillingEvent | None:
        ...

    def put_billing_event(self, event: ManagedBillingEvent) -> None:
        ...

    def get_trial_history(self, ein: str) -> ManagedTrialHistory | None:
        ...

    def put_trial_history(self, history: ManagedTrialHistory) -> None:
        ...

    def list_api_keys(self, account_id: str) -> list[ManagedApiKey]:
        ...

    def get_api_key(self, account_id: str, key_id: str) -> tuple[ManagedApiKey, StoredApiKeyRecord] | None:
        ...

    def get_api_key_record(self, key_id: str) -> StoredApiKeyRecord | None:
        ...

    def put_api_key(self, model: ManagedApiKey, record: StoredApiKeyRecord) -> None:
        ...

    def list_oauth_clients(self, account_id: str) -> list[ManagedOAuthClient]:
        ...

    def get_oauth_client(self, account_id: str, client_id: str) -> tuple[ManagedOAuthClient, StoredOAuthClientRecord] | None:
        ...

    def get_oauth_client_record(self, client_id: str) -> StoredOAuthClientRecord | None:
        ...

    def put_oauth_client(self, model: ManagedOAuthClient, record: StoredOAuthClientRecord) -> None:
        ...

    def get_usage(self, account_id: str, month_key: str) -> int:
        ...

    def increment_usage(self, account_id: str, month_key: str, units: int = 1) -> int:
        ...


class InMemoryControlPlaneStore:
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.subscriptions: dict[str, ManagedSubscription] = {}
        self.api_keys: dict[str, tuple[ManagedApiKey, StoredApiKeyRecord]] = {}
        self.oauth_clients: dict[str, tuple[ManagedOAuthClient, StoredOAuthClientRecord]] = {}
        self.usage: dict[tuple[str, str], int] = {}
        self.billing_events: dict[str, ManagedBillingEvent] = {}
        self.trial_histories: dict[str, ManagedTrialHistory] = {}

    def list_accounts(self) -> list[Account]:
        return list(self.accounts.values())

    def get_account(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)

    def put_account(self, account: Account) -> None:
        self.accounts[account.id] = account

    def get_subscription(self, account_id: str) -> ManagedSubscription | None:
        return self.subscriptions.get(account_id)

    def put_subscription(self, subscription: ManagedSubscription) -> None:
        self.subscriptions[subscription.account_id] = subscription

    def get_subscription_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedSubscription | None:
        for subscription in self.subscriptions.values():
            if subscription.stripe_customer_id == stripe_customer_id:
                return subscription
        return None

    def get_subscription_by_stripe_subscription_id(self, stripe_subscription_id: str) -> ManagedSubscription | None:
        for subscription in self.subscriptions.values():
            if subscription.stripe_subscription_id == stripe_subscription_id:
                return subscription
        return None

    def get_billing_event(self, event_id: str) -> ManagedBillingEvent | None:
        return self.billing_events.get(event_id)

    def put_billing_event(self, event: ManagedBillingEvent) -> None:
        self.billing_events[event.event_id] = event

    def get_trial_history(self, ein: str) -> ManagedTrialHistory | None:
        return self.trial_histories.get(ein)

    def put_trial_history(self, history: ManagedTrialHistory) -> None:
        self.trial_histories[history.ein] = history

    def list_api_keys(self, account_id: str) -> list[ManagedApiKey]:
        return [model for model, _record in self.api_keys.values() if model.account_id == account_id]

    def get_api_key(self, account_id: str, key_id: str) -> tuple[ManagedApiKey, StoredApiKeyRecord] | None:
        candidate = self.api_keys.get(key_id)
        if candidate is None or candidate[0].account_id != account_id:
            return None
        return candidate

    def get_api_key_record(self, key_id: str) -> StoredApiKeyRecord | None:
        candidate = self.api_keys.get(key_id)
        if candidate is None:
            return None
        return candidate[1]

    def put_api_key(self, model: ManagedApiKey, record: StoredApiKeyRecord) -> None:
        self.api_keys[model.key_id] = (model, record)

    def list_oauth_clients(self, account_id: str) -> list[ManagedOAuthClient]:
        return [model for model, _record in self.oauth_clients.values() if model.account_id == account_id]

    def get_oauth_client(self, account_id: str, client_id: str) -> tuple[ManagedOAuthClient, StoredOAuthClientRecord] | None:
        candidate = self.oauth_clients.get(client_id)
        if candidate is None or candidate[0].account_id != account_id:
            return None
        return candidate

    def get_oauth_client_record(self, client_id: str) -> StoredOAuthClientRecord | None:
        candidate = self.oauth_clients.get(client_id)
        if candidate is None:
            return None
        return candidate[1]

    def put_oauth_client(self, model: ManagedOAuthClient, record: StoredOAuthClientRecord) -> None:
        self.oauth_clients[model.client_id] = (model, record)

    def get_usage(self, account_id: str, month_key: str) -> int:
        return self.usage.get((account_id, month_key), 0)

    def increment_usage(self, account_id: str, month_key: str, units: int = 1) -> int:
        key = (account_id, month_key)
        self.usage[key] = self.usage.get(key, 0) + max(0, units)
        return self.usage[key]

    def increment(self, account_id: str, month_key: str) -> None:
        self.increment_usage(account_id, month_key, units=1)


@dataclass
class ControlPlaneService:
    store: ControlPlaneStore

    def __post_init__(self) -> None:
        self._entitlement_service = EntitlementService(subscription_loader=self._load_subscription)

    def list_accounts(self) -> list[dict[str, Any]]:
        return [self._serialize_account(account) for account in self.store.list_accounts()]

    def get_account(self, account_id: str) -> dict[str, Any]:
        return self._serialize_account(self._get_account(account_id))

    def create_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ControlPlaneError("name is required")
        ein = _normalize_ein(payload.get("ein"))
        if "id" in payload:
            raise ControlPlaneError("id is system-generated")
        account_id = f"acct_{uuid4().hex}"
        if self.store.get_account(account_id) is not None:
            raise ControlPlaneError("account already exists")
        account = Account(
            id=account_id,
            name=name,
            status="active",
            created_at=_utcnow(),
            ein=ein,
        )
        self.store.put_account(account)
        self.store.put_subscription(
            ManagedSubscription(
                account_id=account.id,
                plan_code="free",
                status="active",
                effective_from=account.created_at,
                effective_to=None,
                trial_status="never_started",
                trial_consumed=False,
                updated_at=account.created_at,
            )
        )
        return self._serialize_account(account)

    def update_account(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        account = self._get_account(account_id)
        if "ein" in payload:
            raise ControlPlaneError("ein cannot be updated")
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
        self.store.put_account(account)
        return self._serialize_account(account)

    def suspend_account(self, account_id: str) -> dict[str, Any]:
        account = self._get_account(account_id)
        account.status = "suspended"
        self.store.put_account(account)
        return self._serialize_account(account)

    def activate_account(self, account_id: str) -> dict[str, Any]:
        account = self._get_account(account_id)
        account.status = "active"
        self.store.put_account(account)
        return self._serialize_account(account)

    def create_api_key(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._get_account(account_id)
        scopes = _scopes(payload.get("scopes"), default=("verify:read",))
        plan = self._resolve_plan_code(account_id, payload.get("plan"))
        if "key_id" in payload:
            raise ControlPlaneError("key_id is system-generated")
        key_id = f"key_{uuid4().hex}"
        if self.store.get_api_key_record(key_id) is not None:
            raise ControlPlaneError("API key already exists")
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
        self.store.put_api_key(model, record)
        return {"api_key": model.to_dict(), "secret": plaintext}

    def list_api_keys(self, account_id: str) -> list[dict[str, Any]]:
        self._get_account(account_id)
        return [model.to_dict() for model in self.store.list_api_keys(account_id)]

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
        self.store.put_api_key(model, updated_record)
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
        self.store.put_api_key(model, updated_record)
        return {"api_key": model.to_dict(), "secret": plaintext}

    def create_oauth_client(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._get_account(account_id)
        scopes = _scopes(payload.get("scopes"), default=("oauth:token", "verify:read"))
        plan = self._resolve_plan_code(account_id, payload.get("plan"))
        if "client_id" in payload:
            raise ControlPlaneError("client_id is system-generated")
        client_id = f"client_{uuid4().hex}"
        if self.store.get_oauth_client_record(client_id) is not None:
            raise ControlPlaneError("OAuth client already exists")
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
        self.store.put_oauth_client(model, record)
        return {"oauth_client": model.to_dict(), "client_secret": plaintext}

    def list_oauth_clients(self, account_id: str) -> list[dict[str, Any]]:
        self._get_account(account_id)
        return [model.to_dict() for model in self.store.list_oauth_clients(account_id)]

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
        self.store.put_oauth_client(model, updated_record)
        return model.to_dict()

    def list_subscriptions(self) -> list[dict[str, Any]]:
        accounts = [account.id for account in self.store.list_accounts()]
        return [subscription.to_dict() for subscription in (self.store.get_subscription(account_id) for account_id in accounts) if subscription is not None]

    def get_subscription(self, account_id: str) -> dict[str, Any]:
        self._get_account(account_id)
        return self._get_subscription(account_id).to_dict()

    def update_subscription(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._get_account(account_id)
        subscription = self._build_subscription(account_id, payload)
        self.store.put_subscription(subscription)
        return subscription.to_dict()

    def _get_account(self, account_id: str) -> Account:
        account = self.store.get_account(account_id)
        if account is None:
            raise ControlPlaneNotFound("Account not found")
        return account

    def _get_api_key(self, account_id: str, key_id: str) -> tuple[ManagedApiKey, StoredApiKeyRecord]:
        candidate = self.store.get_api_key(account_id, key_id)
        if candidate is None:
            raise ControlPlaneNotFound("API key not found")
        return candidate

    def _get_oauth_client(self, account_id: str, client_id: str) -> tuple[ManagedOAuthClient, StoredOAuthClientRecord]:
        candidate = self.store.get_oauth_client(account_id, client_id)
        if candidate is None:
            raise ControlPlaneNotFound("OAuth client not found")
        return candidate

    def _get_subscription(self, account_id: str) -> ManagedSubscription:
        subscription = self.store.get_subscription(account_id)
        if subscription is None:
            raise ControlPlaneNotFound("Subscription not found")
        return subscription

    def _load_subscription(self, account_id: str) -> Subscription | None:
        subscription = self.store.get_subscription(account_id)
        if subscription is None:
            return None
        return subscription.to_subscription()

    def _resolve_plan_code(self, account_id: str, value: Any) -> str:
        if value is not None:
            return self._entitlement_service.normalize_plan_code(str(value))
        current = self.store.get_subscription(account_id)
        if current is not None:
            return current.plan_code
        return "free"

    def _build_subscription(self, account_id: str, payload: dict[str, Any]) -> ManagedSubscription:
        current = self.store.get_subscription(account_id)
        candidate = Subscription(
            account_id=account_id,
            plan_code=self._entitlement_service.normalize_plan_code(payload.get("plan_code") or payload.get("plan") or (current.plan_code if current else "free")),
            status=str(payload.get("status") or (current.status if current else "active")).strip().lower(),
            effective_from=_optional_string(payload.get("effective_from"), default=current.effective_from if current else None),
            effective_to=_optional_string(payload.get("effective_to"), default=current.effective_to if current else None),
        )
        try:
            normalized = self._entitlement_service.set_subscription(candidate)
        except ValueError as exc:
            raise ControlPlaneError(str(exc)) from exc
        return ManagedSubscription(
            account_id=normalized.account_id,
            plan_code=normalized.plan_code,
            status=normalized.status,
            effective_from=normalized.effective_from,
            effective_to=normalized.effective_to,
            stripe_customer_id=current.stripe_customer_id if current else None,
            stripe_subscription_id=current.stripe_subscription_id if current else None,
            billing_status=current.billing_status if current else None,
            billing_period_start=current.billing_period_start if current else None,
            billing_period_end=current.billing_period_end if current else None,
            trial_status=current.trial_status if current else "never_started",
            trial_started_at=current.trial_started_at if current else None,
            trial_ends_at=current.trial_ends_at if current else None,
            trial_trigger_event=current.trial_trigger_event if current else None,
            trial_consumed=current.trial_consumed if current else False,
            trial_termination_reason=current.trial_termination_reason if current else None,
            pending_plan_code=current.pending_plan_code if current else None,
            pending_plan_effective_at=current.pending_plan_effective_at if current else None,
            stripe_subscription_schedule_id=current.stripe_subscription_schedule_id if current else None,
            pending_checkout_session_id=current.pending_checkout_session_id if current else None,
            pending_checkout_session_url=current.pending_checkout_session_url if current else None,
            pending_checkout_expires_at=current.pending_checkout_expires_at if current else None,
            updated_at=_utcnow(),
        )

    def _serialize_account(self, account: Account) -> dict[str, Any]:
        subscription = self.store.get_subscription(account.id)
        subscription_plan = None
        if subscription is not None:
            subscription_plan = self._entitlement_service.normalize_plan_code(subscription.plan_code)
        return account.to_dict(subscription=subscription_plan)


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


def _optional_string(value: Any, *, default: str | None = None) -> str | None:
    if value is None:
        return default
    candidate = str(value).strip()
    return candidate or None


def _normalize_ein(value: Any) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        raise ControlPlaneError("ein is required")
    normalized = re.sub(r"\D", "", candidate)
    if len(normalized) != 9:
        raise ControlPlaneError("ein must be a valid EIN")
    return normalized
