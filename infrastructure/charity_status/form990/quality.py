from __future__ import annotations

from datetime import date, datetime
from typing import Any


def compute_filing_quality(
    filing: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    history = history or []
    as_of = as_of or date.today()

    required = ["ein", "tax_year", "filing_date", "return_type", "total_revenue", "total_expenses", "total_assets_eoy"]
    missing_required = sum(1 for field in required if filing.get(field) is None)

    consistency_issues = 0
    total_assets = _num(filing.get("total_assets_eoy"))
    total_liabilities = _num(filing.get("total_liabilities_eoy"))
    net_assets = _num(filing.get("net_assets_eoy"))
    if total_assets is not None and total_liabilities is not None and net_assets is not None:
        if abs((total_assets - total_liabilities) - net_assets) > 1:
            consistency_issues += 1

    stale_days = _stale_days(filing.get("filing_date"), as_of)

    narrative_missing = len(filing.get("narrative_sections_missing") or []) > 0

    anomaly_flags = _anomaly_flags(filing, history)

    confidence = "high"
    if missing_required >= 3 or len(anomaly_flags) >= 2:
        confidence = "low"
    elif missing_required >= 1 or len(anomaly_flags) == 1:
        confidence = "medium"

    return {
        "missingRequiredFieldsCount": missing_required,
        "internalConsistencyIssuesCount": consistency_issues,
        "staleFilingDays": stale_days,
        "narrativeMissing": narrative_missing,
        "anomalyFlags": anomaly_flags,
        "scoreConfidence": confidence,
    }


def _anomaly_flags(filing: dict[str, Any], history: list[dict[str, Any]]) -> list[str]:
    flags: list[str] = []

    revenue = _num(filing.get("total_revenue"))
    expenses = _num(filing.get("total_expenses"))
    liabilities = _num(filing.get("total_liabilities_eoy"))
    program_expenses = _num(filing.get("program_service_expenses"))
    net_assets = _num(filing.get("net_assets_eoy"))

    previous = history[-1] if history else None
    if previous:
        prev_revenue = _num(previous.get("total_revenue"))
        prev_expenses = _num(previous.get("total_expenses"))
        prev_liabilities = _num(previous.get("total_liabilities_eoy"))

        if _swing_over_threshold(revenue, prev_revenue, 0.6):
            flags.append("large_revenue_swing")
        if _swing_over_threshold(expenses, prev_expenses, 0.6):
            flags.append("large_expense_swing")
        if _swing_over_threshold(liabilities, prev_liabilities, 0.75):
            flags.append("large_liabilities_jump")

    if expenses not in (None, 0) and (program_expenses is None or program_expenses == 0):
        flags.append("zero_program_expenses_with_nonzero_total")

    amended_recent = [item for item in history[-2:] if item.get("amended_return") is True]
    if filing.get("amended_return") is True and len(amended_recent) >= 1:
        flags.append("repeated_amended_return_pattern")

    net_assets_window = [item for item in history[-2:] if _num(item.get("net_assets_eoy")) is not None]
    if net_assets is not None and net_assets < 0 and len(net_assets_window) >= 1:
        if all((_num(item.get("net_assets_eoy")) or 0) < 0 for item in net_assets_window):
            flags.append("negative_net_assets_pattern")

    return sorted(set(flags))


def _swing_over_threshold(current: float | None, previous: float | None, threshold: float) -> bool:
    if current is None or previous is None or previous == 0:
        return False
    return abs((current - previous) / previous) > threshold


def _stale_days(filing_date_text: str | None, as_of: date) -> int | None:
    if not filing_date_text:
        return None
    try:
        filing_dt = datetime.fromisoformat(filing_date_text.replace("Z", "")).date()
    except ValueError:
        return None
    return (as_of - filing_dt).days


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
