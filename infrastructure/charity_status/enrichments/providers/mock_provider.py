from __future__ import annotations

from charity_status.enrichments.base import EnrichmentProvider
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.sources import ProviderCapability, SourceCategory


class MockProvider(EnrichmentProvider):
    def __init__(self, enabled: bool = False):
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "mock_provider"

    def is_enabled(self) -> bool:
        return self._enabled

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.IDENTITY], source_ids=["mock.profile"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()

        matched = ein == "123456789"
        fetched_at = now_utc_iso()

        if not matched:
            return EnrichmentProviderResult(
                name=self.name,
                status=EnrichmentStatus.NO_MATCH,
                provider_record_id=None,
                fetched_at=fetched_at,
                fields={},
                source_payload={"ein": ein},
                source={"record_id": None, "fetched_at": fetched_at, "licensed": False},
            )

        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.MATCHED,
            provider_record_id="mock-123",
            fetched_at=fetched_at,
            fields={
                "transparency_level": "gold",
                "profile_complete": True,
                "external_rating_label": "A",
                "rating_score": 92,
                "impact_metrics_available": True,
                "leadership_data_present": True,
                "profile_link": "https://example.org/nonprofit/123456789",
            },
            source_payload={"ein": ein, "profile": "mock"},
            source={
                "record_id": "mock-123",
                "fetched_at": fetched_at,
                "licensed": False,
                "notes": "Deterministic test provider",
            },
            source_records=[
                self.build_normalized_source_record(
                    ein=ein,
                    source_id="mock.profile",
                    category=SourceCategory.IDENTITY,
                    description="Deterministic mock profile source",
                    fetched_at=fetched_at,
                    fields={
                        "transparency_level": "gold",
                        "profile_complete": True,
                        "external_rating_label": "A",
                        "rating_score": 92,
                    },
                    record_id="mock-123",
                )
            ],
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )
