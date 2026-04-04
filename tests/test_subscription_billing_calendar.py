from __future__ import annotations

from datetime import datetime, timezone

from charity_status_platform.customer_accounts.billing_calendar import (
    billable_days_remaining,
    days_in_month,
    month_cycle_window,
    next_month_boundary,
    prorated_amount_cents,
    prorated_delta_amount_cents,
)


def test_month_cycle_window_is_full_month_on_first_day():
    effective_at = datetime(2026, 3, 1, tzinfo=timezone.utc)

    cycle_start, cycle_end = month_cycle_window(effective_at)

    assert cycle_start == "2026-03-01T00:00:00+00:00"
    assert cycle_end == "2026-04-01T00:00:00+00:00"
    assert prorated_amount_cents(9900, effective_at) == 9900


def test_proration_for_march_16_on_ninety_nine_dollar_plan():
    effective_at = datetime(2026, 3, 16, tzinfo=timezone.utc)

    assert days_in_month(effective_at) == 31
    assert billable_days_remaining(effective_at) == 16
    assert prorated_amount_cents(9900, effective_at) == 5110


def test_proration_for_last_day_of_month_bills_one_day():
    effective_at = datetime(2026, 3, 31, tzinfo=timezone.utc)

    assert billable_days_remaining(effective_at) == 1
    assert prorated_amount_cents(9900, effective_at) == 320


def test_proration_handles_non_leap_and_leap_february():
    non_leap = datetime(2025, 2, 28, tzinfo=timezone.utc)
    leap = datetime(2024, 2, 29, tzinfo=timezone.utc)

    assert days_in_month(non_leap) == 28
    assert prorated_amount_cents(9900, non_leap) == 354
    assert days_in_month(leap) == 29
    assert prorated_amount_cents(9900, leap) == 342


def test_prorated_delta_amount_uses_remaining_days_only():
    effective_at = datetime(2026, 3, 16, tzinfo=timezone.utc)

    assert prorated_delta_amount_cents(4900, 9900, effective_at) == 2581
    assert next_month_boundary(effective_at).isoformat() == "2026-04-01T00:00:00+00:00"
