from __future__ import annotations

from dataclasses import dataclass

from verification.billing.models import Subscription, TrialHistory


@dataclass
class Account:
    id: str
    name: str
    status: str
    created_at: str
    ein: str | None = None

    def to_dict(self, *, subscription: str | None = None) -> dict[str, str | None]:
        return {
            "id": self.id,
            "name": self.name,
            "subscription": subscription,
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
    created_at: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_status: str | None = None
    billing_period_start: str | None = None
    billing_period_end: str | None = None
    grace_period_ends_at: str | None = None
    trial_status: str | None = None
    trial_started_at: str | None = None
    trial_ends_at: str | None = None
    trial_trigger_event: str | None = None
    trial_consumed: bool = False
    trial_termination_reason: str | None = None
    pending_plan_code: str | None = None
    pending_plan_effective_at: str | None = None
    cancel_at_period_end: bool = False
    stripe_subscription_schedule_id: str | None = None
    pending_checkout_session_id: str | None = None
    pending_checkout_session_url: str | None = None
    pending_checkout_expires_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "account_id": self.account_id,
            "plan_code": self.plan_code,
            "status": self.status,
            "created_at": self.created_at,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "billing_status": self.billing_status,
            "billing_period_start": self.billing_period_start,
            "billing_period_end": self.billing_period_end,
            "grace_period_ends_at": self.grace_period_ends_at,
            "trial_status": self.trial_status,
            "trial_started_at": self.trial_started_at,
            "trial_ends_at": self.trial_ends_at,
            "trial_trigger_event": self.trial_trigger_event,
            "trial_consumed": self.trial_consumed,
            "trial_termination_reason": self.trial_termination_reason,
            "pending_plan_code": self.pending_plan_code,
            "pending_plan_effective_at": self.pending_plan_effective_at,
            "cancel_at_period_end": self.cancel_at_period_end,
            "stripe_subscription_schedule_id": self.stripe_subscription_schedule_id,
            "updated_at": self.updated_at,
        }

    def to_subscription(self) -> Subscription:
        return Subscription(
            account_id=self.account_id,
            plan_code=self.plan_code,
            status=self.status,
            created_at=self.created_at,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            stripe_customer_id=self.stripe_customer_id,
            stripe_subscription_id=self.stripe_subscription_id,
            billing_status=self.billing_status,
            billing_period_start=self.billing_period_start,
            billing_period_end=self.billing_period_end,
            grace_period_ends_at=self.grace_period_ends_at,
            trial_status=self.trial_status,
            trial_started_at=self.trial_started_at,
            trial_ends_at=self.trial_ends_at,
            trial_trigger_event=self.trial_trigger_event,
            trial_consumed=self.trial_consumed,
            trial_termination_reason=self.trial_termination_reason,
            pending_plan_code=self.pending_plan_code,
            pending_plan_effective_at=self.pending_plan_effective_at,
            cancel_at_period_end=self.cancel_at_period_end,
            stripe_subscription_schedule_id=self.stripe_subscription_schedule_id,
            pending_checkout_session_id=self.pending_checkout_session_id,
            pending_checkout_session_url=self.pending_checkout_session_url,
            pending_checkout_expires_at=self.pending_checkout_expires_at,
            updated_at=self.updated_at,
        )


@dataclass
class ManagedBillingCustomer:
    account_id: str
    organization_id: str
    stripe_customer_id: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "account_id": self.account_id,
            "organization_id": self.organization_id,
            "stripe_customer_id": self.stripe_customer_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ManagedBillingEvent:
    event_id: str
    event_type: str
    processed_at: str
    account_id: str | None = None
    processing_outcome: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    stripe_invoice_id: str | None = None
    gross_amount: int | None = None
    tax_amount: int | None = None
    invoice_total: int | None = None
    currency: str | None = None
    webhook_created_at: str | None = None
    payload_fingerprint: str | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "processed_at": self.processed_at,
            "account_id": self.account_id,
            "processing_outcome": self.processing_outcome,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_invoice_id": self.stripe_invoice_id,
            "gross_amount": self.gross_amount,
            "tax_amount": self.tax_amount,
            "invoice_total": self.invoice_total,
            "currency": self.currency,
            "webhook_created_at": self.webhook_created_at,
            "payload_fingerprint": self.payload_fingerprint,
        }


ManagedTrialHistory = TrialHistory

