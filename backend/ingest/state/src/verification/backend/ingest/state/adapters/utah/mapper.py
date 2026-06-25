from __future__ import annotations

from verification.backend.ingest.state.contracts import RawStateRegistryRecord
from verification.backend.ingest.state.enums import StateRegistryEntityStatus, StateRegistryStanding
from verification.backend.ingest.state.matching import classify_name_match
from verification.backend.ingest.state.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType
from verification.backend.ingest.state.normalization import normalize_entity_name, normalize_entity_status, normalize_standing
from verification.backend.ingest.state.traceability import build_raw_payload_ref

PARSER_VERSION = "utah_business_registry.v1"
SOURCE_NAME = "utah_division_of_corporations"
BASE_URL = "https://businessregistration.utah.gov"


def map_utah_record(
    raw_record: RawStateRegistryRecord,
    request: StateRegistryLookupRequest | None = None,
) -> StateRegistryRecord | None:
    entity_name = _clean(raw_record.get("entity_name"))
    entity_number = _clean(raw_record.get("entity_number"))
    if not entity_name or not entity_number:
        return None
    normalized_name = normalize_entity_name(entity_name)
    match = classify_name_match(request.organization_name if request else None, entity_name, normalized_name)
    raw_payload_ref = build_raw_payload_ref(
        payload=raw_record,
        source_identifier=f"{SOURCE_NAME}:{entity_number}",
        parser_version=PARSER_VERSION,
        retrieved_at=_clean(raw_record.get("raw_fetched_at")) or None,
        storage_locator=_clean(raw_record.get("raw_payload_ref")) or None,
    )
    standing = normalize_standing(raw_record.get("status"))
    if standing in {None, StateRegistryStanding.UNKNOWN} and normalize_entity_name(raw_record.get("status")) in {"EXPIRED", "DELINQUENT", "REVOKED"}:
        standing = StateRegistryStanding.NOT_IN_GOOD_STANDING
    return StateRegistryRecord(
        state_code="UT",
        source_name=SOURCE_NAME,
        source_type=StateRegistrySourceType.SEARCH_PORTAL,
        external_entity_id=entity_number,
        entity_name=entity_name,
        normalized_entity_name=normalized_name,
        entity_type=_clean(raw_record.get("entity_type")),
        status=_map_status(raw_record.get("status")),
        standing=standing,
        formation_date=_normalize_date(raw_record.get("formation_date")),
        registry_url=_absolute_url(raw_record.get("detail_href")),
        raw_fetched_at=raw_payload_ref.retrieved_at,
        raw_hash=raw_payload_ref.raw_hash,
        parser_version=PARSER_VERSION,
        matched_on=match.matched_on if match else None,
        confidence=match.confidence if match else None,
        raw_payload_ref=raw_payload_ref,
    )


def _absolute_url(value: object | None) -> str | None:
    href = _clean(value)
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE_URL}{href}"


def _map_status(value: object | None):
    normalized = normalize_entity_name(value)
    if normalized == "EXPIRED":
        return StateRegistryEntityStatus.INACTIVE
    return normalize_entity_status(value)


def _normalize_date(value: object | None) -> str | None:
    raw = _clean(value)
    if not raw:
        return None
    if "/" in raw:
        month, day, year = raw.split("/")
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return raw


def _clean(value: object | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None

