from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from charity_status.state_registry.models import StateRegistryLookupRequest, StateRegistryRecord


class StateRegistryRecordRepository(Protocol):
    def save_record(
        self,
        *,
        request: StateRegistryLookupRequest,
        record: StateRegistryRecord,
    ) -> None:
        ...


class NoopStateRegistryRecordRepository:
    def save_record(
        self,
        *,
        request: StateRegistryLookupRequest,
        record: StateRegistryRecord,
    ) -> None:
        del request, record
        return None


@dataclass
class InMemoryStateRegistryRecordRepository:
    _items: list[dict[str, Any]] = field(default_factory=list)

    def save_record(
        self,
        *,
        request: StateRegistryLookupRequest,
        record: StateRegistryRecord,
    ) -> None:
        self._items.append(build_state_registry_record_item(request=request, record=record))

    def items(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items]


def build_state_registry_record_item(
    *,
    request: StateRegistryLookupRequest,
    record: StateRegistryRecord,
) -> dict[str, Any]:
    persisted_at = datetime.now(timezone.utc).isoformat()
    external_entity_id = str(record.external_entity_id or "").strip()
    fallback_entity_key = str(record.raw_hash or record.normalized_entity_name or "unknown").strip() or "unknown"
    entity_key = external_entity_id or fallback_entity_key
    return {
        "pk": f"STATE#{record.state_code}",
        "sk": f"ENTITY#{entity_key}",
        "state_code": record.state_code,
        "external_entity_id": record.external_entity_id,
        "request": request.to_dict(),
        "record": record.to_dict(),
        "raw_payload_ref": record.raw_payload_ref.to_dict() if record.raw_payload_ref else None,
        "persisted_at": persisted_at,
    }
