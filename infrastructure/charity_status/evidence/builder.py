from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from charity_status.enrichments import annotate_integration_evaluation_payload
from charity_status.evidence.models import Evidence, EvidenceFactor, EvidenceRuleResult, EvidenceSource


def build_evidence(
    verification: dict[str, Any],
    scores: dict[str, Any],
    score_explanation: dict[str, Any],
    decision: dict[str, Any],
    enrichment: dict[str, Any] | None,
    state_compliance: dict[str, Any] | None = None,
    external_signals: dict[str, Any] | None = None,
    integration_evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    factors: list[EvidenceFactor] = []
    sources: list[EvidenceSource] = []
    rule_results: list[EvidenceRuleResult] = []

    eligibility = str(score_explanation.get("eligibility") or "UNKNOWN")
    confidence = str(score_explanation.get("confidence") or "low")
    model_version = str(score_explanation.get("model_version") or "unknown")
    score_factors = score_explanation.get("factors", {}) or {}
    weighting_profile = score_explanation.get("weighting_profile") or {}
    data_sources = score_explanation.get("score_data_sources", []) or []
    enrichment_payload = enrichment or {"providers": [], "failures": []}
    compliance = state_compliance or {}
    external = external_signals or {}
    sanctions = external.get("sanctions") or {}
    federal_awards = external.get("federal_awards") or {}
    enrichment_failures = enrichment_payload.get("failures", []) or []
    enrichment_providers = enrichment_payload.get("providers", []) or []
    integration_payload = annotate_integration_evaluation_payload(integration_evaluation)
    integration_states = integration_payload.get("integrations", []) or []
    attempted_integrations = set(str(item) for item in integration_payload.get("attempted_integrations", []) or [])
    used_integrations = set(str(item) for item in integration_payload.get("used_integrations", []) or [])
    required_unmet_integrations = integration_payload.get("required_unmet_integrations", []) or []
    failure_integrations = set(str(item) for item in integration_payload.get("failure_integrations", []) or [])

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
            key="sanctions_match",
            category="risk",
            polarity="negative" if sanctions.get("sanctions_match") else "positive",
            severity="high" if sanctions.get("sanctions_match") else "low",
            value=bool(sanctions.get("sanctions_match")),
            message="Sanctions screening signal from OFAC-aligned provider adapters.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="federal_award_count",
            category="federal_awards",
            polarity="neutral",
            severity="low",
            value=federal_awards.get("award_count"),
            message="Federal awards visibility from USAspending adapter source.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="weighting_profile_applied",
            category="eligibility_compliance",
            polarity="neutral",
            severity="low",
            value=weighting_profile.get("applied"),
            message="Named deterministic weighting profile used for overall aggregation.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="state_registration_status",
            category="eligibility_compliance",
            polarity="positive" if str(compliance.get("registration_status") or "").lower() in {"active", "good_standing"} else "warning",
            severity="medium",
            value=compliance.get("registration_status"),
            message="State registry registration status when available.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="state_compliance_flags_count",
            category="governance_quality",
            polarity="warning" if (compliance.get("compliance_flags") or []) else "positive",
            severity="medium",
            value=len(compliance.get("compliance_flags") or []),
            message="Compliance flags from state registry enrichment.",
        )
    )
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
            polarity="warning" if failure_integrations & set(required_unmet_integrations) else "neutral",
            severity="medium" if failure_integrations & set(required_unmet_integrations) else "low",
            value=len(enrichment_failures),
            message="Third-party integration failures are recorded for auditability. Optional failures do not penalize evaluation unless requirement or policy settings make them material.",
        )
    )
    factors.append(
        EvidenceFactor(
            key="required_integrations_missing",
            category="enrichment",
            polarity="warning" if required_unmet_integrations else "neutral",
            severity="high" if required_unmet_integrations else "low",
            value=len(required_unmet_integrations),
            message="Required third-party integrations that were unavailable or returned no match.",
        )
    )

    for explanation in integration_payload.get("explanations", []) or []:
        effect = str(explanation.get("effect") or "neutral")
        factors.append(
            EvidenceFactor(
                key=f"integration_policy:{explanation.get('integration_id')}",
                category="enrichment",
                polarity="positive" if effect == "positive" else "warning" if effect == "warning" else "neutral",
                severity="medium" if effect == "warning" else "low",
                value=explanation.get("availability_status"),
                message=str(explanation.get("message") or ""),
            )
        )

    source_set = set(str(source) for source in data_sources)
    sources.append(EvidenceSource(source="irs.eo_bmf", used="irs.eo_bmf" in source_set, detail="Core EO/BMF source"))
    sources.append(EvidenceSource(source="irs_form_990_xml", used="irs_form_990_xml" in source_set, detail="Form 990 derived enrichments"))

    for provider in enrichment_providers:
        name = str(provider.get("integration_id") or provider.get("name") or "unknown_provider")
        sources.append(EvidenceSource(source=f"enrichment:{name}", used=name in used_integrations, detail=f"status={provider.get('status')}"))

    for failure in enrichment_failures:
        name = str(failure.get("integration_id") or failure.get("provider") or "unknown_provider")
        sources.append(EvidenceSource(source=f"enrichment:{name}", used=False, detail="Provider failure"))
    for state in integration_states:
        integration_id = str(state.get("integration_id") or "")
        if not integration_id or integration_id in attempted_integrations:
            continue
        if not state.get("tenant_enabled") and not state.get("required_for_eligibility"):
            continue
        sources.append(
            EvidenceSource(
                source=f"enrichment:{integration_id}",
                used=False,
                detail=f"status={state.get('availability_status')}",
            )
        )
    if compliance.get("source", {}).get("provider"):
        sources.append(EvidenceSource(source=f"state_compliance:{compliance['source']['provider']}", used=True))
    if sanctions.get("source"):
        sources.append(EvidenceSource(source=f"sanctions:{sanctions['source']}", used=True))
    if federal_awards.get("source"):
        sources.append(EvidenceSource(source=f"federal_awards:{federal_awards['source']}", used=True))

    overall = _to_int(scores.get("overall"), 0)
    status = str(decision.get("status") or "")
    rule_results.append(
        EvidenceRuleResult(
            rule="sanctions_clear",
            passed=not bool(sanctions.get("sanctions_match")),
            severity="high",
            detail=f"sanctions_match={bool(sanctions.get('sanctions_match'))}",
        )
    )
    rule_results.append(
        EvidenceRuleResult(
            rule="weighting_profile_valid",
            passed=bool(not weighting_profile.get("fallback_applied")),
            severity="low",
            detail=f"applied={weighting_profile.get('applied')}",
        )
    )
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
            rule="required_integrations_satisfied",
            passed=len(required_unmet_integrations) == 0,
            severity="high",
            detail=f"required_unmet={len(required_unmet_integrations)}",
        )
    )
    rule_results.append(
        EvidenceRuleResult(
            rule="state_compliance_flags_clear",
            passed=len(compliance.get("compliance_flags") or []) == 0,
            severity="medium",
            detail=f"flags={len(compliance.get('compliance_flags') or [])}",
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
