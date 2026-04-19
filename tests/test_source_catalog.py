from __future__ import annotations

from verification.sources import (
    NormalizedSourceRecord,
    ProviderCapability,
    SourceAttribution,
    SourceCatalog,
    SourceCategory,
    SourceFreshness,
    SourceMetadata,
)


def test_source_catalog_registration():
    catalog = SourceCatalog(us_only=True)
    source = SourceMetadata(
        source_id="state_registry.compliance",
        provider_name="state_registry",
        category=SourceCategory.COMPLIANCE,
        us_only=True,
        description="State compliance source",
    )
    catalog.register_source(source)
    assert catalog.list_sources(SourceCategory.COMPLIANCE)[0].source_id == "state_registry.compliance"


def test_normalized_source_record_typing():
    record = NormalizedSourceRecord(
        subject_ein="123456789",
        metadata=SourceMetadata(
            source_id="mock.profile",
            provider_name="mock_provider",
            category=SourceCategory.IDENTITY,
            us_only=True,
            description="Mock profile source",
        ),
        fields={"profile_complete": True},
        attribution=SourceAttribution(
            provider_name="mock_provider",
            source_id="mock.profile",
            record_id="mock-123",
            retrieved_at="2026-03-12T00:00:00+00:00",
        ),
        freshness=SourceFreshness(
            retrieved_at="2026-03-12T00:00:00+00:00",
            valid_as_of="2026-03-12",
            expires_at=None,
        ),
    )
    payload = record.to_dict()
    assert payload["metadata"]["category"] == "identity"
    assert payload["subject_ein"] == "123456789"


def test_provider_capability_discovery_registration():
    catalog = SourceCatalog(us_only=True)
    capability = ProviderCapability(
        provider_name="state_registry_mock",
        categories=[SourceCategory.COMPLIANCE],
        source_ids=["state_registry.compliance"],
        us_only=True,
    )
    catalog.register_capability(capability)
    discovered = catalog.get_capability("state_registry_mock")
    assert discovered is not None
    assert discovered.source_ids == ["state_registry.compliance"]

