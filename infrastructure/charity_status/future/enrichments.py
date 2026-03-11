from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EnrichmentPayload:
    provider: str
    data: dict[str, Any]


@dataclass(frozen=True)
class EnrichmentProviderStub:
    name: str

    def enrich(self, ein: str) -> EnrichmentPayload:
        return EnrichmentPayload(
            provider=self.name,
            data={
                "ein": ein,
                "status": "not_implemented",
                "note": "External enrichment providers are planned for a future phase.",
            },
        )
