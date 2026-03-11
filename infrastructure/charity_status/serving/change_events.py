from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCORE_CHANGE_THRESHOLD = 10
STALE_FILING_DAYS_THRESHOLD = 365


@dataclass(frozen=True)
class ChangeEvent:
    ein: str
    change_types: list[str]
    previous: dict[str, Any]
    current: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ein": self.ein,
            "change_types": self.change_types,
            "previous": self.previous,
            "current": self.current,
        }


def build_change_event(
    ein: str,
    previous_item: dict[str, Any] | None,
    current_item: dict[str, Any],
    score_change_threshold: int = SCORE_CHANGE_THRESHOLD,
) -> dict[str, Any] | None:
    if not previous_item:
        return None

    previous = _snapshot(previous_item)
    current = _snapshot(current_item)
    change_types: list[str] = []

    if previous["eligibility"] != current["eligibility"]:
        change_types.append("eligibility_changed")
    if previous["decision_status"] != current["decision_status"]:
        change_types.append("decision_status_changed")

    old_score = _to_float(previous["overall_score"])
    new_score = _to_float(current["overall_score"])
    if old_score is not None and new_score is not None and abs(new_score - old_score) >= float(score_change_threshold):
        change_types.append("overall_score_threshold_crossed")

    previous_risk_flags = set(previous["risk_flags"])
    current_risk_flags = set(current["risk_flags"])
    if sorted(current_risk_flags - previous_risk_flags):
        change_types.append("new_risk_flags")

    if _filing_freshness_crossed(previous, current):
        change_types.append("filing_freshness_threshold_crossed")

    if previous["registration_status"] != current["registration_status"]:
        change_types.append("compliance_status_changed")
    previous_compliance_flags = set(previous["compliance_flags"])
    current_compliance_flags = set(current["compliance_flags"])
    if sorted(current_compliance_flags - previous_compliance_flags):
        change_types.append("new_compliance_flags")

    if not change_types:
        return None

    event = ChangeEvent(
        ein=ein,
        change_types=sorted(set(change_types)),
        previous=previous,
        current=current,
    )
    return event.to_dict()


def _snapshot(item: dict[str, Any]) -> dict[str, Any]:
    explanation = item.get("score_explanation") or {}
    decision = item.get("decision") or {}
    verification = item.get("verification") or {}
    state_compliance = item.get("state_compliance") or {}
    stale_days = (explanation.get("factors") or {}).get("stale_filing_days")
    return {
        "eligibility": explanation.get("eligibility"),
        "overall_score": (item.get("scores") or {}).get("overall"),
        "decision_status": decision.get("status"),
        "risk_flags": sorted(set(decision.get("risk_flags") or [])),
        "recent_990_on_file": verification.get("recent_990_on_file"),
        "stale_filing_days": _to_float(stale_days),
        "registration_status": state_compliance.get("registration_status"),
        "compliance_flags": sorted(set(state_compliance.get("compliance_flags") or [])),
    }


def _filing_freshness_crossed(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    old_days = previous.get("stale_filing_days")
    new_days = current.get("stale_filing_days")
    if old_days is not None and new_days is not None:
        old_stale = old_days > STALE_FILING_DAYS_THRESHOLD
        new_stale = new_days > STALE_FILING_DAYS_THRESHOLD
        return old_stale != new_stale
    return previous.get("recent_990_on_file") != current.get("recent_990_on_file")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
