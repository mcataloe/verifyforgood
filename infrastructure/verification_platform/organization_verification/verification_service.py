from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from charity_status.decision import build_decision
from charity_status.enrichments import EvaluationContext, annotate_integration_evaluation_payload, build_integration_policy_summary
from charity_status.enrichments.external_signals import extract_external_signals
from charity_status.evidence import build_evidence
from charity_status.normalization import compare_names
from charity_status.policy import evaluate_policy
from charity_status.scoring import assign_peer_group, calculate_v1_scores
from verification_platform.compliance_data.interpretation import interpret_jurisdiction_compliance
from verification_platform.organization_verification.organization_lookup import map_organization_record


@dataclass(frozen=True)
class OrganizationVerificationInput:
    ein: str
    provided_name: str | None = None
    subsection: str | None = None
    policy_id: str | None = None
    weighting_profile: str | None = None


def verify_organization(
    client: Any,
    verification_input: OrganizationVerificationInput,
    enrichment_service: Any | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> tuple[int, dict[str, Any]]:
    query_execution_id, record = client.lookup_nonprofit(verification_input.ein, subsection=verification_input.subsection)

    if not record:
        return 404, {"message": "Nonprofit not found", "ein": verification_input.ein}

    mapped = map_organization_record(verification_input.ein, record)
    name_check = compare_names(verification_input.provided_name, mapped.organization.get("name"))

    filings, metrics, governance, quality = client.lookup_form990_enrichment(verification_input.ein)
    peer_group = assign_peer_group(
        ntee_code=record.get("ntee_cd"),
        org_type=record.get("subsection"),
        total_revenue=_to_float((filings or {}).get("total_revenue")),
        state=record.get("state"),
    )
    peer_stats = client.lookup_peer_benchmark(peer_group)

    score_result = calculate_v1_scores(
        record=record,
        verification=mapped.verification,
        ein_valid=True,
        name_match=name_check.get("name_match"),
        filing_record=filings,
        metrics_record=metrics,
        governance_record=governance,
        quality_record=quality,
        peer_group=peer_group,
        peer_stats=peer_stats,
        weighting_profile_id=verification_input.weighting_profile,
    )

    payload = mapped.to_dict()
    payload["scores"] = score_result.scores
    payload["score_explanation"] = score_result.explanation
    payload["name_verification"] = name_check
    payload["queryExecutionId"] = query_execution_id
    if filings:
        payload["filing_summary"] = {
            "tax_year": filings.get("tax_year"),
            "form_type": filings.get("return_type"),
            "filing_date": filings.get("filing_date"),
            "amended": _to_bool(filings.get("amended_return")),
            "parse_status": filings.get("parse_status"),
        }
    payload = apply_verification_overlay(
        payload=payload,
        policy_id=verification_input.policy_id,
        enrichment_service=enrichment_service,
        evaluation_context=evaluation_context,
        ein=verification_input.ein,
    )
    return 200, payload


def apply_verification_overlay(
    *,
    payload: dict[str, Any],
    policy_id: str | None,
    enrichment_service: Any | None,
    evaluation_context: EvaluationContext | None = None,
    ein: str | None = None,
) -> dict[str, Any]:
    context = evaluation_context or EvaluationContext()
    organization_name = ((payload.get("organization") or {}).get("name"))
    subject_ein = str(ein or (payload.get("organization") or {}).get("ein") or "")
    existing_state_compliance = payload.get("state_compliance") or {}
    existing_external_signals = payload.get("external_signals") or {}

    if enrichment_service is not None and subject_ein:
        enrichment = _enrich_payload(
            enrichment_service=enrichment_service,
            ein=subject_ein,
            organization_name=organization_name,
            jurisdiction_state=str((payload.get("verification") or {}).get("state") or "").strip() or None,
            evaluation_context=context,
        )
    else:
        enrichment = {"providers": [], "failures": [], "integration_evaluation": _default_integration_evaluation(context)}

    payload["enrichment"] = enrichment
    payload["integration_evaluation"] = annotate_integration_evaluation_payload(
        enrichment.get("integration_evaluation") or _legacy_integration_evaluation(enrichment, context)
    )
    payload["score_explanation"] = {
        **(payload.get("score_explanation") or {}),
        "integration_policy": {
            **build_integration_policy_summary(payload["integration_evaluation"]),
            "explanations": payload["integration_evaluation"].get("explanations") or [],
        },
    }
    if (
        not (payload["integration_evaluation"].get("attempted_integrations") or [])
        and not context.has_non_default_integrations()
        and (existing_state_compliance or existing_external_signals)
    ):
        payload["state_compliance"] = existing_state_compliance
        payload["external_signals"] = existing_external_signals
    else:
        payload["state_compliance"] = interpret_jurisdiction_compliance(payload.get("enrichment"))
        payload["external_signals"] = extract_external_signals(payload.get("enrichment"))

    decision, extras = build_decision(
        organization=payload["organization"],
        verification=payload["verification"],
        scores=payload["scores"],
        score_explanation=payload["score_explanation"],
        name_verification=payload.get("name_verification") or {},
        filing_summary=payload.get("filing_summary"),
        enrichment=payload.get("enrichment"),
        state_compliance=payload.get("state_compliance"),
        external_signals=payload.get("external_signals"),
        integration_evaluation=payload.get("integration_evaluation"),
    )
    payload["decision"] = decision
    payload["audit"] = extras["audit"]
    payload["summary"] = extras["summary"]
    payload["evidence"] = build_evidence(
        verification=payload["verification"],
        scores=payload["scores"],
        score_explanation=payload["score_explanation"],
        decision=payload["decision"],
        enrichment=payload.get("enrichment"),
        state_compliance=payload.get("state_compliance"),
        external_signals=payload.get("external_signals"),
        integration_evaluation=payload.get("integration_evaluation"),
    )
    payload["policy_evaluation"] = evaluate_policy(payload, policy_id)
    payload["final_recommendation"] = payload["policy_evaluation"]["final_recommendation"]
    return payload


def _default_integration_evaluation(context: EvaluationContext) -> dict[str, Any]:
    integrations = []
    required_unmet = []
    for integration_id in context.integration_ids():
        setting = context.setting_for(integration_id)
        state = {
            "integration_id": integration_id,
            "offered": False,
            "credentials_present": False,
            "tenant_enabled": setting.enabled,
            "required_for_eligibility": setting.required_for_eligibility,
            "attempted": False,
            "availability_status": "not_offered",
            "requirement_status": "unmet" if setting.required_for_eligibility else "not_required",
            "driver": "none",
        }
        integrations.append(state)
        if setting.required_for_eligibility:
            required_unmet.append(integration_id)
    return {
        "integrations": integrations,
        "attempted_integrations": [],
        "used_integrations": [],
        "required_unmet_integrations": required_unmet,
        "failure_integrations": [],
    }


def _legacy_integration_evaluation(enrichment: dict[str, Any], context: EvaluationContext) -> dict[str, Any]:
    providers = enrichment.get("providers") or []
    integrations = []
    attempted = []
    used = []
    failure_integrations = []

    for provider in providers:
        integration_id = _provider_integration_id(provider)
        status = str(provider.get("status") or "")
        attempted.append(integration_id)
        if status == "matched":
            used.append(integration_id)
        if status == "failed":
            failure_integrations.append(integration_id)
        integrations.append(
            {
                "integration_id": integration_id,
                "offered": True,
                "credentials_present": status != "disabled",
                "tenant_enabled": True,
                "required_for_eligibility": False,
                "attempted": status != "disabled",
                "availability_status": status or "unknown",
                "requirement_status": "not_required",
                "driver": _provider_driver(provider),
                "provider_name": provider.get("name"),
                "error": provider.get("error"),
            }
        )

    if providers:
        return {
            "integrations": integrations,
            "attempted_integrations": sorted(set(attempted)),
            "used_integrations": sorted(set(used)),
            "required_unmet_integrations": [],
            "failure_integrations": sorted(set(failure_integrations)),
        }
    return _default_integration_evaluation(context)


def _enrich_payload(
    *,
    enrichment_service: Any,
    ein: str,
    organization_name: str | None,
    jurisdiction_state: str | None,
    evaluation_context: EvaluationContext,
) -> dict[str, Any]:
    try:
        result = enrichment_service.enrich(
            ein=ein,
            organization_name=organization_name,
            evaluation_context=evaluation_context,
            jurisdiction_state=jurisdiction_state,
        )
    except TypeError:
        result = enrichment_service.enrich(ein=ein, organization_name=organization_name)
    return result.to_dict()


def _provider_integration_id(provider: dict[str, Any]) -> str:
    name = str(provider.get("integration_id") or provider.get("name") or "").strip()
    if name.endswith("_mock"):
        return name.removesuffix("_mock")
    return name


def _provider_driver(provider: dict[str, Any]) -> str:
    driver = str(provider.get("driver") or "").strip()
    if driver:
        return driver
    name = str(provider.get("name") or "")
    return "mock" if name.endswith("_mock") or name == "mock_provider" else "live"


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1"}:
            return True
        if lowered in {"false", "0"}:
            return False
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


VerificationInput = OrganizationVerificationInput
verify_nonprofit = verify_organization
apply_evaluation_overlay = apply_verification_overlay


__all__ = [
    "OrganizationVerificationInput",
    "VerificationInput",
    "apply_evaluation_overlay",
    "apply_verification_overlay",
    "verify_nonprofit",
    "verify_organization",
]
