from __future__ import annotations

from datetime import datetime, timezone

from charity_status.billing.service import DEFAULT_PLANS, check_feature_entitlement, check_quota_and_calculate, monthly_period_for, quota_period_state


def test_plan_entitlements():
    developer = DEFAULT_PLANS["developer"]
    team = DEFAULT_PLANS["team"]
    assert developer.entitlements.batch_verification is False
    assert team.entitlements.batch_verification is True
    assert team.entitlements.advanced_source_visibility is True


def test_quota_period_modeling_reset_key():
    jan = monthly_period_for(datetime(2026, 1, 15, tzinfo=timezone.utc))
    feb = monthly_period_for(datetime(2026, 2, 1, tzinfo=timezone.utc))
    assert jan == "2026-01"
    assert feb == "2026-02"


def test_overage_ready_calculation():
    plan = DEFAULT_PLANS["developer"]
    decision = check_quota_and_calculate(
        plan=plan,
        used_units=249,
        consumed_units=2,
        period_key="2026-03",
    )
    assert decision.projected_usage == 251
    assert decision.overage_units == 1
    assert decision.overage_cost_usd_micros == plan.overage_unit_price_usd_micros


def test_feature_gating():
    developer = DEFAULT_PLANS["developer"]
    assert check_feature_entitlement(developer, "POST /v1/verify/batch") is False
    assert check_feature_entitlement(developer, "GET /v1/nonprofit/{ein}") is True


def test_quota_period_state():
    plan = DEFAULT_PLANS["starter"]
    period = quota_period_state(plan, used_units=120, period_key="2026-03")
    assert period.limit_units == 1000
    assert period.remaining_units == 880
