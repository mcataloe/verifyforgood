from __future__ import annotations

from charity_status.enrichments.base import EnrichmentProvider
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.sources import ProviderCapability, SourceCategory


class StateRegistryMockProvider(EnrichmentProvider):
    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "state_registry_mock"

    def is_enabled(self) -> bool:
        return self._enabled

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.COMPLIANCE], source_ids=["state_registry.compliance"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()

        fetched_at = now_utc_iso()
        if ein == "999999999":
            return self.failure_result("Deterministic mock failure")

        if ein != "123456789":
            return EnrichmentProviderResult(
                name=self.name,
                status=EnrichmentStatus.NO_MATCH,
                provider_record_id=None,
                fetched_at=fetched_at,
                fields={},
                source_payload={"ein": ein},
                source={"record_id": None, "fetched_at": fetched_at, "licensed": False},
            )

        flags = ["state_registration_expiring_soon"] if organization_name and "Risk" in organization_name else []
        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.MATCHED,
            provider_record_id="state-mock-123",
            fetched_at=fetched_at,
            fields={
                "registration_status": "active",
                "registration_jurisdiction": "IL",
                "registration_expiration_date": "2026-12-31",
                "solicitation_permitted": True,
                "compliance_flags": flags,
            },
            source_payload={"ein": ein, "mock": True},
            source={"record_id": "state-mock-123", "fetched_at": fetched_at, "licensed": False, "notes": "Deterministic state compliance mock"},
            source_records=[
                self.build_normalized_source_record(
                    ein=ein,
                    source_id="state_registry.compliance",
                    category=SourceCategory.COMPLIANCE,
                    description="Deterministic state registry compliance mock",
                    fetched_at=fetched_at,
                    fields={
                        "registration_status": "active",
                        "registration_jurisdiction": "IL",
                        "registration_expiration_date": "2026-12-31",
                        "solicitation_permitted": True,
                        "compliance_flags": flags,
                    },
                    record_id="state-mock-123",
                    expires_at="2026-12-31",
                )
            ],
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )
