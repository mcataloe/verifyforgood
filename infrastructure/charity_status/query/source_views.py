from __future__ import annotations

from typing import Any

from charity_status.enrichments import EvaluationContext, annotate_integration_evaluation_payload
from charity_status.enrichments.compliance import extract_state_compliance
from charity_status.enrichments.external_signals import extract_external_signals
from charity_status.query.nonprofit_lookup import map_nonprofit_record


def get_nonprofit_sources_view(
    client: Any,
    enrichment_service: Any,
    ein: str,
    subsection: str | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> tuple[int, dict[str, Any]]:
    _, record = client.lookup_nonprofit(ein, subsection=subsection)
    if not record:
        return 404, {"message": "Nonprofit not found", "ein": ein}

    mapped = map_nonprofit_record(ein, record).to_dict()
    enrichment = _enrich_payload(
        enrichment_service=enrichment_service,
        ein=ein,
        organization_name=mapped["organization"].get("name"),
        jurisdiction_state=str(mapped["verification"].get("state") or "").strip() or None,
        evaluation_context=evaluation_context,
    )
    providers = enrichment.get("providers") or []
    failures = enrichment.get("failures") or []
    integration_evaluation = annotate_integration_evaluation_payload(
        enrichment.get("integration_evaluation") or _legacy_integration_evaluation(providers, failures)
    )

    sources = _to_sources(
        providers=providers,
        failures=failures,
        integration_evaluation=integration_evaluation,
    )
    return 200, {
        "ein": ein,
        "organization": {
            "ein": mapped["organization"].get("ein"),
            "name": mapped["organization"].get("name"),
            "state": mapped["verification"].get("state"),
        },
        "sources": sources,
        "failures": failures,
    }


def get_nonprofit_single_source_view(
    client: Any,
    enrichment_service: Any,
    ein: str,
    source_name: str,
    subsection: str | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> tuple[int, dict[str, Any]]:
    status, payload = get_nonprofit_sources_view(
        client,
        enrichment_service,
        ein,
        subsection=subsection,
        evaluation_context=evaluation_context,
    )
    if status != 200:
        return status, payload

    normalized_name = source_name.strip().lower()
    sources = payload.get("sources") or []
    match = next((source for source in sources if str(source.get("source_name", "")).lower() == normalized_name), None)
    legacy_alias_used = False
    if match is None and normalized_name.endswith("_mock"):
        legacy_name = normalized_name.removesuffix("_mock")
        match = next((source for source in sources if str(source.get("source_name", "")).lower() == legacy_name), None)
        legacy_alias_used = match is not None
    if match is None:
        return 404, {"message": f"Unsupported source name: {source_name}", "ein": ein}
    if legacy_alias_used:
        match = {**match, "source_name": normalized_name}
    return 200, {"ein": ein, "source": match}


def get_nonprofit_compliance_view(
    client: Any,
    enrichment_service: Any,
    ein: str,
    subsection: str | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> tuple[int, dict[str, Any]]:
    status, payload = get_nonprofit_sources_view(
        client,
        enrichment_service,
        ein,
        subsection=subsection,
        evaluation_context=evaluation_context,
    )
    if status != 200:
        return status, payload

    enrichment = {"providers": [_to_legacy_provider_shape(source) for source in payload.get("sources", [])]}
    state_compliance = extract_state_compliance(enrichment)
    external_signals = extract_external_signals(enrichment)
    state_business = external_signals.get("state_business") or {}

    summary = {
        "registration_status": _first_present(payload.get("sources", []), "registration_status", state_compliance.get("registration_status")),
        "registration_jurisdiction": _first_present(payload.get("sources", []), "registration_jurisdiction", state_compliance.get("registration_jurisdiction")),
        "registration_expiration_date": _first_present(payload.get("sources", []), "registration_expiration_date", state_compliance.get("registration_expiration_date")),
        "solicitation_permitted": _first_present(payload.get("sources", []), "solicitation_permitted", state_compliance.get("solicitation_permitted")),
        "compliance_flags": sorted(set((state_compliance.get("compliance_flags") or []) + (state_business.get("compliance_flags") or []))),
        "state_business_status": state_business.get("entity_status"),
        "state_business_good_standing": state_business.get("good_standing"),
        "status": "available" if state_compliance.get("registration_status") or state_business.get("entity_status") else "unavailable",
    }
    return 200, {"ein": ein, "compliance": summary, "sources": payload.get("sources", [])}


def get_nonprofit_federal_awards_view(
    client: Any,
    enrichment_service: Any,
    ein: str,
    subsection: str | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> tuple[int, dict[str, Any]]:
    status, payload = get_nonprofit_sources_view(
        client,
        enrichment_service,
        ein,
        subsection=subsection,
        evaluation_context=evaluation_context,
    )
    if status != 200:
        return status, payload

    enrichment = {"providers": [_to_legacy_provider_shape(source) for source in payload.get("sources", [])]}
    external_signals = extract_external_signals(enrichment)
    awards = external_signals.get("federal_awards") or {}
    summary = {
        "award_count": awards.get("award_count"),
        "total_obligations_usd": awards.get("total_obligations_usd"),
        "latest_award_date": awards.get("latest_award_date"),
        "status": "available" if awards.get("award_count") is not None else "unavailable",
        "source": awards.get("source"),
    }
    return 200, {"ein": ein, "federal_awards": summary}


def _to_sources(
    *,
    providers: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    integration_evaluation: dict[str, Any],
) -> list[dict[str, Any]]:
    provider_by_integration = {
        _provider_integration_id(provider): provider
        for provider in providers
        if _provider_integration_id(provider)
    }
    failure_by_integration = {
        str(failure.get("integration_id") or failure.get("provider") or "").replace("_mock", ""): failure
        for failure in failures
        if str(failure.get("integration_id") or failure.get("provider") or "").strip()
    }

    entries: list[dict[str, Any]] = []
    for state in integration_evaluation.get("integrations", []) or []:
        integration_id = str(state.get("integration_id") or "")
        if not integration_id:
            continue
        if not state.get("attempted") and not state.get("tenant_enabled") and not state.get("required_for_eligibility"):
            continue
        provider = provider_by_integration.get(integration_id, {})
        failure = failure_by_integration.get(integration_id, {})
        source = provider.get("source") or {}
        entries.append(
            {
                "source_name": integration_id,
                "status": state.get("availability_status"),
                "normalized_data": provider.get("fields") or {},
                "attribution": {
                    "record_id": source.get("record_id"),
                    "licensed": source.get("licensed"),
                    "notes": source.get("notes"),
                },
                "freshness": {
                    "retrieved_at": source.get("fetched_at") or provider.get("fetched_at"),
                },
                "error": failure.get("error") or state.get("error") or provider.get("error"),
                "driver": state.get("driver"),
                "tenant_enabled": state.get("tenant_enabled"),
                "required_for_eligibility": state.get("required_for_eligibility"),
                "integration_id": integration_id,
                "evaluation_effect": state.get("evaluation_effect"),
                "explanation_code": state.get("explanation_code"),
                "explanation": state.get("explanation"),
            }
        )
    return entries


def _to_legacy_provider_shape(source_entry: dict[str, Any]) -> dict[str, Any]:
    freshness = source_entry.get("freshness") or {}
    attribution = source_entry.get("attribution") or {}
    return {
        "name": source_entry.get("source_name"),
        "integration_id": source_entry.get("integration_id") or source_entry.get("source_name"),
        "status": source_entry.get("status"),
        "fields": source_entry.get("normalized_data") or {},
        "source": {
            "record_id": attribution.get("record_id"),
            "fetched_at": freshness.get("retrieved_at"),
            "licensed": attribution.get("licensed"),
            "notes": attribution.get("notes"),
        },
        "error": source_entry.get("error"),
    }


def _first_present(sources: list[dict[str, Any]], field: str, fallback: Any) -> Any:
    for source in sources:
        normalized = source.get("normalized_data") or {}
        if isinstance(normalized, dict) and normalized.get(field) is not None:
            return normalized.get(field)
    return fallback


def _enrich_payload(
    *,
    enrichment_service: Any,
    ein: str,
    organization_name: str | None,
    jurisdiction_state: str | None,
    evaluation_context: EvaluationContext | None,
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


def _legacy_integration_evaluation(providers: list[dict[str, Any]], failures: list[dict[str, Any]]) -> dict[str, Any]:
    integrations = []
    attempted = []
    used = []
    failure_integrations = []
    failure_by_id = {
        str(item.get("integration_id") or item.get("provider") or ""): item
        for item in failures
        if isinstance(item, dict)
    }
    for provider in providers:
        integration_id = _provider_integration_id(provider)
        status = str(provider.get("status") or "")
        attempted.append(integration_id)
        if status == "matched":
            used.append(integration_id)
        if status == "failed" or integration_id in failure_by_id:
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
                "error": (failure_by_id.get(integration_id) or {}).get("error") or provider.get("error"),
            }
        )
    return {
        "integrations": integrations,
        "attempted_integrations": sorted(set(attempted)),
        "used_integrations": sorted(set(used)),
        "required_unmet_integrations": [],
        "failure_integrations": sorted(set(failure_integrations)),
    }


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
