from __future__ import annotations

from typing import Any

from charity_status.enrichments.compliance import extract_state_compliance
from charity_status.enrichments.external_signals import extract_external_signals
from charity_status.query.nonprofit_lookup import map_nonprofit_record


def get_nonprofit_sources_view(client: Any, enrichment_service: Any, ein: str, subsection: str | None = None) -> tuple[int, dict[str, Any]]:
    _, record = client.lookup_nonprofit(ein, subsection=subsection)
    if not record:
        return 404, {"message": "Nonprofit not found", "ein": ein}

    mapped = map_nonprofit_record(ein, record).to_dict()
    enrichment = enrichment_service.enrich(ein=ein, organization_name=mapped["organization"].get("name")).to_dict()
    providers = enrichment.get("providers") or []
    failures = enrichment.get("failures") or []

    sources = [_to_source_entry(provider) for provider in providers]
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
) -> tuple[int, dict[str, Any]]:
    status, payload = get_nonprofit_sources_view(client, enrichment_service, ein, subsection=subsection)
    if status != 200:
        return status, payload

    normalized_name = source_name.strip().lower()
    sources = payload.get("sources") or []
    match = next((source for source in sources if str(source.get("source_name", "")).lower() == normalized_name), None)
    if match is None:
        return 404, {"message": f"Unsupported source name: {source_name}", "ein": ein}
    return 200, {"ein": ein, "source": match}


def get_nonprofit_compliance_view(client: Any, enrichment_service: Any, ein: str, subsection: str | None = None) -> tuple[int, dict[str, Any]]:
    status, payload = get_nonprofit_sources_view(client, enrichment_service, ein, subsection=subsection)
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


def get_nonprofit_federal_awards_view(client: Any, enrichment_service: Any, ein: str, subsection: str | None = None) -> tuple[int, dict[str, Any]]:
    status, payload = get_nonprofit_sources_view(client, enrichment_service, ein, subsection=subsection)
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


def _to_source_entry(provider: dict[str, Any]) -> dict[str, Any]:
    source = provider.get("source") or {}
    return {
        "source_name": provider.get("name"),
        "status": provider.get("status"),
        "normalized_data": provider.get("fields") or {},
        "attribution": {
            "record_id": source.get("record_id"),
            "licensed": source.get("licensed"),
            "notes": source.get("notes"),
        },
        "freshness": {
            "retrieved_at": source.get("fetched_at") or provider.get("fetched_at"),
        },
        "error": provider.get("error"),
    }


def _to_legacy_provider_shape(source_entry: dict[str, Any]) -> dict[str, Any]:
    freshness = source_entry.get("freshness") or {}
    attribution = source_entry.get("attribution") or {}
    return {
        "name": source_entry.get("source_name"),
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
