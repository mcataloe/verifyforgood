from verification.backend.shared.enrichments.base import EnrichmentProvider, ProviderError
from verification.backend.shared.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from verification.backend.shared.enrichments.providers import MockProvider
from verification.backend.shared.enrichments.registry import ProviderRegistry
from verification.backend.shared.enrichments.service import EnrichmentService


class FailingProvider(EnrichmentProvider):
    @property
    def name(self) -> str:
        return "failing"

    def is_enabled(self) -> bool:
        return True

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        raise ProviderError("boom")


class DisabledProvider(EnrichmentProvider):
    @property
    def name(self) -> str:
        return "disabled"

    def is_enabled(self) -> bool:
        return False

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        raise RuntimeError("should not be called")


def test_provider_registry_list_enabled():
    registry = ProviderRegistry([MockProvider(enabled=True), DisabledProvider()])

    assert len(registry.list_all()) == 2
    assert [p.name for p in registry.list_enabled()] == ["mock_provider"]


def test_mock_provider_normalization_match():
    provider = MockProvider(enabled=True)
    result = provider.lookup("123456789")

    assert result.status == EnrichmentStatus.MATCHED
    assert result.fields["transparency_level"] == "gold"


def test_mock_provider_no_match():
    provider = MockProvider(enabled=True)
    result = provider.lookup("999999999")

    assert result.status == EnrichmentStatus.NO_MATCH


def test_enrichment_service_disabled_and_failure_fallback():
    registry = ProviderRegistry([DisabledProvider(), FailingProvider()])
    service = EnrichmentService(registry)

    aggregate = service.enrich("123456789", "Test Org")
    data = aggregate.to_dict()

    assert len(data["providers"]) == 2
    assert any(item["status"] == "disabled" for item in data["providers"])
    assert any(item["status"] == "failed" for item in data["providers"])
    assert any(f["provider"] == "failing" for f in data["failures"])
    assert data["source_catalog"]["us_only"] is True


def test_enrichment_service_capability_discovery_and_backward_compatibility():
    registry = ProviderRegistry([MockProvider(enabled=True)])
    service = EnrichmentService(registry)

    aggregate = service.enrich("123456789", "Test Org").to_dict()
    assert "providers" in aggregate
    assert "failures" in aggregate
    assert "source_catalog" in aggregate
    assert aggregate["providers"][0]["name"] == "mock_provider"
    assert "fields" in aggregate["providers"][0]

    discovered = service.discover_capabilities()
    assert discovered["us_only"] is True
    provider_names = [item["provider_name"] for item in discovered["provider_capabilities"]]
    assert "mock_provider" in provider_names

