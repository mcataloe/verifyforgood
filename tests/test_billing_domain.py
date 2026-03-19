from __future__ import annotations

from datetime import datetime, timezone

from charity_status.billing import DEFAULT_ENTITLEMENTS, EntitlementService, Subscription
from charity_status.billing.service import check_feature_entitlement, check_quota_and_calculate, monthly_period_for, quota_period_state


def test_plan_entitlements():
    free = DEFAULT_ENTITLEMENTS["free"]
    growth = DEFAULT_ENTITLEMENTS["growth"]
    assert free.has_feature("financial_trends") is False
    assert growth.has_feature("financial_trends") is True
    assert growth.has_feature("benchmarking") is True


def test_quota_period_modeling_reset_key():
    jan = monthly_period_for(datetime(2026, 1, 15, tzinfo=timezone.utc))
    feb = monthly_period_for(datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert jan == "2026-01"
    assert feb == "2026-02"


def test_overage_ready_calculation():
    entitlement = DEFAULT_ENTITLEMENTS["free"]
    decision = check_quota_and_calculate(
        plan=entitlement,
        used_units=249,
        consumed_units=2,
        period_key="2026-03",
    )
    assert decision.projected_usage == 251
    assert decision.overage_units == 1
    assert decision.overage_cost_usd_micros == entitlement.overage_unit_price_usd_micros


def test_feature_gating():
    free = DEFAULT_ENTITLEMENTS["free"]
    assert check_feature_entitlement(free, "POST /v1/verify/batch") is False
    assert check_feature_entitlement(free, "GET /v1/nonprofit/{ein}") is True


def test_quota_period_state():
    entitlement = DEFAULT_ENTITLEMENTS["starter"]
    period = quota_period_state(entitlement, used_units=120, period_key="2026-03")
    assert period.limit_units == 1000
    assert period.remaining_units == 880


def test_entitlement_service_resolves_inactive_subscription_to_free():
    service = EntitlementService(
        subscriptions={
            "acct_1": Subscription(
                account_id="acct_1",
                plan_code="pro",
                status="canceled",
                effective_from="2026-01-01T00:00:00+00:00",
                effective_to="2026-02-01T00:00:00+00:00",
            )
        }
    )

    resolved = service.resolve(account_id="acct_1", now=datetime(2026, 3, 1, tzinfo=timezone.utc))

    assert resolved.subscription.plan_code == "free"
    assert resolved.entitlements.monthly_request_limit == 250


def test_entitlement_service_keeps_current_plan_during_pending_downgrade():
    service = EntitlementService(
        subscriptions={
            "acct_1": Subscription(
                account_id="acct_1",
                plan_code="pro",
                status="active",
                billing_status="active",
                pending_plan_code="growth",
                pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            )
        }
    )

    resolved = service.resolve(account_id="acct_1", now=datetime(2026, 3, 15, tzinfo=timezone.utc))

    assert resolved.subscription.plan_code == "pro"
    assert resolved.entitlements.monthly_request_limit == 100000
