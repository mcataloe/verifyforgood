from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EnrichmentStatus(str, Enum):
    MATCHED = "matched"
    NO_MATCH = "no_match"
    DISABLED = "disabled"
    FAILED = "failed"


@dataclass(frozen=True)
class EnrichmentProviderResult:
    name: str
    status: EnrichmentStatus
    provider_record_id: str | None
    fetched_at: str
    fields: dict[str, Any]
    source_payload: dict[str, Any] | None
    source: dict[str, Any]
    source_records: list[dict[str, Any]] | None = None
    capabilities: list[dict[str, Any]] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "status": self.status.value,
            "fields": self.fields,
            "source": self.source,
        }
        if self.source_records is not None:
            payload["source_records"] = self.source_records
        if self.capabilities is not None:
            payload["capabilities"] = self.capabilities
        if self.error:
            payload["error"] = self.error
        if self.source_payload is not None:
            payload["source_payload"] = self.source_payload
        return payload


@dataclass(frozen=True)
class EnrichmentAggregateResult:
    providers: list[EnrichmentProviderResult]
    failures: list[dict[str, str]]
    source_catalog: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "providers": [provider.to_dict() for provider in self.providers],
            "failures": self.failures,
        }
        if self.source_catalog is not None:
            payload["source_catalog"] = self.source_catalog
        return payload



def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
