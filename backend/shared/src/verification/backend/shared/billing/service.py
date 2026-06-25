from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from verification.backend.shared.api import normalize_route_key
from verification.backend.shared.billing.models import Entitlement, MonthlyQuotaPeriod, ResolvedEntitlements, Subscription, SubscriptionPlan
from verification.backend.shared.billing.trials import TrialConfig


PLAN_CODE_ALIASES: dict[str, str] = {
    "developer": "free",
    "team": "growth",
    "business": "pro",
}

PLAN_CODES: tuple[str, ...] = ("free", "starter", "growth", "pro", "enterprise")

CAPABILITY_BY_ROUTE: dict[str, str] = {
    "POST /v1/verify": "verification",
    "POST /v1/nonprofits/verify": "verification",
    "POST /v1/verify/batch": "batch_verification",
    "GET /v1/nonprofit/{ein}": "verification",
    "GET /v1/nonprofits/{ein}": "verification",
    "GET /v1/nonprofit/{ein}/filings": "verification",
    "GET /v1/nonprofits/search": "verification",
    "GET /v1/nonprofits/{ein}/sources": "financial_trends",
    "GET /v1/nonprofits/{ein}/sources/{source_name}": "financial_trends",
    "GET /v1/nonprofits/{ein}/compliance": "risk_flags",
    "GET /v1/nonprofits/{ein}/federal-awards": "risk_flags",
}

ROUTE_FEATURE_REQUIREMENTS: dict[str, str] = {
    "GET /v1/nonprofits/{ein}/sources": "financial_trends",
    "GET /v1/nonprofits/{ein}/sources/{source_name}": "financial_trends",
    "GET /v1/nonprofits/{ein}/compliance": "risk_flags",
    "GET /v1/nonprofits/{ein}/federal-awards": "risk_flags",
}


DEFAULT_ENTITLEMENTS: dict[str, Entitlement] = {
    "free": Entitlement(
        plan_code="free",
        feature_flags=(),
        request_limits={"monthly_requests": 250, "batch_items": 0},
        rate_limits={"requests_per_minute": 10},
        allowed_capabilities=("verification",),
        overage_unit_price_usd_micros=5000,
    ),
    "starter": Entitlement(
        plan_code="starter",
        feature_flags=("risk_flags",),
        request_limits={"monthly_requests": 1000, "batch_items": 0},
        rate_limits={"requests_per_minute": 30},
        allowed_capabilities=("verification", "risk_flags"),
        overage_unit_price_usd_micros=4000,
    ),
    "growth": Entitlement(
        plan_code="growth",
        feature_flags=("financial_trends", "risk_flags", "benchmarking"),
        request_limits={"monthly_requests": 10000, "batch_items": 100},
        rate_limits={"requests_per_minute": 120},
        allowed_capabilities=("verification", "risk_flags", "financial_trends", "benchmarking", "batch_verification"),
        overage_unit_price_usd_micros=3000,
    ),
    "pro": Entitlement(
        plan_code="pro",
        feature_flags=("financial_trends", "risk_flags", "benchmarking", "state_registry", "monitoring"),
        request_limits={"monthly_requests": 100000, "batch_items": 1000},
        rate_limits={"requests_per_minute": 600},
        allowed_capabilities=(
            "verification",
            "risk_flags",
            "financial_trends",
            "benchmarking",
            "state_registry",
            "monitoring",
            "batch_verification",
            "organization_settings",
        ),
        overage_unit_price_usd_micros=2000,
    ),
    "enterprise": Entitlement(
        plan_code="enterprise",
        feature_flags=("financial_trends", "risk_flags", "benchmarking", "state_registry", "monitoring"),
        request_limits={"monthly_requests": 1000000, "batch_items": 5000},
        rate_limits={"requests_per_minute": 5000},
        allowed_capabilities=(
            "verification",
            "risk_flags",
            "financial_trends",
            "benchmarking",
            "state_registry",
            "monitoring",
            "batch_verification",
            "organization_settings",
        ),
        overage_unit_price_usd_micros=1000,
    ),
}

DEFAULT_PLANS: dict[str, SubscriptionPlan] = {
    plan_code: SubscriptionPlan(
        plan_id=plan_code,
        monthly_request_limit=entitlement.monthly_request_limit,
        included_units=entitlement.monthly_request_limit,
        overage_unit_price_usd_micros=entitlement.overage_unit_price_usd_micros,
        entitlements=entitlement,
    )
    for plan_code, entitlement in DEFAULT_ENTITLEMENTS.items()
}


@dataclass(frozen=True)
class MeteringDecision:
    period_key: str
    limit_units: int
    used_units: int
    consumed_units: int
    projected_usage: int
    overage_units: int
    overage_cost_usd_micros: int


class EntitlementService:
    def __init__(
        self,
        subscriptions: dict[str, Subscription] | None = None,
        subscription_loader: Callable[[str], Subscription | None] | None = None,
        trial_config: TrialConfig | None = None,
    ):
        self._subscriptions = subscriptions if subscriptions is not None else {}
        self._subscription_loader = subscription_loader
        self._trial_config = trial_config or TrialConfig()

    def resolve(
        self,
        *,
        account_id: str,
        fallback_plan_code: str | None = None,
        subscription: Subscription | None = None,
        now: datetime | None = None,
    ) -> ResolvedEntitlements:
        candidate = subscription or self._subscriptions.get(account_id)
        if candidate is None and self._subscription_loader is not None:
            candidate = self._subscription_loader(account_id)
        if candidate is None:
            candidate = Subscription(
                account_id=account_id,
                plan_code=self.normalize_plan_code(fallback_plan_code or "free"),
                status="active",
                created_at=None,
            )
        plan_code = self.normalize_plan_code(candidate.plan_code)
        resolved_subscription = Subscription(
            account_id=candidate.account_id or account_id,
            plan_code=plan_code,
            status=str(candidate.status or "active").lower(),
            created_at=candidate.created_at,
            effective_from=candidate.effective_from,
            effective_to=candidate.effective_to,
            stripe_customer_id=candidate.stripe_customer_id,
            stripe_subscription_id=candidate.stripe_subscription_id,
            billing_status=candidate.billing_status,
            billing_period_start=candidate.billing_period_start,
            billing_period_end=candidate.billing_period_end,
            grace_period_ends_at=candidate.grace_period_ends_at,
            trial_status=candidate.trial_status,
            trial_started_at=candidate.trial_started_at,
            trial_ends_at=candidate.trial_ends_at,
            trial_trigger_event=candidate.trial_trigger_event,
            trial_consumed=candidate.trial_consumed,
            trial_termination_reason=candidate.trial_termination_reason,
            pending_plan_code=candidate.pending_plan_code,
            pending_plan_effective_at=candidate.pending_plan_effective_at,
            cancel_at_period_end=candidate.cancel_at_period_end,
            stripe_subscription_schedule_id=candidate.stripe_subscription_schedule_id,
            pending_checkout_session_id=candidate.pending_checkout_session_id,
            pending_checkout_session_url=candidate.pending_checkout_session_url,
            pending_checkout_expires_at=candidate.pending_checkout_expires_at,
            updated_at=candidate.updated_at,
        )
        if not self.subscription_is_active(resolved_subscription, now=now):
            resolved_subscription = Subscription(
                account_id=resolved_subscription.account_id,
                plan_code="free",
                status=resolved_subscription.status,
                created_at=resolved_subscription.created_at,
                effective_from=resolved_subscription.effective_from,
                effective_to=resolved_subscription.effective_to,
                stripe_customer_id=resolved_subscription.stripe_customer_id,
                stripe_subscription_id=resolved_subscription.stripe_subscription_id,
                billing_status=resolved_subscription.billing_status,
                billing_period_start=resolved_subscription.billing_period_start,
                billing_period_end=resolved_subscription.billing_period_end,
                grace_period_ends_at=resolved_subscription.grace_period_ends_at,
                trial_status=resolved_subscription.trial_status,
                trial_started_at=resolved_subscription.trial_started_at,
                trial_ends_at=resolved_subscription.trial_ends_at,
                trial_trigger_event=resolved_subscription.trial_trigger_event,
                trial_consumed=resolved_subscription.trial_consumed,
                trial_termination_reason=resolved_subscription.trial_termination_reason,
                pending_plan_code=resolved_subscription.pending_plan_code,
                pending_plan_effective_at=resolved_subscription.pending_plan_effective_at,
                cancel_at_period_end=resolved_subscription.cancel_at_period_end,
                stripe_subscription_schedule_id=resolved_subscription.stripe_subscription_schedule_id,
                pending_checkout_session_id=resolved_subscription.pending_checkout_session_id,
                pending_checkout_session_url=resolved_subscription.pending_checkout_session_url,
                pending_checkout_expires_at=resolved_subscription.pending_checkout_expires_at,
                updated_at=resolved_subscription.updated_at,
            )
        entitlements = DEFAULT_ENTITLEMENTS[resolved_subscription.plan_code]
        if _trial_is_active(resolved_subscription, now=now) and resolved_subscription.plan_code == "free":
            entitlements = _trial_entitlement(self._trial_config)
        return ResolvedEntitlements(
            subscription=resolved_subscription,
            entitlements=entitlements,
        )

    def get_subscription(self, account_id: str, *, fallback_plan_code: str | None = None) -> Subscription:
        return self.resolve(account_id=account_id, fallback_plan_code=fallback_plan_code).subscription

    def set_subscription(self, subscription: Subscription) -> Subscription:
        normalized = Subscription(
            account_id=str(subscription.account_id or "").strip(),
            plan_code=self.normalize_plan_code(subscription.plan_code),
            status=str(subscription.status or "active").strip().lower(),
            created_at=subscription.created_at,
            effective_from=subscription.effective_from,
            effective_to=subscription.effective_to,
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_subscription_id=subscription.stripe_subscription_id,
            billing_status=subscription.billing_status,
            billing_period_start=subscription.billing_period_start,
            billing_period_end=subscription.billing_period_end,
            grace_period_ends_at=subscription.grace_period_ends_at,
            trial_status=subscription.trial_status,
            trial_started_at=subscription.trial_started_at,
            trial_ends_at=subscription.trial_ends_at,
            trial_trigger_event=subscription.trial_trigger_event,
            trial_consumed=subscription.trial_consumed,
            trial_termination_reason=subscription.trial_termination_reason,
            pending_plan_code=subscription.pending_plan_code,
            pending_plan_effective_at=subscription.pending_plan_effective_at,
            cancel_at_period_end=subscription.cancel_at_period_end,
            stripe_subscription_schedule_id=subscription.stripe_subscription_schedule_id,
            pending_checkout_session_id=subscription.pending_checkout_session_id,
            pending_checkout_session_url=subscription.pending_checkout_session_url,
            pending_checkout_expires_at=subscription.pending_checkout_expires_at,
            updated_at=subscription.updated_at,
        )
        if not normalized.account_id:
            raise ValueError("account_id is required")
        if normalized.status not in {"active", "scheduled", "canceled", "suspended"}:
            raise ValueError("status must be active, scheduled, canceled, or suspended")
        self._subscriptions[normalized.account_id] = normalized
        return normalized

    def normalize_plan_code(self, plan_code: str | None) -> str:
        candidate = str(plan_code or "free").strip().lower()
        candidate = PLAN_CODE_ALIASES.get(candidate, candidate)
        if candidate not in DEFAULT_ENTITLEMENTS:
            return "free"
        return candidate

    def subscription_is_active(self, subscription: Subscription, *, now: datetime | None = None) -> bool:
        if subscription.status not in {"active", "scheduled"}:
            return False
        current = now or datetime.now(timezone.utc)
        effective_from = _parse_iso_datetime(subscription.effective_from)
        effective_to = _parse_iso_datetime(subscription.effective_to)
        if effective_from is not None and current < effective_from:
            return subscription.status == "scheduled"
        if effective_to is not None and current > effective_to:
            return False
        return True


def monthly_period_for(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y-%m")


def route_feature_flag(route_key: str) -> str | None:
    return ROUTE_FEATURE_REQUIREMENTS.get(normalize_route_key(route_key))


def route_capability(route_key: str) -> str | None:
    return CAPABILITY_BY_ROUTE.get(normalize_route_key(route_key))


def check_feature_entitlement(entitlement_or_plan: Entitlement | SubscriptionPlan, route_key: str) -> bool:
    entitlements = _coerce_entitlement(entitlement_or_plan)
    required_feature = route_feature_flag(route_key)
    required_capability = route_capability(route_key)
    if required_feature and not entitlements.has_feature(required_feature):
        return False
    if required_capability and not entitlements.allows_capability(required_capability):
        return False
    return True


def check_quota_and_calculate(
    *,
    plan: SubscriptionPlan | Entitlement,
    used_units: int,
    consumed_units: int,
    period_key: str,
) -> MeteringDecision:
    entitlements = _coerce_entitlement(plan)
    projected = used_units + max(0, consumed_units)
    limit = max(0, entitlements.monthly_request_limit)
    if projected <= limit:
        overage_units = 0
    else:
        overage_units = projected - limit
    return MeteringDecision(
        period_key=period_key,
        limit_units=limit,
        used_units=used_units,
        consumed_units=max(0, consumed_units),
        projected_usage=projected,
        overage_units=overage_units,
        overage_cost_usd_micros=overage_units * entitlements.overage_unit_price_usd_micros,
    )


def quota_period_state(plan: SubscriptionPlan | Entitlement, used_units: int, period_key: str) -> MonthlyQuotaPeriod:
    entitlements = _coerce_entitlement(plan)
    limit = max(0, entitlements.monthly_request_limit)
    used = max(0, used_units)
    return MonthlyQuotaPeriod(period_key=period_key, limit_units=limit, used_units=used, remaining_units=max(0, limit - used))


def _coerce_entitlement(plan: SubscriptionPlan | Entitlement) -> Entitlement:
    if isinstance(plan, Entitlement):
        return plan
    return plan.entitlements


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    candidate = str(value).strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _trial_is_active(subscription: Subscription, *, now: datetime | None = None) -> bool:
    if str(subscription.trial_status or "").strip().lower() != "active":
        return False
    trial_ends_at = _parse_iso_datetime(subscription.trial_ends_at)
    if trial_ends_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current < trial_ends_at


def _trial_entitlement(config: TrialConfig) -> Entitlement:
    base_plan_code = config.plan_code if config.plan_code in DEFAULT_ENTITLEMENTS else "growth"
    base = DEFAULT_ENTITLEMENTS[base_plan_code]
    if config.monthly_request_limit_override is None:
        return base
    request_limits = dict(base.request_limits)
    request_limits["monthly_requests"] = max(1, int(config.monthly_request_limit_override))
    return replace(base, request_limits=request_limits)

