from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class IngestSource(Protocol):
    name: str

    async def fetch(self) -> bytes:
        ...


class EnrichmentProvider(Protocol):
    name: str

    def enrich(self, ein: str) -> dict[str, str | int | float | bool | None]:
        ...


@dataclass(frozen=True)
class FileIngestResult:
    name: str
    status: str
    s3_key: str | None = None
    error: str | None = None
