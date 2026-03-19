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
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_status: str | None = None
    billing_period_start: str | None = None
    billing_period_end: str | None = None
    pending_plan_code: str | None = None
    pending_checkout_session_id: str | None = None
    pending_checkout_session_url: str | None = None
    pending_checkout_expires_at: str | None = None
    updated_at: str | None = None

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
            stripe_customer_id=self.stripe_customer_id,
            stripe_subscription_id=self.stripe_subscription_id,
            billing_status=self.billing_status,
            billing_period_start=self.billing_period_start,
            billing_period_end=self.billing_period_end,
            pending_plan_code=self.pending_plan_code,
            pending_checkout_session_id=self.pending_checkout_session_id,
            pending_checkout_session_url=self.pending_checkout_session_url,
            pending_checkout_expires_at=self.pending_checkout_expires_at,
            updated_at=self.updated_at,
        )
