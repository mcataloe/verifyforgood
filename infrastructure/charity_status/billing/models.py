from __future__ import annotations

from dataclasses import dataclass, field


FEATURE_FLAGS: tuple[str, ...] = (
    "financial_trends",
    "risk_flags",
    "benchmarking",
    "state_registry",
    "monitoring",
)


@dataclass(frozen=True)
class Subscription:
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


@dataclass(frozen=True)
class TrialHistory:
    ein: str
    trial_consumed: bool
    first_account_id: str | None = None
    last_account_id: str | None = None
    trial_started_at: str | None = None
    trial_ended_at: str | None = None
    last_status: str | None = None
    last_termination_reason: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class Entitlement:
    plan_code: str
    feature_flags: tuple[str, ...] = ()
    request_limits: dict[str, int] = field(default_factory=dict)
    rate_limits: dict[str, int] = field(default_factory=dict)
    allowed_capabilities: tuple[str, ...] = ()
    overage_unit_price_usd_micros: int = 0

    @property
    def monthly_request_limit(self) -> int:
        return max(0, int(self.request_limits.get("monthly_requests", 0)))

    @property
    def batch_request_limit(self) -> int:
        return max(0, int(self.request_limits.get("batch_items", 0)))

    @property
    def requests_per_minute(self) -> int:
        return max(0, int(self.rate_limits.get("requests_per_minute", 0)))

    def has_feature(self, feature_flag: str) -> bool:
        return feature_flag in self.feature_flags

    def allows_capability(self, capability: str) -> bool:
        return capability in self.allowed_capabilities


@dataclass(frozen=True)
class ResolvedEntitlements:
    subscription: Subscription
    entitlements: Entitlement


@dataclass(frozen=True)
class SubscriptionPlan:
    plan_id: str
    monthly_request_limit: int
    included_units: int
    overage_unit_price_usd_micros: int
    entitlements: Entitlement


@dataclass(frozen=True)
class Account:
    account_id: str
    plan: SubscriptionPlan


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    account_id: str


@dataclass(frozen=True)
class UsageMeter:
    account_id: str
    period_key: str
    used_units: int


@dataclass(frozen=True)
class MonthlyQuotaPeriod:
    period_key: str
    limit_units: int
    used_units: int
    remaining_units: int
