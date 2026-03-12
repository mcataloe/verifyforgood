from __future__ import annotations

from charity_status.enrichments.base import EnrichmentProvider
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.sources import ProviderCapability, SourceCategory


class OFACMockProvider(EnrichmentProvider):
    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "ofac_mock"

    def is_enabled(self) -> bool:
        return self._enabled

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.RISK], source_ids=["ofac.sanctions"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()
        if ein == "999999999":
            return self.failure_result("Deterministic OFAC mock failure")
        fetched_at = now_utc_iso()
        if ein != "123456789":
            return EnrichmentProviderResult(
                name=self.name,
                status=EnrichmentStatus.NO_MATCH,
                provider_record_id=None,
                fetched_at=fetched_at,
                fields={},
                source_payload={"ein": ein},
                source={"record_id": None, "fetched_at": fetched_at, "licensed": False},
                capabilities=[capability.to_dict() for capability in self.capabilities()],
            )
        match = bool(organization_name and "Watchlist" in organization_name)
        fields = {
            "sanctions_match": match,
            "sanctions_lists": ["SDN"] if match else [],
            "matched_name": organization_name if match else None,
            "match_confidence": "high" if match else "none",
        }
        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.MATCHED,
            provider_record_id=None,
            fetched_at=fetched_at,
            fields=fields,
            source_payload={"ein": ein, "mock": True},
            source={"record_id": None, "fetched_at": fetched_at, "licensed": False, "notes": "Deterministic OFAC mock"},
            source_records=[
                self.build_normalized_source_record(
                    ein=ein,
                    source_id="ofac.sanctions",
                    category=SourceCategory.RISK,
                    description="Deterministic OFAC sanctions mock",
                    fetched_at=fetched_at,
                    fields=fields,
                )
            ],
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )
