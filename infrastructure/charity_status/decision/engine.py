from __future__ import annotations

from typing import Any

from charity_status.enrichments import annotate_integration_evaluation_payload, build_integration_policy_summary


def build_decision(
    organization: dict[str, Any],
    verification: dict[str, Any],
    scores: dict[str, Any],
    score_explanation: dict[str, Any],
    name_verification: dict[str, Any],
    filing_summary: dict[str, Any] | None,
    enrichment: dict[str, Any] | None,
    state_compliance: dict[str, Any] | None = None,
    external_signals: dict[str, Any] | None = None,
    integration_evaluation: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    reasons: list[str] = []
    risk_flags: list[str] = []
    manual_review_codes: list[str] = []
    manual_review_notes: list[str] = []
    next_actions: list[str] = []

    active = verification.get("irs_status") == "active"
    deductible = verification.get("tax_deductible") is True
    recent_filing = verification.get("recent_990_on_file") is True
    overall = _to_float(scores.get("overall"))
    eligibility = score_explanation.get("eligibility")
    confidence = score_explanation.get("confidence")

    if active:
        reasons.append("irs_active")
    else:
        manual_review_codes.append("inactive_or_unknown_status")
        manual_review_notes.append("IRS status is not active")

    if deductible:
        reasons.append("tax_deductible")

    if recent_filing:
        reasons.append("recent_filing_present")
    else:
        manual_review_codes.append("missing_or_stale_filing")
        manual_review_notes.append("Recent filing not confirmed")

    if name_verification.get("name_match") is False:
        manual_review_codes.append("ein_name_mismatch")
        manual_review_notes.append("Provided name does not confidently match IRS organization name")

    liabilities_ratio = _to_float(score_explanation.get("factors", {}).get("liabilities_to_assets_ratio"))
    if liabilities_ratio is not None and liabilities_ratio > 0.8:
        risk_flags.append("high_liabilities_to_assets")

    narrative_missing = score_explanation.get("factors", {}).get("narrative_missing")
    if narrative_missing is True:
        risk_flags.append("missing_governance_disclosures")
        manual_review_codes.append("missing_governance_disclosures")
        manual_review_notes.append("Narrative/governance disclosures are incomplete")

    if filing_summary is None:
        risk_flags.append("missing_filing_data")

    if confidence == "low":
        risk_flags.append("low_score_confidence")

    integration_evaluation = annotate_integration_evaluation_payload(integration_evaluation)
    integration_policy = integration_evaluation.get("summary") or build_integration_policy_summary(integration_evaluation)
    enrichment_failures = (enrichment or {}).get("failures", [])
    failure_integrations = integration_evaluation.get("failure_integrations") or []
    required_unmet_integrations = integration_evaluation.get("required_unmet_integrations") or []
    used_integrations = integration_evaluation.get("used_integrations") or []
    attempted_integrations = integration_evaluation.get("attempted_integrations") or []
    if required_unmet_integrations:
        risk_flags.append("required_integration_unavailable")
        manual_review_codes.append("required_integration_unavailable")
        manual_review_notes.append("One or more required third-party integrations were unavailable or returned no match")

    compliance_flags = (state_compliance or {}).get("compliance_flags") or []
    registration_status = (state_compliance or {}).get("registration_status")
    solicitation_permitted = (state_compliance or {}).get("solicitation_permitted")
    if compliance_flags:
        risk_flags.append("state_compliance_flags_present")
        manual_review_codes.append("state_compliance_review")
        manual_review_notes.append("State registry reported compliance flags")
    if registration_status and str(registration_status).lower() not in {"active", "good_standing"}:
        risk_flags.append("state_registration_not_active")
        manual_review_codes.append("state_registration_status_issue")
    if solicitation_permitted is False:
        risk_flags.append("state_solicitation_not_permitted")
        manual_review_codes.append("state_solicitation_restriction")

    external = external_signals or {}
    sanctions = external.get("sanctions") or {}
    state_business = external.get("state_business") or {}
    federal_awards = external.get("federal_awards") or {}
    if bool(sanctions.get("sanctions_match")):
        risk_flags.append("sanctions_match_detected")
        manual_review_codes.append("sanctions_screening_match")
        manual_review_notes.append("External sanctions screening returned a potential match")
    if state_business.get("entity_status") and str(state_business.get("entity_status")).lower() not in {"active", "good_standing"}:
        risk_flags.append("state_business_not_active")
        manual_review_codes.append("state_business_status_issue")
    if state_business.get("compliance_flags"):
        risk_flags.append("state_business_compliance_flags_present")
        manual_review_codes.append("state_business_compliance_review")

    status = "approve"

    if eligibility == "INELIGIBLE" and not active:
        status = "deny"
        risk_flags.append("ineligible_status")
        next_actions.append("deny automated approval")
        next_actions.append("request corrected legal/status documentation")
    elif eligibility == "INELIGIBLE":
        status = "deny"
        risk_flags.append("ineligible_status")
        next_actions.append("deny automated approval")
    elif overall is None:
        status = "insufficient_data"
        next_actions.append("obtain minimum required filing and verification data")
    elif overall < 45:
        status = "deny"
        next_actions.append("deny automated approval")
    elif overall < 60:
        status = "manual_review"
        next_actions.append("request manual review")
        next_actions.append("obtain latest supporting documents")
    elif required_unmet_integrations:
        status = "manual_review"
        next_actions.append("request manual review")
    elif manual_review_codes:
        status = "approve_with_review"
        next_actions.append("request manual review")
    elif confidence == "low":
        status = "manual_review"
        next_actions.append("request manual review")
    else:
        status = "approve"

    if status == "insufficient_data" and "missing_filing_data" not in risk_flags:
        risk_flags.append("insufficient_core_data")

    decision = {
        "status": status,
        "reasons": sorted(set(reasons)),
        "risk_flags": sorted(set(risk_flags)),
        "next_actions": _unique(next_actions),
        "manual_review": {
            "reason_codes": sorted(set(manual_review_codes)),
            "notes": _unique(manual_review_notes),
            "flags": sorted(set(risk_flags)),
        },
    }

    audit = {
        "data_sources_used": score_explanation.get("score_data_sources", []),
        "model_version": score_explanation.get("model_version"),
        "material_factors": {
            "active_status": score_explanation.get("factors", {}).get("active_status"),
            "program_expense_ratio": score_explanation.get("factors", {}).get("program_expense_ratio"),
            "liabilities_to_assets_ratio": score_explanation.get("factors", {}).get("liabilities_to_assets_ratio"),
            "narrative_missing": score_explanation.get("factors", {}).get("narrative_missing"),
            "name_match": score_explanation.get("factors", {}).get("name_match"),
            "state_registration_status": registration_status,
            "state_compliance_flags": compliance_flags,
            "state_solicitation_permitted": solicitation_permitted,
            "sanctions_match": sanctions.get("sanctions_match"),
            "state_business_entity_status": state_business.get("entity_status"),
            "federal_award_count": federal_awards.get("award_count"),
        },
        "peer_benchmarking_used": score_explanation.get("peer_benchmarking_used"),
        "peer_group": score_explanation.get("peer_group"),
        "peer_group_size": score_explanation.get("peer_group_size"),
        "weighting_profile": score_explanation.get("weighting_profile"),
        "enrichments_used": bool(used_integrations),
        "attempted_integrations": attempted_integrations,
        "used_integrations": used_integrations,
        "failure_integrations": failure_integrations,
        "integration_explanations": integration_evaluation.get("explanations") or [],
        "integration_policy": integration_policy,
        "required_unmet_integrations": required_unmet_integrations,
        "decision_basis": {
            "eligibility": eligibility,
            "overall_score": overall,
            "decision_status": status,
            "manual_review_reason_codes": decision["manual_review"]["reason_codes"],
            "state_compliance_flags_count": len(compliance_flags),
            "integration_policy_status": integration_policy.get("status"),
            "enrichment_failure_count": len(failure_integrations) or len(enrichment_failures),
        },
    }

    summary = {
        "ein": organization.get("ein"),
        "organization_name": organization.get("name"),
        "eligibility_status": "ELIGIBLE_WITH_REVIEW" if status in {"approve_with_review", "manual_review"} else ("INELIGIBLE" if status == "deny" else "ELIGIBLE"),
        "overall_score": overall,
        "decision_status": status,
        "integration_policy_status": integration_policy.get("status"),
    }

    return decision, {"audit": audit, "summary": summary}


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
