from __future__ import annotations

from typing import Any


def revenue_band(total_revenue: float | int | None) -> str:
    if total_revenue is None:
        return "unknown"
    value = float(total_revenue)
    if value < 250_000:
        return "under_250k"
    if value < 1_000_000:
        return "250k_to_1m"
    if value < 10_000_000:
        return "1m_to_10m"
    if value < 100_000_000:
        return "10m_to_100m"
    return "100m_plus"


def assign_peer_group(
    ntee_code: str | None,
    org_type: str | None,
    total_revenue: float | int | None,
    state: str | None = None,
) -> dict[str, Any]:
    ntee = (ntee_code or "").strip().upper()
    ntee_group = ntee[0] if ntee else "unknown"
    org_group = (org_type or "unknown").strip() or "unknown"
    state_group = (state or "").strip().upper() or None

    return {
        "ntee": ntee_group,
        "org_type": org_group,
        "revenue_band": revenue_band(total_revenue),
        "state": state_group,
    }
