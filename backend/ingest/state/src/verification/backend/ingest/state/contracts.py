from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from verification.backend.ingest.state.errors import StateRegistryAdapterOperationNotSupportedError
from verification.backend.ingest.state.models import StateRegistryLookupRequest, StateRegistryRecord, StateRegistrySourceType

RawStateRegistryRecord = dict[str, Any]


class StateRegistryAdapter(ABC):
    @property
    @abstractmethod
    def state_code(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def source_type(self) -> StateRegistrySourceType:
        raise NotImplementedError

    @abstractmethod
    def search(self, request: StateRegistryLookupRequest) -> list[RawStateRegistryRecord]:
        raise NotImplementedError

    def fetch_by_external_entity_id(self, external_entity_id: str) -> RawStateRegistryRecord | None:
        raise StateRegistryAdapterOperationNotSupportedError(
            f"{self.source_name} does not support fetch_by_external_entity_id"
        )

    @abstractmethod
    def parse_record(
        self,
        raw_record: RawStateRegistryRecord,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        raise NotImplementedError

