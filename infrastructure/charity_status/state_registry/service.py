from __future__ import annotations

from dataclasses import dataclass

from charity_status.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord
from charity_status.state_registry.registry import StateRegistryAdapterRegistry


@dataclass(frozen=True)
class StateRegistryLookupService:
    adapter_registry: StateRegistryAdapterRegistry

    def search(self, request: StateRegistryLookupRequest) -> list[StateRegistryRecord]:
        adapter = self.adapter_registry.resolve(request.state)
        records: list[StateRegistryRecord] = []
        for raw_record in adapter.search(request):
            parsed = adapter.parse_record(raw_record, request=request)
            if parsed is not None:
                records.append(parsed)
        return records

    def fetch_by_external_entity_id(
        self,
        *,
        state_code: str,
        external_entity_id: str,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        adapter = self.adapter_registry.resolve(state_code)
        raw_record = adapter.fetch_by_external_entity_id(external_entity_id)
        if raw_record is None:
            return None
        return adapter.parse_record(raw_record, request=request)
