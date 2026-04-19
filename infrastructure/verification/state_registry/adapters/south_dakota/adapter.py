from __future__ import annotations

from verification.state_registry.contracts import RawStateRegistryRecord, StateRegistryAdapter
from verification.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType

from .client import SouthDakotaRegistryClient
from .mapper import SOURCE_NAME, map_south_dakota_record


class SouthDakotaBusinessRegistryAdapter(StateRegistryAdapter):
    def __init__(self, client: SouthDakotaRegistryClient | None = None) -> None:
        self._client = client or SouthDakotaRegistryClient()

    @property
    def state_code(self) -> str:
        return "SD"

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
        return map_south_dakota_record(raw_record, request=request)

