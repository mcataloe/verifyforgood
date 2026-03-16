from __future__ import annotations

from charity_status.state_registry.contracts import RawStateRegistryRecord, StateRegistryAdapter
from charity_status.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType

from .client import NewYorkRegistryClient
from .mapper import SOURCE_NAME, map_new_york_record


class NewYorkBusinessRegistryAdapter(StateRegistryAdapter):
    def __init__(self, client: NewYorkRegistryClient | None = None) -> None:
        self._client = client or NewYorkRegistryClient()

    @property
    def state_code(self) -> str:
        return "NY"

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
        return map_new_york_record(raw_record, request=request)
