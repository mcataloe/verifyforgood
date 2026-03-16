from __future__ import annotations

from typing import Any

from charity_status.state_registry.contracts import RawStateRegistryRecord
from charity_status.state_registry.enums import StateRegistryEntityStatus, StateRegistryStanding
from charity_status.state_registry.matching import classify_name_match
from charity_status.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType
from charity_status.state_registry.normalization import normalize_entity_name
from charity_status.state_registry.traceability import build_raw_payload_ref

from .parser import kentucky_external_entity_id

PARSER_VERSION = "kentucky_bulk_companies.v1"
SOURCE_NAME = "kentucky_secretary_of_state"

_TYPE_MAP = {
    "KCO": "Kentucky Corporation",
    "FCO": "Foreign Corporation",
    "KLC": "Kentucky Limited Liability Company",
    "FLC": "Foreign Limited Liability Company",
    "KLP": "Kentucky Limited Partnership",
    "FLP": "Foreign Limited Partnership",
    "KLL": "Kentucky Limited Liability Partnership",
    "FLL": "Foreign Limited Liability Partnership",
    "KBT": "Kentucky Business Trust",
    "FBT": "Foreign Business Trust",
    "PSC": "Professional Services Corporation",
    "FPS": "Foreign Professional Services Corporation",
    "DNC": "Domestic Nonprofit Corporation",
}

_STANDING_MAP = {
    "G": StateRegistryStanding.GOOD_STANDING,
    "B": StateRegistryStanding.NOT_IN_GOOD_STANDING,
    "X": StateRegistryStanding.NOT_IN_GOOD_STANDING,
}

_STATUS_MAP = {
    "A": StateRegistryEntityStatus.ACTIVE,
    "D": StateRegistryEntityStatus.REVOKED,
    "I": StateRegistryEntityStatus.INACTIVE,
}


def map_kentucky_company_record(
    raw_record: RawStateRegistryRecord,
    request: StateRegistryLookupRequest | None = None,
) -> StateRegistryRecord | None:
    if not raw_record:
        return None
    entity_name = _clean(raw_record.get("Name"))
    external_entity_id = kentucky_external_entity_id(raw_record)
    if not entity_name or not external_entity_id:
        return None
    normalized_entity_name = normalize_entity_name(entity_name)
    match = classify_name_match(
        request.organization_name if request else None,
        entity_name,
        normalized_entity_name,
    )
    raw_payload_ref = build_raw_payload_ref(
        payload=raw_record,
        source_identifier=f"{SOURCE_NAME}:{external_entity_id}",
        parser_version=PARSER_VERSION,
        retrieved_at=_clean(raw_record.get("raw_fetched_at")) or None,
        storage_locator=_clean(raw_record.get("raw_payload_ref")) or None,
    )
    return StateRegistryRecord(
        state_code="KY",
        source_name=SOURCE_NAME,
        source_type=StateRegistrySourceType.BULK_DATASET,
        external_entity_id=external_entity_id,
        entity_name=entity_name,
        normalized_entity_name=normalized_entity_name,
        entity_type=_map_entity_type(raw_record.get("Type")),
        status=_map_status(raw_record.get("Status")),
        standing=_map_standing(raw_record.get("Standing")),
        formation_date=_pick_date(raw_record.get("orgdate"), raw_record.get("filedate"), raw_record.get("authdate")),
        dissolution_date=None,
        last_filing_date=_normalize_date(raw_record.get("recorddate")),
        registry_url=None,
        raw_fetched_at=raw_payload_ref.retrieved_at,
        raw_hash=raw_payload_ref.raw_hash,
        parser_version=PARSER_VERSION,
        matched_on=match.matched_on if match else None,
        confidence=match.confidence if match else None,
        raw_payload_ref=raw_payload_ref,
    )


def _map_entity_type(value: object | None) -> str | None:
    code = _clean(value)
    if not code:
        return None
    return _TYPE_MAP.get(code.upper(), code)


def _map_standing(value: object | None):
    code = _clean(value)
    if not code:
        return None
    return _STANDING_MAP.get(code.upper(), StateRegistryStanding.UNKNOWN)


def _map_status(value: object | None):
    code = _clean(value)
    if not code:
        return None
    return _STATUS_MAP.get(code.upper(), StateRegistryEntityStatus.UNKNOWN)


def _pick_date(*values: object | None) -> str | None:
    for value in values:
        normalized = _normalize_date(value)
        if normalized:
            return normalized
    return None


def _normalize_date(value: object | None) -> str | None:
    raw = _clean(value)
    if not raw:
        return None
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3:
            month, day, year = parts
            if len(year) == 4:
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return raw.split("T", 1)[0]


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
