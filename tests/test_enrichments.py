from charity_status.enrichments.base import EnrichmentProvider, ProviderError
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.enrichments.providers import MockProvider
from charity_status.enrichments.registry import ProviderRegistry
from charity_status.enrichments.service import EnrichmentService


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
