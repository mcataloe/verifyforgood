from __future__ import annotations

from charity_status.enrichments.base import ProviderError
from charity_status.enrichments.models import EnrichmentAggregateResult, EnrichmentProviderResult, EnrichmentStatus
from charity_status.enrichments.registry import ProviderRegistry


class EnrichmentService:
    def __init__(self, registry: ProviderRegistry):
        self._registry = registry

    def enrich(self, ein: str, organization_name: str | None = None) -> EnrichmentAggregateResult:
        providers: list[EnrichmentProviderResult] = []
        failures: list[dict[str, str]] = []

        for provider in self._registry.list_all():
            if not provider.is_enabled():
                providers.append(provider.disabled_result())
                continue

            try:
                result = provider.lookup(ein=ein, organization_name=organization_name)
                providers.append(result)
                if result.status == EnrichmentStatus.FAILED and result.error:
                    failures.append({"provider": provider.name, "error": result.error})
            except ProviderError as exc:
                providers.append(provider.failure_result(str(exc)))
                failures.append({"provider": provider.name, "error": str(exc)})
            except Exception:
                safe_error = "Provider lookup failed"
                providers.append(provider.failure_result(safe_error))
                failures.append({"provider": provider.name, "error": safe_error})

        return EnrichmentAggregateResult(providers=providers, failures=failures)
