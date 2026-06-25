from __future__ import annotations

from typing import Iterable

from verification.backend.shared.enrichments.base import EnrichmentProvider


class ProviderRegistry:
    def __init__(self, providers: Iterable[EnrichmentProvider] | None = None) -> None:
        self._providers: dict[str, EnrichmentProvider] = {}
        if providers:
            for provider in providers:
                self.register(provider)

    def register(self, provider: EnrichmentProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> EnrichmentProvider | None:
        return self._providers.get(name)

    def list_all(self) -> list[EnrichmentProvider]:
        return list(self._providers.values())

    def list_enabled(self) -> list[EnrichmentProvider]:
        return [provider for provider in self._providers.values() if provider.is_enabled()]

