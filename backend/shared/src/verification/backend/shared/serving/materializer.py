from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from verification.backend.shared.serving.hash import calculate_source_hash
from verification.backend.shared.serving.keys import profile_pk, profile_sk
from verification.backend.shared.serving.models import MaterializedProfile


def response_to_store_payload(response_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "organization": response_payload.get("organization"),
        "verification": response_payload.get("verification"),
        "scores": response_payload.get("scores"),
        "score_explanation": response_payload.get("score_explanation"),
        "latest_filing": response_payload.get("filing_summary"),
        "enrichment": response_payload.get("enrichment"),
        "integration_evaluation": response_payload.get("integration_evaluation"),
        "decision": response_payload.get("decision"),
        "summary": response_payload.get("summary"),
        "audit": response_payload.get("audit"),
        "evidence": response_payload.get("evidence"),
        "policy_evaluation": response_payload.get("policy_evaluation"),
        "final_recommendation": response_payload.get("final_recommendation"),
        "review": response_payload.get("review"),
        "state_compliance": response_payload.get("state_compliance"),
        "external_signals": response_payload.get("external_signals"),
    }


def materialize_profile_item(
    ein: str,
    response_payload: dict[str, Any],
    environment: str,
    source_data_versions: dict[str, Any],
) -> dict[str, Any]:
    source_input = {
        "ein": ein,
        "model_version": response_payload.get("score_explanation", {}).get("model_version"),
        "verification": response_payload.get("verification"),
        "scores": response_payload.get("scores"),
        "score_explanation": response_payload.get("score_explanation"),
        "filing_summary": response_payload.get("filing_summary"),
        "enrichment": response_payload.get("enrichment"),
        "integration_evaluation": response_payload.get("integration_evaluation"),
        "decision": response_payload.get("decision"),
        "review": response_payload.get("review"),
        "state_compliance": response_payload.get("state_compliance"),
        "external_signals": response_payload.get("external_signals"),
        "source_data_versions": source_data_versions,
    }

    profile = MaterializedProfile(
        pk=profile_pk(ein),
        sk=profile_sk(),
        ein=ein,
        organization=response_payload.get("organization") or {},
        verification=response_payload.get("verification") or {},
        scores=response_payload.get("scores") or {},
        score_explanation=response_payload.get("score_explanation") or {},
        latest_filing=response_payload.get("filing_summary"),
        enrichment=response_payload.get("enrichment"),
        integration_evaluation=response_payload.get("integration_evaluation"),
        decision=response_payload.get("decision"),
        summary=response_payload.get("summary"),
        audit=response_payload.get("audit"),
        evidence=response_payload.get("evidence"),
        policy_evaluation=response_payload.get("policy_evaluation"),
        final_recommendation=response_payload.get("final_recommendation"),
        review=response_payload.get("review"),
        state_compliance=response_payload.get("state_compliance"),
        external_signals=response_payload.get("external_signals"),
        model_version=response_payload.get("score_explanation", {}).get("model_version", "unknown"),
        source_hash=calculate_source_hash(source_input),
        materialized_at=datetime.now(timezone.utc).isoformat(),
        environment=environment,
        source_data_versions=source_data_versions,
    )
    return profile.to_item()

