from __future__ import annotations

from charity_status.enrichments.base import EnrichmentProvider
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.sources import ProviderCapability, SourceCategory


class StateBusinessMockProvider(EnrichmentProvider):
    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "state_business_mock"

    def is_enabled(self) -> bool:
        return self._enabled

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.COMPLIANCE], source_ids=["state_business.entity_status"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()
        if ein == "999999999":
            return self.failure_result("Deterministic state business mock failure")
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
        fields = {
            "entity_status": "active",
            "entity_jurisdiction": "IL",
            "entity_expiration_date": "2026-11-30",
            "good_standing": True,
            "compliance_flags": [],
        }
        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.MATCHED,
            provider_record_id="state-business-mock-123",
            fetched_at=fetched_at,
            fields=fields,
            source_payload={"ein": ein, "mock": True},
            source={"record_id": "state-business-mock-123", "fetched_at": fetched_at, "licensed": False, "notes": "Deterministic state business mock"},
            source_records=[
                self.build_normalized_source_record(
                    ein=ein,
                    source_id="state_business.entity_status",
                    category=SourceCategory.COMPLIANCE,
                    description="Deterministic state business mock",
                    fetched_at=fetched_at,
                    fields=fields,
                    record_id="state-business-mock-123",
                    expires_at="2026-11-30",
                )
            ],
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )
