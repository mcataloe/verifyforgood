from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from charity_status.scoring.weighting_profiles import resolve_weighting_profile


@dataclass(frozen=True)
class ScoreResult:
    scores: dict[str, Any]
    explanation: dict[str, Any]


MIN_PEER_GROUP_SIZE = 25


def calculate_v1_scores(
    record: dict[str, Any] | None,
    verification: dict[str, Any],
    ein_valid: bool,
    name_match: bool | None = None,
    filing_record: dict[str, Any] | None = None,
    metrics_record: dict[str, Any] | None = None,
    governance_record: dict[str, Any] | None = None,
    quality_record: dict[str, Any] | None = None,
    peer_group: dict[str, Any] | None = None,
    peer_stats: dict[str, Any] | None = None,
    min_peer_group_size: int = MIN_PEER_GROUP_SIZE,
    weighting_profile_id: str | None = None,
    fallback_invalid_weighting_profile: bool = True,
) -> ScoreResult:
    record = record or {}
    filing_record = filing_record or {}
    metrics_record = metrics_record or {}
    governance_record = governance_record or {}
    quality_record = quality_record or {}
    peer_group = peer_group or {}
    peer_stats = peer_stats or {}

    has_990 = any([filing_record, metrics_record, governance_record, quality_record])
    peer_group_size = _to_int(peer_stats.get("count"))
    use_peer = bool(peer_group) and peer_group_size is not None and peer_group_size >= min_peer_group_size

    active_status = verification.get("irs_status") == "active"
    revoked = bool(verification.get("revoked"))
    tax_period_present = verification.get("recent_990_on_file") is not None

    compliance = _bound(
        _weighted(
            [
                (ein_valid, 25),
                (bool(record), 25),
                (active_status, 20),
                (verification.get("tax_deductible") is not None, 10),
                (record.get("filing_req_cd") is not None, 10),
                (tax_period_present, 10),
            ]
        )
    )

    financial_resilience, benchmarked_metrics = _financial_resilience_score(metrics_record, peer_stats, use_peer)

    transparency = (
        _bound(
            _weighted(
                [
                    (tax_period_present, 20),
                    (governance_record.get("public_disclosure_available") is True, 20),
                    (filing_record.get("mission_description_present") is True, 15),
                    (filing_record.get("program_accomplishments_present") is True, 15),
                    (filing_record.get("leadership_disclosed") is True, 15),
                    (_to_bool(quality_record.get("narrativeMissing")) is False, 15),
                ]
            )
        )
        if bool(record)
        else None
    )

    trust_base = _weighted(
        [
            (compliance >= 70, 40),
            (transparency is not None and transparency >= 60, 20),
            (governance_record.get("material_diversion_reported") is False, 15),
            (governance_record.get("whistleblower_policy") is True, 10),
            (quality_record.get("scoreConfidence") == "high", 15),
        ]
    )
    trust = _bound(trust_base)

    weighting_profile, weighting_meta = resolve_weighting_profile(
        requested_profile_id=weighting_profile_id,
        fallback_to_default=fallback_invalid_weighting_profile,
    )
    dimension_scores = {
        "compliance": compliance,
        "trust": trust,
        "financial_resilience": financial_resilience,
        "transparency": transparency,
    }
    overall = _weighted_overall(dimension_scores, weighting_profile.weights)

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
        "stale_filing_days": _to_int(quality_record.get("staleFilingDays")),
        "name_match": name_match,
    }

    confidence = "low"
    present = sum(1 for v in factors.values() if v is not None and v is not False)
    if has_990 and present >= 8:
        confidence = "high"
    elif present >= 5:
        confidence = "medium"

    data_sources = ["irs_eo_bmf_athena"]
    notes: list[str] = []
    if has_990:
        data_sources.append("irs_form_990_xml")
        notes.append("Score incorporates IRS EO/BMF verification and parsed Form 990 data")
    else:
        notes.append("Score uses EO/BMF-style IRS data only; Form 990 enrichment unavailable")

    if use_peer:
        notes.append("Peer benchmarking applied for selected financial metrics")
    else:
        notes.append("Peer benchmarking not used due to sparse or unavailable peer data")

    notes.append("No third-party enrichment provider data included")

    explanation = {
        "model_version": "2.0.0",
        "score_data_sources": data_sources,
        "confidence": confidence,
        "factors": factors,
        "eligibility": eligibility,
        "peer_group": peer_group if peer_group else None,
        "peer_group_size": peer_group_size,
        "peer_benchmarking_used": use_peer,
        "benchmarked_metrics": benchmarked_metrics,
        "weighting_profile": {
            **weighting_meta,
            "weights": weighting_profile.weights,
            "description": weighting_profile.description,
        },
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


def _financial_resilience_score(metrics: dict[str, Any], peer_stats: dict[str, Any], use_peer: bool) -> tuple[int | None, list[str]]:
    if not metrics:
        return None, []

    benchmarked: list[str] = []
    components: list[int] = []

    peers = peer_stats.get("metrics") if isinstance(peer_stats, dict) else {}

    mapping = [
        ("programExpenseRatio", True, "program_expense_ratio"),
        ("liabilitiesToAssetsRatio", False, "liabilities_to_assets_ratio"),
        ("operatingMargin", True, "operating_margin"),
        ("monthsOfRunway", True, "months_of_runway"),
    ]

    for metric_key, higher_is_better, output_name in mapping:
        value = _to_float(metrics.get(metric_key))
        if value is None:
            continue

        if use_peer:
            peer_metric = peers.get(metric_key, {}) if isinstance(peers, dict) else {}
            peer_score = _peer_component_score(value, peer_metric, higher_is_better)
            if peer_score is not None:
                components.append(peer_score)
                benchmarked.append(output_name)
                continue

        components.append(_threshold_component_score(metric_key, value))

    if not components:
        return None, benchmarked
    return _bound(round(sum(components) / len(components))), benchmarked


def _peer_component_score(value: float, peer_metric: dict[str, Any], higher_is_better: bool) -> int | None:
    p25 = _to_float(peer_metric.get("p25"))
    p75 = _to_float(peer_metric.get("p75"))
    median = _to_float(peer_metric.get("median"))
    if p25 is None or p75 is None or median is None:
        return None

    if higher_is_better:
        if value >= p75:
            return 90
        if value >= median:
            return 75
        if value >= p25:
            return 60
        return 40

    if value <= p25:
        return 90
    if value <= median:
        return 75
    if value <= p75:
        return 60
    return 40


def _threshold_component_score(metric_key: str, value: float) -> int:
    if metric_key == "programExpenseRatio":
        return 90 if value >= 0.75 else 70 if value >= 0.6 else 50 if value >= 0.5 else 30
    if metric_key == "liabilitiesToAssetsRatio":
        return 90 if value <= 0.4 else 75 if value <= 0.6 else 55 if value <= 0.8 else 35
    if metric_key == "monthsOfRunway":
        return 90 if value >= 12 else 75 if value >= 6 else 55 if value >= 3 else 35
    if metric_key == "operatingMargin":
        return 90 if value >= 0.1 else 75 if value >= 0.02 else 55 if value >= -0.05 else 35
    return 50


def _weighted(weighted_conditions: list[tuple[bool, int]]) -> int:
    return sum(weight for condition, weight in weighted_conditions if condition)


def _weighted_overall(dimension_scores: dict[str, int | None], weights: dict[str, float]) -> int:
    weighted_sum = 0.0
    weight_total = 0.0
    for dimension, score in dimension_scores.items():
        if score is None:
            continue
        weight = float(weights.get(dimension, 0.0))
        if weight <= 0:
            continue
        weighted_sum += float(score) * weight
        weight_total += weight
    if weight_total <= 0:
        available = [value for value in dimension_scores.values() if value is not None]
        return round(sum(available) / len(available)) if available else 0
    return round(weighted_sum / weight_total)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
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
