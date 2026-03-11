from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from charity_status.normalization import compare_names
from charity_status.query.nonprofit_lookup import map_nonprofit_record
from charity_status.scoring import assign_peer_group, calculate_v1_scores


@dataclass(frozen=True)
class VerificationInput:
    ein: str
    provided_name: str | None = None
    subsection: str | None = None


def verify_nonprofit(
    client: Any,
    verification_input: VerificationInput,
    enrichment_service: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    query_execution_id, record = client.lookup_nonprofit(verification_input.ein, subsection=verification_input.subsection)

    if not record:
        return 404, {"message": "Nonprofit not found", "ein": verification_input.ein}

    mapped = map_nonprofit_record(verification_input.ein, record)
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
    )

    payload = mapped.to_dict()
    payload["scores"] = score_result.scores
    payload["score_explanation"] = score_result.explanation
    payload["name_verification"] = name_check
    payload["queryExecutionId"] = query_execution_id
    if enrichment_service is not None:
        enrichment = enrichment_service.enrich(
            ein=verification_input.ein,
            organization_name=mapped.organization.get("name"),
        )
        payload["enrichment"] = enrichment.to_dict()
    else:
        payload["enrichment"] = {"providers": [], "failures": []}
    if filings:
        payload["filing_summary"] = {
            "tax_year": filings.get("tax_year"),
            "form_type": filings.get("return_type"),
            "filing_date": filings.get("filing_date"),
            "amended": _to_bool(filings.get("amended_return")),
            "parse_status": filings.get("parse_status"),
        }
    return 200, payload


def get_nonprofit_filings(client: Any, ein: str) -> tuple[int, dict[str, Any]]:
    _, rows = client.list_form990_filings(ein)
    if not rows:
        return 200, {"ein": ein, "filings": []}

    filings = [
        {
            "tax_year": row.get("tax_year"),
            "form_type": row.get("return_type"),
            "filing_date": row.get("filing_date"),
            "amended": _to_bool(row.get("amended_return")),
            "parse_status": row.get("parse_status"),
        }
        for row in rows
    ]
    return 200, {"ein": ein, "filings": filings}


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
