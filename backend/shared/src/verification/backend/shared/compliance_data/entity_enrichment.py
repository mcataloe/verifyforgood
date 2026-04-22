from __future__ import annotations

from dataclasses import replace

from verification.backend.shared.enrichments.base import ProviderError
from verification.backend.shared.enrichments.models import (
    EnrichmentAggregateResult,
    EvaluationContext,
    IntegrationBinding,
    IntegrationEvaluation,
    IntegrationState,
)
from verification.backend.shared.enrichments.registry import ProviderRegistry
from verification.backend.shared.sources import default_us_source_catalog


class EntityEnrichmentService:
    def __init__(
        self,
        registry: ProviderRegistry,
        integration_bindings: list[IntegrationBinding] | None = None,
    ):
        self._registry = registry
        self._legacy_mode = integration_bindings is None
        self._integration_bindings = {
            binding.integration_id: binding
            for binding in (integration_bindings or [])
        }

    def enrich(
        self,
        ein: str,
        organization_name: str | None = None,
        evaluation_context: EvaluationContext | None = None,
        jurisdiction_state: str | None = None,
    ) -> EnrichmentAggregateResult:
        if self._legacy_mode:
            return self._legacy_enrich(
                ein=ein,
                organization_name=organization_name,
                jurisdiction_state=jurisdiction_state,
            )

        context = evaluation_context or EvaluationContext()
        providers = []
        failures: list[dict[str, object]] = []
        integration_states: list[IntegrationState] = []
        capabilities = [capability for provider in self._registry.list_all() for capability in provider.capabilities()]

        all_integration_ids = set(self._integration_bindings.keys()) | set(context.integration_ids())
        for integration_id in sorted(all_integration_ids):
            setting = context.setting_for(integration_id)
            binding = self._integration_bindings.get(
                integration_id,
                IntegrationBinding(
                    integration_id=integration_id,
                    provider_name=None,
                    offered=False,
                    driver="none",
                    credentials_present=False,
                ),
            )
            provider = self._registry.get(binding.provider_name) if binding.provider_name else None
            attempted = (
                binding.offered
                and setting.enabled
                and binding.credentials_present
                and provider is not None
            )

            if not binding.offered:
                availability_status = "not_offered"
                requirement_status = "unmet" if setting.required_for_eligibility else "not_required"
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=False,
                        credentials_present=False,
                        tenant_enabled=setting.enabled,
                        required_for_eligibility=setting.required_for_eligibility,
                        attempted=False,
                        availability_status=availability_status,
                        requirement_status=requirement_status,
                        driver="none",
                    )
                )
                continue

            if not setting.enabled:
                availability_status = "tenant_disabled"
                requirement_status = "unmet" if setting.required_for_eligibility else "not_required"
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=binding.credentials_present,
                        tenant_enabled=False,
                        required_for_eligibility=setting.required_for_eligibility,
                        attempted=False,
                        availability_status=availability_status,
                        requirement_status=requirement_status,
                        driver=binding.driver,
                        provider_name=binding.provider_name,
                    )
                )
                continue

            if not binding.credentials_present or provider is None:
                availability_status = "missing_credentials"
                requirement_status = "unmet" if setting.required_for_eligibility else "not_required"
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=binding.credentials_present,
                        tenant_enabled=True,
                        required_for_eligibility=setting.required_for_eligibility,
                        attempted=False,
                        availability_status=availability_status,
                        requirement_status=requirement_status,
                        driver=binding.driver,
                        provider_name=binding.provider_name,
                    )
                )
                continue

            try:
                try:
                    result = provider.lookup(
                        ein=ein,
                        organization_name=organization_name,
                        jurisdiction_state=jurisdiction_state,
                    )
                except TypeError:
                    result = provider.lookup(ein=ein, organization_name=organization_name)
                result = replace(
                    result,
                    integration_id=integration_id,
                    driver=binding.driver,
                )
                providers.append(result)
                availability_status = result.status.value
                requirement_status = (
                    "satisfied"
                    if setting.required_for_eligibility and availability_status == "matched"
                    else "unmet"
                    if setting.required_for_eligibility
                    else "not_required"
                )
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=True,
                        tenant_enabled=True,
                        required_for_eligibility=setting.required_for_eligibility,
                        attempted=attempted,
                        availability_status=availability_status,
                        requirement_status=requirement_status,
                        driver=binding.driver,
                        provider_name=provider.name,
                        error=result.error,
                    )
                )
                if result.status.value == "failed" and result.error:
                    failures.append(
                        {
                            "provider": provider.name,
                            "integration_id": integration_id,
                            "driver": binding.driver,
                            "error": result.error,
                        }
                    )
            except ProviderError as exc:
                safe_error = str(exc)
                result = replace(
                    provider.failure_result(safe_error),
                    integration_id=integration_id,
                    driver=binding.driver,
                )
                providers.append(result)
                failures.append(
                    {
                        "provider": provider.name,
                        "integration_id": integration_id,
                        "driver": binding.driver,
                        "error": safe_error,
                    }
                )
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=True,
                        tenant_enabled=True,
                        required_for_eligibility=setting.required_for_eligibility,
                        attempted=attempted,
                        availability_status="failed",
                        requirement_status="unmet" if setting.required_for_eligibility else "not_required",
                        driver=binding.driver,
                        provider_name=provider.name,
                        error=safe_error,
                    )
                )
            except Exception:
                safe_error = "Provider lookup failed"
                result = replace(
                    provider.failure_result(safe_error),
                    integration_id=integration_id,
                    driver=binding.driver,
                )
                providers.append(result)
                failures.append(
                    {
                        "provider": provider.name,
                        "integration_id": integration_id,
                        "driver": binding.driver,
                        "error": safe_error,
                    }
                )
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=True,
                        tenant_enabled=True,
                        required_for_eligibility=setting.required_for_eligibility,
                        attempted=attempted,
                        availability_status="failed",
                        requirement_status="unmet" if setting.required_for_eligibility else "not_required",
                        driver=binding.driver,
                        provider_name=provider.name,
                        error=safe_error,
                    )
                )

        catalog = default_us_source_catalog(capabilities).to_dict()
        return EnrichmentAggregateResult(
            providers=providers,
            failures=failures,
            source_catalog=catalog,
            integration_evaluation=IntegrationEvaluation(integrations=integration_states),
        )

    def discover_source_capabilities(self) -> dict[str, object]:
        capabilities = [capability for provider in self._registry.list_all() for capability in provider.capabilities()]
        return default_us_source_catalog(capabilities).to_dict()

    def discover_capabilities(self) -> dict[str, object]:
        return self.discover_source_capabilities()

    def _legacy_enrich(
        self,
        *,
        ein: str,
        organization_name: str | None,
        jurisdiction_state: str | None = None,
    ) -> EnrichmentAggregateResult:
        providers = []
        failures: list[dict[str, object]] = []
        integration_states: list[IntegrationState] = []
        capabilities = [capability for provider in self._registry.list_all() for capability in provider.capabilities()]

        for provider in self._registry.list_all():
            integration_id, driver = _legacy_identity(provider.name)
            if not provider.is_enabled():
                result = replace(
                    provider.disabled_result(),
                    integration_id=integration_id,
                    driver=driver,
                )
                providers.append(result)
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=False,
                        tenant_enabled=True,
                        required_for_eligibility=False,
                        attempted=False,
                        availability_status="disabled",
                        requirement_status="not_required",
                        driver=driver,
                        provider_name=provider.name,
                    )
                )
                continue

            try:
                try:
                    provider_result = provider.lookup(
                        ein=ein,
                        organization_name=organization_name,
                        jurisdiction_state=jurisdiction_state,
                    )
                except TypeError:
                    provider_result = provider.lookup(ein=ein, organization_name=organization_name)
                result = replace(
                    provider_result,
                    integration_id=integration_id,
                    driver=driver,
                )
                providers.append(result)
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=True,
                        tenant_enabled=True,
                        required_for_eligibility=False,
                        attempted=True,
                        availability_status=result.status.value,
                        requirement_status="not_required",
                        driver=driver,
                        provider_name=provider.name,
                        error=result.error,
                    )
                )
                if result.status.value == "failed" and result.error:
                    failures.append({"provider": provider.name, "integration_id": integration_id, "driver": driver, "error": result.error})
            except ProviderError as exc:
                safe_error = str(exc)
                result = replace(
                    provider.failure_result(safe_error),
                    integration_id=integration_id,
                    driver=driver,
                )
                providers.append(result)
                failures.append({"provider": provider.name, "integration_id": integration_id, "driver": driver, "error": safe_error})
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=True,
                        tenant_enabled=True,
                        required_for_eligibility=False,
                        attempted=True,
                        availability_status="failed",
                        requirement_status="not_required",
                        driver=driver,
                        provider_name=provider.name,
                        error=safe_error,
                    )
                )
            except Exception:
                safe_error = "Provider lookup failed"
                result = replace(
                    provider.failure_result(safe_error),
                    integration_id=integration_id,
                    driver=driver,
                )
                providers.append(result)
                failures.append({"provider": provider.name, "integration_id": integration_id, "driver": driver, "error": safe_error})
                integration_states.append(
                    IntegrationState(
                        integration_id=integration_id,
                        offered=True,
                        credentials_present=True,
                        tenant_enabled=True,
                        required_for_eligibility=False,
                        attempted=True,
                        availability_status="failed",
                        requirement_status="not_required",
                        driver=driver,
                        provider_name=provider.name,
                        error=safe_error,
                    )
                )

        catalog = default_us_source_catalog(capabilities).to_dict()
        return EnrichmentAggregateResult(
            providers=providers,
            failures=failures,
            source_catalog=catalog,
            integration_evaluation=IntegrationEvaluation(integrations=integration_states),
        )


def _legacy_identity(provider_name: str) -> tuple[str, str]:
    if provider_name == "mock_provider":
        return "mock_provider", "mock"
    if provider_name.endswith("_mock"):
        return provider_name.removesuffix("_mock"), "mock"
    return provider_name, "live"


EnrichmentService = EntityEnrichmentService


__all__ = [
    "EnrichmentService",
    "EntityEnrichmentService",
]

