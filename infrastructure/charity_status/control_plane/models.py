from __future__ import annotations

from dataclasses import dataclass

from charity_status.billing.models import Subscription


@dataclass
class Account:
    id: str
    name: str
    status: str
    created_at: str
    ein: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "name": self.name,
            "ein": self.ein,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class ManagedApiKey:
    key_id: str
    account_id: str
    status: str
    created_at: str
    plan: str
    scopes: tuple[str, ...]
    rate_limit_profile: str

    def to_dict(self) -> dict[str, object]:
        return {
            "key_id": self.key_id,
            "account_id": self.account_id,
            "status": self.status,
            "created_at": self.created_at,
            "plan": self.plan,
            "scopes": list(self.scopes),
            "rate_limit_profile": self.rate_limit_profile,
        }


@dataclass
class ManagedOAuthClient:
    client_id: str
    account_id: str
    status: str
    created_at: str
    plan: str
    scopes: tuple[str, ...]
    rate_limit_profile: str

    def to_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "account_id": self.account_id,
            "status": self.status,
            "created_at": self.created_at,
            "plan": self.plan,
            "scopes": list(self.scopes),
            "rate_limit_profile": self.rate_limit_profile,
        }


@dataclass
class ManagedSubscription:
    account_id: str
    plan_code: str
    status: str
    effective_from: str | None = None
    effective_to: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "account_id": self.account_id,
            "plan_code": self.plan_code,
            "status": self.status,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
        }

    def to_subscription(self) -> Subscription:
        return Subscription(
            account_id=self.account_id,
            plan_code=self.plan_code,
            status=self.status,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
        )
