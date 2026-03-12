from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.sources import NormalizedSourceRecord, ProviderCapability, SourceAttribution, SourceCategory, SourceFreshness, SourceMetadata


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

    def capabilities(self) -> list[ProviderCapability]:
        return []

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
            capabilities=[capability.to_dict() for capability in self.capabilities()],
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
            capabilities=[capability.to_dict() for capability in self.capabilities()],
            error=error,
        )

    def build_normalized_source_record(
        self,
        ein: str,
        source_id: str,
        category: SourceCategory,
        description: str,
        fetched_at: str,
        fields: dict[str, Any],
        record_id: str | None = None,
        valid_as_of: str | None = None,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        metadata = SourceMetadata(
            source_id=source_id,
            provider_name=self.name,
            category=category,
            us_only=True,
            description=description,
        )
        record = NormalizedSourceRecord(
            subject_ein=ein,
            metadata=metadata,
            fields=fields,
            attribution=SourceAttribution(
                provider_name=self.name,
                source_id=source_id,
                record_id=record_id,
                retrieved_at=fetched_at,
            ),
            freshness=SourceFreshness(
                retrieved_at=fetched_at,
                valid_as_of=valid_as_of,
                expires_at=expires_at,
            ),
        )
        return record.to_dict()


class ProviderError(RuntimeError):
    pass
