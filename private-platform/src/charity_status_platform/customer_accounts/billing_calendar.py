from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ProrationDetail:
    amount_cents: int
    billable_days: int
    days_in_month: int


def month_cycle_window(effective_at: datetime) -> tuple[str, str]:
    start = _normalize_datetime(effective_at)
    end = next_month_boundary(start)
    return _to_iso(start), _to_iso(end)


def days_in_month(effective_at: datetime) -> int:
    current = _normalize_datetime(effective_at)
    return monthrange(current.year, current.month)[1]


def billable_days_remaining(effective_at: datetime) -> int:
    current = _normalize_datetime(effective_at)
    return days_in_month(current) - current.day + 1


def prorated_amount_cents(monthly_price_cents: int, effective_at: datetime) -> int:
    current = _normalize_datetime(effective_at)
    return _ceil_div(max(0, int(monthly_price_cents)) * billable_days_remaining(current), days_in_month(current))


def prorated_delta_amount_cents(
    old_monthly_price_cents: int,
    new_monthly_price_cents: int,
    effective_at: datetime,
) -> int:
    current = _normalize_datetime(effective_at)
    delta = max(0, int(new_monthly_price_cents) - int(old_monthly_price_cents))
    return _ceil_div(delta * billable_days_remaining(current), days_in_month(current))


def prorated_quota_delta(old_limit: int, new_limit: int, effective_at: datetime) -> int:
    current = _normalize_datetime(effective_at)
    delta = max(0, int(new_limit) - int(old_limit))
    return _ceil_div(delta * billable_days_remaining(current), days_in_month(current))


def next_month_boundary(effective_at: datetime) -> datetime:
    current = _normalize_datetime(effective_at)
    if current.month == 12:
        return datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)


def proration_detail(monthly_price_cents: int, effective_at: datetime) -> ProrationDetail:
    current = _normalize_datetime(effective_at)
    return ProrationDetail(
        amount_cents=prorated_amount_cents(monthly_price_cents, current),
        billable_days=billable_days_remaining(current),
        days_in_month=days_in_month(current),
    )


def _normalize_datetime(value: datetime) -> datetime:
    current = value
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0)


def _to_iso(value: datetime) -> str:
    return _normalize_datetime(value).isoformat()


def _ceil_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    return (numerator + denominator - 1) // denominator


__all__ = [
    "ProrationDetail",
    "billable_days_remaining",
    "days_in_month",
    "month_cycle_window",
    "next_month_boundary",
    "prorated_amount_cents",
    "prorated_delta_amount_cents",
    "prorated_quota_delta",
    "proration_detail",
]
