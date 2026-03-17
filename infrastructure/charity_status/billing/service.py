from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from charity_status.api import normalize_route_key
from charity_status.billing.models import EntitlementSet, MonthlyQuotaPeriod, SubscriptionPlan


DEFAULT_PLANS: dict[str, SubscriptionPlan] = {
    "developer": SubscriptionPlan(
        plan_id="developer",
        monthly_request_limit=250,
        included_units=250,
        overage_unit_price_usd_micros=5000,
        entitlements=EntitlementSet(batch_verification=False, advanced_source_visibility=False, monitoring_change_events=False, premium_compliance_risk=False),
    ),
    "starter": SubscriptionPlan(
        plan_id="starter",
        monthly_request_limit=1000,
        included_units=1000,
        overage_unit_price_usd_micros=4000,
        entitlements=EntitlementSet(batch_verification=True, advanced_source_visibility=False, monitoring_change_events=False, premium_compliance_risk=False),
    ),
    "team": SubscriptionPlan(
        plan_id="team",
        monthly_request_limit=10000,
        included_units=10000,
        overage_unit_price_usd_micros=3000,
        entitlements=EntitlementSet(batch_verification=True, advanced_source_visibility=True, monitoring_change_events=False, premium_compliance_risk=True),
    ),
    "business": SubscriptionPlan(
        plan_id="business",
        monthly_request_limit=100000,
        included_units=100000,
        overage_unit_price_usd_micros=2000,
        entitlements=EntitlementSet(batch_verification=True, advanced_source_visibility=True, monitoring_change_events=True, premium_compliance_risk=True),
    ),
    "enterprise": SubscriptionPlan(
        plan_id="enterprise",
        monthly_request_limit=1000000,
        included_units=1000000,
        overage_unit_price_usd_micros=1000,
        entitlements=EntitlementSet(batch_verification=True, advanced_source_visibility=True, monitoring_change_events=True, premium_compliance_risk=True),
    ),
}

ROUTE_ENTITLEMENT_REQUIREMENTS: dict[str, str] = {
    "POST /v1/verify/batch": "batch_verification",
    "GET /v1/nonprofits/{ein}/sources": "advanced_source_visibility",
    "GET /v1/nonprofits/{ein}/sources/{source_name}": "advanced_source_visibility",
    "GET /v1/nonprofits/{ein}/federal-awards": "premium_compliance_risk",
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


def monthly_period_for(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y-%m")


def check_feature_entitlement(plan: SubscriptionPlan, route_key: str) -> bool:
    route_key = normalize_route_key(route_key)
    required = ROUTE_ENTITLEMENT_REQUIREMENTS.get(route_key)
    if not required:
        return True
    return bool(getattr(plan.entitlements, required, False))


def check_quota_and_calculate(
    *,
    plan: SubscriptionPlan,
    used_units: int,
    consumed_units: int,
    period_key: str,
) -> MeteringDecision:
    projected = used_units + max(0, consumed_units)
    limit = max(0, plan.monthly_request_limit)
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
        overage_cost_usd_micros=overage_units * max(0, plan.overage_unit_price_usd_micros),
    )


def quota_period_state(plan: SubscriptionPlan, used_units: int, period_key: str) -> MonthlyQuotaPeriod:
    limit = max(0, plan.monthly_request_limit)
    used = max(0, used_units)
    return MonthlyQuotaPeriod(period_key=period_key, limit_units=limit, used_units=used, remaining_units=max(0, limit - used))
