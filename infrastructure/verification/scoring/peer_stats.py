from __future__ import annotations

from statistics import mean, median
from typing import Any


def compute_peer_stats(rows: list[dict[str, Any]], metric_fields: list[str]) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "count": len(rows),
        "metrics": {},
    }

    for field in metric_fields:
        values = [_to_float(row.get(field)) for row in rows]
        values = [value for value in values if value is not None]

        if not values:
            stats["metrics"][field] = {
                "count": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "p25": None,
                "p75": None,
            }
            continue

        sorted_values = sorted(values)
        stats["metrics"][field] = {
            "count": len(sorted_values),
            "mean": mean(sorted_values),
            "median": median(sorted_values),
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p25": _percentile(sorted_values, 0.25),
            "p75": _percentile(sorted_values, 0.75),
        }

    return stats


def _percentile(sorted_values: list[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]

    idx = q * (len(sorted_values) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = idx - lower
    return sorted_values[lower] * (1 - frac) + sorted_values[upper] * frac


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
