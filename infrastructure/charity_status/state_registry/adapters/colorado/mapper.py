from __future__ import annotations

from typing import Any

from charity_status.state_registry.contracts import RawStateRegistryRecord
from charity_status.state_registry.matching import classify_name_match
from charity_status.state_registry.enums import StateRegistryStanding
from charity_status.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType
from charity_status.state_registry.normalization import normalize_entity_name, normalize_entity_status, normalize_standing
from charity_status.state_registry.traceability import build_raw_payload_ref

PARSER_VERSION = "colorado_business_entities.v1"
SOURCE_NAME = "colorado_secretary_of_state"
DETAIL_URL_TEMPLATE = "https://www.sos.state.co.us/biz/BusinessEntityDetail.do?masterFileId={entity_id}"


def map_colorado_record(
    raw_record: RawStateRegistryRecord,
    request: StateRegistryLookupRequest | None = None,
) -> StateRegistryRecord | None:
    if not raw_record:
        return None
    external_entity_id = _clean(raw_record.get("entityid"))
    entity_name = _extract_entity_name(raw_record)
    if not external_entity_id and not entity_name:
        return None
    normalized_entity_name = normalize_entity_name(entity_name)
    match = classify_name_match(
        request.organization_name if request else None,
        entity_name,
        normalized_entity_name,
    )
    raw_payload_ref = build_raw_payload_ref(
        payload=raw_record,
        source_identifier=f"{SOURCE_NAME}:{external_entity_id or 'unknown'}",
        parser_version=PARSER_VERSION,
        retrieved_at=_clean(raw_record.get("raw_fetched_at")) or None,
        storage_locator=_clean(raw_record.get("raw_payload_ref")) or None,
    )
    return StateRegistryRecord(
        state_code="CO",
        source_name=SOURCE_NAME,
        source_type=StateRegistrySourceType.BULK_DATASET,
        external_entity_id=external_entity_id,
        entity_name=entity_name,
        normalized_entity_name=normalized_entity_name,
        entity_type=_map_entity_type(raw_record.get("entitytype")),
        status=_map_status(raw_record.get("entitystatus")),
        standing=_map_standing(raw_record.get("entitystatus")),
        formation_date=_normalize_date(raw_record.get("entityformdate")),
        dissolution_date=None,
        last_filing_date=None,
        registry_url=_registry_url(external_entity_id),
        raw_fetched_at=raw_payload_ref.retrieved_at,
        raw_hash=raw_payload_ref.raw_hash,
        parser_version=PARSER_VERSION,
        matched_on=match.matched_on if match else None,
        confidence=match.confidence if match else None,
        raw_payload_ref=raw_payload_ref,
    )


def _extract_entity_name(raw_record: dict[str, Any]) -> str | None:
    candidate = _clean(raw_record.get("entityname"))
    if not candidate:
        return None
    suffix_markers = [
        ", DISSOLVED",
        ", DELINQUENT",
        ", WITHDRAWN",
        ", NONCOMPLIANT",
        ", REVOKED",
    ]
    upper = candidate.upper()
    for marker in suffix_markers:
        if marker in upper:
            index = upper.index(marker)
            cleaned = candidate[:index].strip(" ,")
            return cleaned or candidate
    return candidate


def _map_status(value: object | None):
    return normalize_entity_status(value)


def _map_standing(value: object | None):
    standing = normalize_standing(value)
    if standing is not None and standing != StateRegistryStanding.UNKNOWN:
        return standing
    normalized = normalize_entity_name(value)
    if normalized in {"ADMINISTRATIVELY DISSOLVED", "DELINQUENT", "NONCOMPLIANT", "REVOKED", "WITHDRAWN"}:
        return StateRegistryStanding.NOT_IN_GOOD_STANDING
    return standing


def _map_entity_type(value: object | None) -> str | None:
    raw = _clean(value)
    if not raw:
        return None
    entity_types = {
        "DLLC": "Domestic Limited Liability Company",
        "FLLC": "Foreign Limited Liability Company",
        "DNC": "Domestic Nonprofit Corporation",
        "FNC": "Foreign Nonprofit Corporation",
        "DPC": "Domestic Profit Corporation",
        "FPC": "Foreign Profit Corporation",
    }
    return entity_types.get(raw.upper(), raw)


def _registry_url(entity_id: str | None) -> str | None:
    if not entity_id:
        return None
    return DETAIL_URL_TEMPLATE.format(entity_id=entity_id)


def _normalize_date(value: object | None) -> str | None:
    raw = _clean(value)
    if not raw:
        return None
    return raw.split("T", 1)[0]


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
