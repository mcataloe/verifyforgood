from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoreResult:
    scores: dict[str, Any]
    explanation: dict[str, Any]


def calculate_v1_scores(
    record: dict[str, Any] | None,
    verification: dict[str, Any],
    ein_valid: bool,
    name_match: bool | None = None,
    filing_record: dict[str, Any] | None = None,
    metrics_record: dict[str, Any] | None = None,
    governance_record: dict[str, Any] | None = None,
    quality_record: dict[str, Any] | None = None,
) -> ScoreResult:
    record = record or {}
    filing_record = filing_record or {}
    metrics_record = metrics_record or {}
    governance_record = governance_record or {}
    quality_record = quality_record or {}

    has_990 = any([filing_record, metrics_record, governance_record, quality_record])

    active_status = verification.get("irs_status") == "active"
    revoked = bool(verification.get("revoked"))
    tax_period_present = verification.get("recent_990_on_file") is not None

    compliance = _bound(
        _weighted([
            (ein_valid, 25),
            (bool(record), 25),
            (active_status, 20),
            (verification.get("tax_deductible") is not None, 10),
            (record.get("filing_req_cd") is not None, 10),
            (tax_period_present, 10),
        ])
    )

    financial_resilience = _financial_resilience_score(metrics_record)

    transparency = _bound(
        _weighted([
            (tax_period_present, 20),
            (governance_record.get("public_disclosure_available") is True, 20),
            (filing_record.get("mission_description_present") is True, 15),
            (filing_record.get("program_accomplishments_present") is True, 15),
            (filing_record.get("leadership_disclosed") is True, 15),
            (_to_bool(quality_record.get("narrativeMissing")) is False, 15),
        ])
    ) if bool(record) else None

    trust_base = _weighted([
        (compliance >= 70, 40),
        (transparency is not None and transparency >= 60, 20),
        (governance_record.get("material_diversion_reported") is False, 15),
        (governance_record.get("whistleblower_policy") is True, 10),
        (quality_record.get("scoreConfidence") == "high", 15),
    ])
    trust = _bound(trust_base)

    available = [v for v in [compliance, trust, transparency, financial_resilience] if v is not None]
    overall = round(sum(available) / len(available)) if available else 0

    eligibility = "ELIGIBLE"
    if not active_status:
        eligibility = "INELIGIBLE"
        overall = min(overall, 45)
    if revoked:
        eligibility = "INELIGIBLE"
        overall = min(overall, 30)

    factors = {
        "ein_valid": ein_valid,
        "record_found": bool(record),
        "active_status": active_status,
        "deductibility_present": verification.get("tax_deductible") is not None,
        "ntee_present": verification.get("ntee_category") is not None,
        "tax_period_present": tax_period_present,
        "program_expense_ratio": _to_float(metrics_record.get("programExpenseRatio")),
        "liabilities_to_assets_ratio": _to_float(metrics_record.get("liabilitiesToAssetsRatio")),
        "whistleblower_policy": governance_record.get("whistleblower_policy"),
        "material_diversion_reported": governance_record.get("material_diversion_reported"),
        "narrative_missing": quality_record.get("narrativeMissing"),
        "name_match": name_match,
    }

    confidence = "low"
    present = sum(1 for v in factors.values() if v is not None and v is not False)
    if has_990 and present >= 8:
        confidence = "high"
    elif present >= 5:
        confidence = "medium"

    data_sources = ["irs_eo_bmf_athena"]
    notes = []
    if has_990:
        data_sources.append("irs_form_990_xml")
        notes.append("Score incorporates IRS EO/BMF verification and parsed Form 990 data")
    else:
        notes.append("Score uses EO/BMF-style IRS data only; Form 990 enrichment unavailable")
    notes.append("No third-party enrichment provider data included")

    explanation = {
        "model_version": "1.1.0",
        "score_data_sources": data_sources,
        "confidence": confidence,
        "factors": factors,
        "eligibility": eligibility,
        "notes": notes,
    }

    return ScoreResult(
        scores={
            "overall": _bound(overall),
            "trust": trust,
            "financial_resilience": financial_resilience,
            "transparency": transparency,
            "compliance": compliance,
        },
        explanation=explanation,
    )


def _financial_resilience_score(metrics: dict[str, Any]) -> int | None:
    if not metrics:
        return None

    components: list[int] = []
    per = _to_float(metrics.get("programExpenseRatio"))
    if per is not None:
        components.append(90 if per >= 0.75 else 70 if per >= 0.6 else 50 if per >= 0.5 else 30)

    lta = _to_float(metrics.get("liabilitiesToAssetsRatio"))
    if lta is not None:
        components.append(90 if lta <= 0.4 else 75 if lta <= 0.6 else 55 if lta <= 0.8 else 35)

    runway = _to_float(metrics.get("monthsOfRunway"))
    if runway is not None:
        components.append(90 if runway >= 12 else 75 if runway >= 6 else 55 if runway >= 3 else 35)

    margin = _to_float(metrics.get("operatingMargin"))
    if margin is not None:
        components.append(90 if margin >= 0.1 else 75 if margin >= 0.02 else 55 if margin >= -0.05 else 35)

    stability = _to_float(metrics.get("revenueStability"))
    if stability is not None:
        components.append(90 if stability >= 0.8 else 70 if stability >= 0.5 else 45)

    if not components:
        return None
    return _bound(round(sum(components) / len(components)))


def _weighted(weighted_conditions: list[tuple[bool, int]]) -> int:
    return sum(weight for condition, weight in weighted_conditions if condition)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.lower()
        if lower in {"true", "1"}:
            return True
        if lower in {"false", "0"}:
            return False
    return None


def _bound(value: int) -> int:
    return min(max(int(value), 0), 100)
