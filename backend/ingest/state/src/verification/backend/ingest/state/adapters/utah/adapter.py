from __future__ import annotations

from verification.backend.ingest.state.contracts import RawStateRegistryRecord, StateRegistryAdapter
from verification.backend.ingest.state.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType

from .client import UtahRegistryClient
from .mapper import SOURCE_NAME, map_utah_record


class UtahBusinessRegistryAdapter(StateRegistryAdapter):
    def __init__(self, client: UtahRegistryClient | None = None) -> None:
        self._client = client or UtahRegistryClient()

    @property
    def state_code(self) -> str:
        return "UT"

    @property
    def source_name(self) -> str:
        return SOURCE_NAME

    @property
    def source_type(self) -> StateRegistrySourceType:
        return StateRegistrySourceType.SEARCH_PORTAL

    def search(self, request: StateRegistryLookupRequest) -> list[RawStateRegistryRecord]:
        return self._client.search(normalized_name=request.normalized_organization_name or "")

    def parse_record(
        self,
        raw_record: RawStateRegistryRecord,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        return map_utah_record(raw_record, request=request)

