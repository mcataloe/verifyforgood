from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from charity_status.evidence.models import Evidence, EvidenceFactor, EvidenceRuleResult, EvidenceSource


def build_evidence(
    verification: dict[str, Any],
    scores: dict[str, Any],
    score_explanation: dict[str, Any],
    decision: dict[str, Any],
    enrichment: dict[str, Any] | None,
) -> dict[str, Any]:
    factors: list[EvidenceFactor] = []
    sources: list[EvidenceSource] = []
    rule_results: list[EvidenceRuleResult] = []

    eligibility = str(score_explanation.get("eligibility") or "UNKNOWN")
    confidence = str(score_explanation.get("confidence") or "low")
    model_version = str(score_explanation.get("model_version") or "unknown")
    score_factors = score_explanation.get("factors", {}) or {}
    data_sources = score_explanation.get("score_data_sources", []) or []
    enrichment_payload = enrichment or {"providers": [], "failures": []}
    enrichment_failures = enrichment_payload.get("failures", []) or []
    enrichment_providers = enrichment_payload.get("providers", []) or []

    factors.append(
        EvidenceFactor(
            key="eligibility_status",
            category="eligibility_compliance",
            polarity="positive" if eligibility == "ELIGIBLE" else "negative",
            severity="high" if eligibility != "ELIGIBLE" else "low",
            value=eligibility,
            message="Eligibility outcome derived from deterministic compliance checks.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="compliance_score",
            category="eligibility_compliance",
            polarity="positive" if _to_int(scores.get("compliance"), 0) >= 70 else "warning",
            severity="medium",
            value=scores.get("compliance"),
            message="Compliance dimension score from deterministic rule engine.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="financial_resilience_score",
            category="financial_resilience",
            polarity="positive" if _to_int(scores.get("financial_resilience"), 0) >= 60 else "warning",
            severity="medium",
            value=scores.get("financial_resilience"),
            message="Financial resilience based on ratio checks and peer context when available.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="transparency_score",
            category="transparency",
            polarity="positive" if _to_int(scores.get("transparency"), 0) >= 60 else "warning",
            severity="medium",
            value=scores.get("transparency"),
            message="Transparency score from filings, governance disclosures, and narrative completeness.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="governance_material_diversion",
            category="governance_quality",
            polarity="negative" if score_factors.get("material_diversion_reported") is True else "positive",
            severity="high" if score_factors.get("material_diversion_reported") is True else "low",
            value=score_factors.get("material_diversion_reported"),
            message="Material diversion indicator influences governance quality risk.",
        )
    )

    peer_used = bool(score_explanation.get("peer_benchmarking_used"))
    factors.append(
        EvidenceFactor(
            key="peer_benchmarking_used",
            category="peer_benchmarking",
            polarity="positive" if peer_used else "neutral",
            severity="low",
            value=peer_used,
            message="Peer benchmarking usage determined by deterministic minimum peer-group threshold.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="enrichment_failures",
            category="enrichment",
            polarity="warning" if enrichment_failures else "positive",
            severity="medium" if enrichment_failures else "low",
            value=len(enrichment_failures),
            message="External enrichment failures are tracked but do not break core scoring.",
        )
    )

    source_set = set(str(source) for source in data_sources)
    sources.append(EvidenceSource(source="irs_eo_bmf_athena", used="irs_eo_bmf_athena" in source_set, detail="Core EO/BMF source"))
    sources.append(EvidenceSource(source="irs_form_990_xml", used="irs_form_990_xml" in source_set, detail="Form 990 derived enrichments"))

    for provider in enrichment_providers:
        name = str(provider.get("provider") or provider.get("name") or "unknown_provider")
        sources.append(EvidenceSource(source=f"enrichment:{name}", used=True))

    for failure in enrichment_failures:
        name = str(failure.get("provider") or "unknown_provider")
        sources.append(EvidenceSource(source=f"enrichment:{name}", used=False, detail="Provider failure"))

    overall = _to_int(scores.get("overall"), 0)
    status = str(decision.get("status") or "")
    rule_results.append(
        EvidenceRuleResult(
            rule="overall_score_threshold",
            passed=overall >= 60,
            severity="medium",
            detail=f"overall={overall}",
        )
    )
    rule_results.append(
        EvidenceRuleResult(
            rule="active_status_required",
            passed=bool(verification.get("irs_status") == "active"),
            severity="high",
            detail=f"irs_status={verification.get('irs_status')}",
        )
    )
    rule_results.append(
        EvidenceRuleResult(
            rule="enrichment_provider_health",
            passed=len(enrichment_failures) == 0,
            severity="low",
            detail=f"failures={len(enrichment_failures)}",
        )
    )
    rule_results.append(
        EvidenceRuleResult(
            rule="decision_not_deny",
            passed=status != "deny",
            severity="high",
            detail=f"decision_status={status}",
        )
    )

    evidence = Evidence(
        factors=factors,
        sources=sources,
        rule_results=rule_results,
        confidence=confidence,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model_version=model_version,
    )
    return evidence.to_dict()


def _to_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
