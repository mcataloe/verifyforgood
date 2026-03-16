from __future__ import annotations

from charity_status.state_registry.contracts import RawStateRegistryRecord, StateRegistryAdapter
from charity_status.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType

from .client import ColoradoRegistryClient
from .mapper import SOURCE_NAME, map_colorado_record


class ColoradoBusinessRegistryAdapter(StateRegistryAdapter):
    def __init__(self, client: ColoradoRegistryClient | None = None, *, search_limit: int = 10) -> None:
        self._client = client or ColoradoRegistryClient()
        self._search_limit = max(1, int(search_limit))

    @property
    def state_code(self) -> str:
        return "CO"

    @property
    def source_name(self) -> str:
        return SOURCE_NAME

    @property
    def source_type(self) -> StateRegistrySourceType:
        return StateRegistrySourceType.BULK_DATASET

    def search(self, request: StateRegistryLookupRequest) -> list[RawStateRegistryRecord]:
        return self._client.search(
            normalized_name=request.normalized_organization_name or "",
            limit=self._search_limit,
        )

    def fetch_by_external_entity_id(self, external_entity_id: str) -> RawStateRegistryRecord | None:
        return self._client.fetch_by_entity_id(external_entity_id)

    def parse_record(
        self,
        raw_record: RawStateRegistryRecord,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        return map_colorado_record(raw_record, request=request)
