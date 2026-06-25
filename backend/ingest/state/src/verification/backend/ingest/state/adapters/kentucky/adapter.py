from __future__ import annotations

from verification.backend.ingest.state.contracts import RawStateRegistryRecord, StateRegistryAdapter
from verification.backend.ingest.state.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType
from verification.backend.ingest.state.normalization import normalize_entity_name

from .client import KentuckyBulkDataClient
from .mapper import SOURCE_NAME, map_kentucky_company_record
from .parser import build_kentucky_companies_index, kentucky_external_entity_id, parse_kentucky_companies_tsv


class KentuckyBusinessRegistryAdapter(StateRegistryAdapter):
    def __init__(
        self,
        client: KentuckyBulkDataClient | None = None,
        *,
        companies_snapshot_text: str | None = None,
    ) -> None:
        self._client = client or KentuckyBulkDataClient()
        self._companies_snapshot_text = companies_snapshot_text
        self._cached_rows: list[RawStateRegistryRecord] | None = None
        self._cached_index: dict[str, RawStateRegistryRecord] | None = None

    @property
    def state_code(self) -> str:
        return "KY"

    @property
    def source_name(self) -> str:
        return SOURCE_NAME

    @property
    def source_type(self) -> StateRegistrySourceType:
        return StateRegistrySourceType.BULK_DATASET

    def search(self, request: StateRegistryLookupRequest) -> list[RawStateRegistryRecord]:
        query_name = request.normalized_organization_name or ""
        if not query_name:
            return []
        return [
            dict(row)
            for row in self._companies_rows()
            if query_name in (normalize_entity_name(row.get("Name")) or "")
        ]

    def fetch_by_external_entity_id(self, external_entity_id: str) -> RawStateRegistryRecord | None:
        normalized = str(external_entity_id or "").strip()
        if not normalized:
            return None
        return dict(self._companies_index().get(normalized) or {}) or None

    def parse_record(
        self,
        raw_record: RawStateRegistryRecord,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        return map_kentucky_company_record(raw_record, request=request)

    def _companies_rows(self) -> list[RawStateRegistryRecord]:
        if self._cached_rows is None:
            snapshot = self._companies_snapshot_text
            if snapshot is None:
                snapshot = self._client.fetch_companies_snapshot()
            self._cached_rows = parse_kentucky_companies_tsv(snapshot)
        return self._cached_rows

    def _companies_index(self) -> dict[str, RawStateRegistryRecord]:
        if self._cached_index is None:
            self._cached_index = build_kentucky_companies_index(self._companies_rows())
        return self._cached_index

