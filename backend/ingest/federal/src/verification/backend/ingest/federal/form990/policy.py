from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class IngestPolicyConfig:
    mode: str
    incremental_year_window: int = 2
    target_years: tuple[str, ...] = ()
    reconciliation_enabled: bool = True
    reconciliation_cadence_days: int = 30
    last_reconciliation_at: str | None = None
    force_reconciliation: bool = False


def select_target_years(discovered_years: list[str], config: IngestPolicyConfig, now: datetime | None = None) -> tuple[list[str], dict[str, Any]]:
    current = now or datetime.now(timezone.utc)
    years = sorted({str(year).strip() for year in discovered_years if str(year).strip()})
    if not years:
        return [], {"effective_mode": config.mode, "reconciliation_due": False, "fallback_used": True}

    if config.mode == "bootstrap":
        return years, {"effective_mode": "bootstrap", "reconciliation_due": True, "fallback_used": False}

    if config.target_years:
        selected = [year for year in config.target_years if year in years]
        if selected:
            return sorted(set(selected)), {"effective_mode": "incremental", "reconciliation_due": False, "fallback_used": False}

    if _is_reconciliation_due(config, current):
        return years, {"effective_mode": "reconciliation", "reconciliation_due": True, "fallback_used": False}

    selected = _incremental_years(current.year, years, config.incremental_year_window)
    if selected:
        return selected, {"effective_mode": "incremental", "reconciliation_due": False, "fallback_used": False}

    # Safe fallback when year metadata is malformed/missing in source catalog.
    fallback = years[-min(len(years), max(1, config.incremental_year_window)) :]
    return fallback, {"effective_mode": "incremental", "reconciliation_due": False, "fallback_used": True}


def _is_reconciliation_due(config: IngestPolicyConfig, now: datetime) -> bool:
    if config.force_reconciliation:
        return True
    if not config.reconciliation_enabled:
        return False
    if not config.last_reconciliation_at:
        return False
    try:
        last = datetime.fromisoformat(config.last_reconciliation_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return now - last >= timedelta(days=max(1, config.reconciliation_cadence_days))


def _incremental_years(current_year: int, available_years: list[str], window: int) -> list[str]:
    candidates = {str(current_year - offset) for offset in range(max(1, window))}
    selected = [year for year in available_years if year in candidates]
    return sorted(set(selected))
