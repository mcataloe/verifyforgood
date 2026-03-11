from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso


class EnrichmentProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        raise NotImplementedError

    def disabled_result(self) -> EnrichmentProviderResult:
        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.DISABLED,
            provider_record_id=None,
            fetched_at=now_utc_iso(),
            fields={},
            source_payload=None,
            source={
                "record_id": None,
                "fetched_at": now_utc_iso(),
                "licensed": False,
                "notes": "Provider disabled or missing credentials",
            },
        )

    def failure_result(self, error: str) -> EnrichmentProviderResult:
        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.FAILED,
            provider_record_id=None,
            fetched_at=now_utc_iso(),
            fields={},
            source_payload=None,
            source={
                "record_id": None,
                "fetched_at": now_utc_iso(),
                "licensed": False,
            },
            error=error,
        )


class ProviderError(RuntimeError):
    pass
