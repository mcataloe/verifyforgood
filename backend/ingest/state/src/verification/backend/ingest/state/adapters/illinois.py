from __future__ import annotations

from typing import Any

from verification.backend.ingest.state.contracts import RawStateRegistryRecord, StateRegistryAdapter
from verification.backend.ingest.state.matching import classify_name_match
from verification.backend.ingest.state.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType
from verification.backend.ingest.state.normalization import normalize_entity_name, normalize_entity_status, normalize_standing
from verification.backend.ingest.state.traceability import build_raw_payload_ref

PARSER_VERSION = "illinois_business_registry.v1"


class IllinoisBusinessRegistryAdapter(StateRegistryAdapter):
    def __init__(self, records: list[RawStateRegistryRecord] | None = None) -> None:
        self._records = [item for item in records or [] if isinstance(item, dict)]

    @property
    def state_code(self) -> str:
        return "IL"

    @property
    def source_name(self) -> str:
        return "illinois_secretary_of_state"

    @property
    def source_type(self) -> StateRegistrySourceType:
        return StateRegistrySourceType.SEARCH_PORTAL

    def search(self, request: StateRegistryLookupRequest) -> list[RawStateRegistryRecord]:
        query_name = request.normalized_organization_name or ""
        if not query_name:
            return []
        return [
            dict(item)
            for item in self._records
            if query_name in (normalize_entity_name(item.get("entity_name")) or "")
        ]

    def fetch_by_external_entity_id(self, external_entity_id: str) -> RawStateRegistryRecord | None:
        normalized_id = str(external_entity_id or "").strip()
        if not normalized_id:
            return None
        for item in self._records:
            if str(item.get("file_number") or item.get("external_entity_id") or "").strip() == normalized_id:
                return dict(item)
        return None

    def parse_record(
        self,
        raw_record: RawStateRegistryRecord,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        if not raw_record:
            return None
        external_entity_id = str(raw_record.get("file_number") or raw_record.get("external_entity_id") or "").strip() or None
        entity_name = str(raw_record.get("entity_name") or raw_record.get("name") or "").strip() or None
        normalized_entity_name = normalize_entity_name(entity_name)
        match_result = classify_name_match(
            request.organization_name if request else None,
            entity_name,
            normalized_entity_name,
        )
        raw_payload_ref = build_raw_payload_ref(
            payload=raw_record,
            source_identifier=f"{self.source_name}:{external_entity_id or 'unknown'}",
            parser_version=PARSER_VERSION,
            retrieved_at=str(raw_record.get("raw_fetched_at") or "").strip() or None,
            storage_locator=str(raw_record.get("raw_payload_ref") or raw_record.get("storage_locator") or "").strip() or None,
        )
        return StateRegistryRecord(
            state_code=self.state_code,
            source_name=self.source_name,
            source_type=self.source_type,
            external_entity_id=external_entity_id,
            entity_name=entity_name,
            normalized_entity_name=normalized_entity_name,
            entity_type=str(raw_record.get("entity_type") or "").strip() or None,
            status=normalize_entity_status(raw_record.get("status")),
            standing=normalize_standing(raw_record.get("standing") or raw_record.get("good_standing")),
            formation_date=str(raw_record.get("formation_date") or "").strip() or None,
            dissolution_date=str(raw_record.get("dissolution_date") or "").strip() or None,
            last_filing_date=str(raw_record.get("last_filing_date") or "").strip() or None,
            registry_url=str(raw_record.get("registry_url") or "").strip() or None,
            raw_fetched_at=raw_payload_ref.retrieved_at,
            raw_hash=raw_payload_ref.raw_hash,
            parser_version=PARSER_VERSION,
            matched_on=match_result.matched_on if match_result else None,
            confidence=match_result.confidence if match_result else None,
            raw_payload_ref=raw_payload_ref,
        )

