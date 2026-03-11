from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreResult:
    scores: dict[str, Any]
    explanation: dict[str, Any]


def calculate_v1_scores(record: dict[str, Any] | None, verification: dict[str, Any], ein_valid: bool) -> ScoreResult:
    record = record or {}

    factors = {
        "ein_valid": ein_valid,
        "record_found": bool(record),
        "status_present": verification.get("irs_status") in {"active", "inactive"},
        "deductibility_present": verification.get("tax_deductible") is not None,
        "ntee_present": verification.get("ntee_category") is not None,
        "tax_period_present": verification.get("recent_990_on_file") is not None,
        "financial_fields_present": any(record.get(field) for field in ["asset_amt", "income_amt", "revenue_amt"]),
    }

    compliance = _score_from_bools(
        100,
        [
            (factors["ein_valid"], 35),
            (factors["record_found"], 35),
            (factors["status_present"], 15),
            (factors["deductibility_present"], 15),
        ],
    )
    trust = _score_from_bools(
        100,
        [
            (factors["record_found"], 40),
            (verification.get("irs_status") == "active", 35),
            (factors["deductibility_present"], 15),
            (factors["ntee_present"], 10),
        ],
    )
    transparency = _score_from_bools(
        100,
        [
            (factors["status_present"], 30),
            (factors["deductibility_present"], 20),
            (factors["ntee_present"], 20),
            (factors["tax_period_present"], 30),
        ],
    ) if factors["record_found"] else None

    financial_resilience = 50 if factors["financial_fields_present"] else None

    available_scores = [s for s in [compliance, trust, transparency, financial_resilience] if s is not None]
    overall = round(sum(available_scores) / len(available_scores)) if available_scores else 0

    confidence = "low"
    present_count = sum(1 for value in factors.values() if value)
    if present_count >= 6:
        confidence = "high"
    elif present_count >= 4:
        confidence = "medium"

    explanation = {
        "factors": factors,
        "confidence": confidence,
        "notes": [
            "Score is based only on EO/BMF-style IRS data",
            "Full 990-based financial and governance scoring not yet implemented",
        ],
    }

    return ScoreResult(
        scores={
            "overall": overall,
            "trust": trust,
            "financial_resilience": financial_resilience,
            "transparency": transparency,
            "compliance": compliance,
        },
        explanation=explanation,
    )


def _score_from_bools(max_score: int, weighted_conditions: list[tuple[bool, int]]) -> int:
    score = 0
    for condition, weight in weighted_conditions:
        if condition:
            score += weight
    return min(max(score, 0), max_score)
