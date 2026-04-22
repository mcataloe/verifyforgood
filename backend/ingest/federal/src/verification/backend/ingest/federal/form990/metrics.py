from __future__ import annotations

from typing import Any


def compute_derived_metrics(financials: dict[str, Any], history: list[dict[str, Any]] | None = None) -> dict[str, float | None]:
    total_expenses = _num(financials.get("total_expenses"))
    total_revenue = _num(financials.get("total_revenue"))
    fundraising_expenses = _num(financials.get("fundraising_expenses"))
    total_assets = _num(financials.get("total_assets_eoy"))
    total_liabilities = _num(financials.get("total_liabilities_eoy"))

    working_capital = None
    if total_assets is not None and total_liabilities is not None:
        working_capital = total_assets - total_liabilities

    months_of_runway = None
    if working_capital is not None and total_expenses not in (None, 0):
        monthly_burn = total_expenses / 12
        if monthly_burn != 0:
            months_of_runway = working_capital / monthly_burn

    return {
        "programExpenseRatio": _safe_div(_num(financials.get("program_service_expenses")), total_expenses),
        "adminExpenseRatio": _safe_div(_num(financials.get("management_general_expenses")), total_expenses),
        "fundraisingRatio": _safe_div(fundraising_expenses, total_expenses),
        "liabilitiesToAssetsRatio": _safe_div(total_liabilities, total_assets),
        "operatingMargin": _safe_div(_safe_sub(total_revenue, total_expenses), total_revenue),
        "fundraisingEfficiency": _safe_div(_num(financials.get("contributions_revenue")), fundraising_expenses),
        "workingCapital": working_capital,
        "monthsOfRunway": months_of_runway,
    }


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _safe_sub(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right
