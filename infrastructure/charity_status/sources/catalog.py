from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from charity_status.sources.models import ProviderCapability, SourceCategory, SourceMetadata


@dataclass
class SourceCatalog:
    us_only: bool = True

    def __post_init__(self) -> None:
        self._sources: dict[str, SourceMetadata] = {}
        self._capabilities: dict[str, ProviderCapability] = {}

    def register_source(self, source: SourceMetadata) -> None:
        if self.us_only and not source.us_only:
            raise ValueError("Catalog is scoped to U.S.-only sources")
        self._sources[source.source_id] = source

    def register_capability(self, capability: ProviderCapability) -> None:
        if self.us_only and not capability.us_only:
            raise ValueError("Catalog is scoped to U.S.-only providers")
        self._capabilities[capability.provider_name] = capability

    def list_sources(self, category: SourceCategory | None = None) -> list[SourceMetadata]:
        values = list(self._sources.values())
        if category is None:
            return sorted(values, key=lambda item: item.source_id)
        return sorted([source for source in values if source.category == category], key=lambda item: item.source_id)

    def get_capability(self, provider_name: str) -> ProviderCapability | None:
        return self._capabilities.get(provider_name)

    def to_dict(self) -> dict[str, object]:
        return {
            "us_only": self.us_only,
            "sources": [source.to_dict() for source in self.list_sources()],
            "provider_capabilities": [capability.to_dict() for capability in sorted(self._capabilities.values(), key=lambda item: item.provider_name)],
        }


def default_us_source_catalog(capabilities: Iterable[ProviderCapability]) -> SourceCatalog:
    catalog = SourceCatalog(us_only=True)
    catalog.register_source(
        SourceMetadata(
            source_id="candid.profile",
            provider_name="candid",
            category=SourceCategory.TRANSPARENCY,
            us_only=True,
            description="Candid transparency/profile enrichment source (scaffolded).",
        )
    )
    catalog.register_source(
        SourceMetadata(
            source_id="state_registry.compliance",
            provider_name="state_registry",
            category=SourceCategory.COMPLIANCE,
            us_only=True,
            description="State charity registration/compliance source (adapter scaffold).",
        )
    )
    catalog.register_source(
        SourceMetadata(
            source_id="mock.profile",
            provider_name="mock_provider",
            category=SourceCategory.IDENTITY,
            us_only=True,
            description="Deterministic mock profile source for tests/development.",
        )
    )
    for capability in capabilities:
        catalog.register_capability(capability)
    return catalog
