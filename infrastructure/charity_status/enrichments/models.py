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
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "status": self.status.value,
            "fields": self.fields,
            "source": self.source,
        }
        if self.error:
            payload["error"] = self.error
        if self.source_payload is not None:
            payload["source_payload"] = self.source_payload
        return payload


@dataclass(frozen=True)
class EnrichmentAggregateResult:
    providers: list[EnrichmentProviderResult]
    failures: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "providers": [provider.to_dict() for provider in self.providers],
            "failures": self.failures,
        }



def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
