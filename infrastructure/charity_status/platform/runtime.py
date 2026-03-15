from __future__ import annotations

from dataclasses import dataclass

from charity_status.enrichments import EnrichmentService, ProviderRegistry
from charity_status.enrichments.models import IntegrationBinding
from charity_status.enrichments.providers import (
    CandidProvider,
    MockProvider,
    OFACApiAdapter,
    OFACMockProvider,
    OFACProvider,
    StateBusinessApiAdapter,
    StateBusinessMockProvider,
    StateBusinessProvider,
    StateRegistryApiAdapter,
    StateRegistryMockProvider,
    StateRegistryProvider,
    USAspendingApiAdapter,
    USAspendingMockProvider,
    USAspendingProvider,
)
from charity_status.query import AthenaQueryClient


@dataclass(frozen=True)
class QueryRuntimeConfig:
    database: str
    table: str
    workgroup: str | None
    form990_filings_table: str
    form990_metrics_table: str
    form990_governance_table: str
    form990_quality_table: str


@dataclass(frozen=True)
class RefreshRuntimeConfig(QueryRuntimeConfig):
    enrichment_mock_offered: bool | None = None
    enrichment_mock_enabled: bool = False
    enrichment_candid_offered: bool | None = None
    enrichment_candid_enabled: bool = False
    enrichment_candid_api_key: str | None = None
    enrichment_candid_endpoint: str | None = None
    enrichment_timeout_seconds: int = 5
    enrichment_state_registry_offered: bool | None = None
    enrichment_state_registry_enabled: bool = False
    enrichment_state_registry_mock_enabled: bool = False
    enrichment_state_registry_endpoint: str | None = None
    enrichment_state_business_offered: bool | None = None
    enrichment_state_business_enabled: bool = False
    enrichment_state_business_mock_enabled: bool = False
    enrichment_state_business_endpoint: str | None = None
    enrichment_usaspending_offered: bool | None = None
    enrichment_usaspending_enabled: bool = False
    enrichment_usaspending_mock_enabled: bool = False
    enrichment_usaspending_endpoint: str | None = None
    enrichment_ofac_offered: bool | None = None
    enrichment_ofac_enabled: bool = False
    enrichment_ofac_mock_enabled: bool = False
    enrichment_ofac_endpoint: str | None = None


def build_athena_client(config: QueryRuntimeConfig) -> AthenaQueryClient:
    return AthenaQueryClient(
        database=config.database,
        table=config.table,
        workgroup=config.workgroup,
        form990_filings_table=config.form990_filings_table,
        form990_metrics_table=config.form990_metrics_table,
        form990_governance_table=config.form990_governance_table,
        form990_quality_table=config.form990_quality_table,
    )


def build_enrichment_service(config: RefreshRuntimeConfig) -> EnrichmentService:
    providers = []
    bindings: list[IntegrationBinding] = []

    mock_offered = _resolve_offered(config.enrichment_mock_offered, config.enrichment_mock_enabled)
    if mock_offered:
        if config.enrichment_mock_enabled:
            providers.append(MockProvider(enabled=True))
        bindings.append(
            IntegrationBinding(
                integration_id="mock_provider",
                provider_name="mock_provider" if config.enrichment_mock_enabled else None,
                offered=True,
                driver="mock" if config.enrichment_mock_enabled else "none",
                credentials_present=config.enrichment_mock_enabled,
            )
        )

    candid_offered = _resolve_offered(config.enrichment_candid_offered, config.enrichment_candid_enabled)
    candid_credentials_present = bool(config.enrichment_candid_enabled and config.enrichment_candid_api_key and config.enrichment_candid_endpoint)
    if candid_offered:
        if candid_credentials_present:
            providers.append(
                CandidProvider(
                    enabled=True,
                    api_key=config.enrichment_candid_api_key,
                    endpoint=config.enrichment_candid_endpoint,
                    timeout_seconds=config.enrichment_timeout_seconds,
                )
            )
        bindings.append(
            IntegrationBinding(
                integration_id="candid",
                provider_name="candid" if candid_credentials_present else None,
                offered=True,
                driver="live" if config.enrichment_candid_enabled else "none",
                credentials_present=candid_credentials_present,
                endpoint=config.enrichment_candid_endpoint,
            )
        )

    _register_dual_mode_integration(
        bindings=bindings,
        providers=providers,
        integration_id="state_registry",
        offered=_resolve_offered(
            config.enrichment_state_registry_offered,
            config.enrichment_state_registry_enabled or config.enrichment_state_registry_mock_enabled,
        ),
        live_enabled=config.enrichment_state_registry_enabled,
        mock_enabled=config.enrichment_state_registry_mock_enabled,
        endpoint=config.enrichment_state_registry_endpoint,
        timeout_seconds=config.enrichment_timeout_seconds,
        live_provider_factory=lambda endpoint: StateRegistryProvider(
            enabled=True,
            adapter=StateRegistryApiAdapter(endpoint, config.enrichment_timeout_seconds),
        ),
        mock_provider_factory=lambda: StateRegistryMockProvider(enabled=True),
        live_provider_name="state_registry",
        mock_provider_name="state_registry_mock",
    )
    _register_dual_mode_integration(
        bindings=bindings,
        providers=providers,
        integration_id="state_business",
        offered=_resolve_offered(
            config.enrichment_state_business_offered,
            config.enrichment_state_business_enabled or config.enrichment_state_business_mock_enabled,
        ),
        live_enabled=config.enrichment_state_business_enabled,
        mock_enabled=config.enrichment_state_business_mock_enabled,
        endpoint=config.enrichment_state_business_endpoint,
        timeout_seconds=config.enrichment_timeout_seconds,
        live_provider_factory=lambda endpoint: StateBusinessProvider(
            enabled=True,
            adapter=StateBusinessApiAdapter(endpoint, config.enrichment_timeout_seconds),
        ),
        mock_provider_factory=lambda: StateBusinessMockProvider(enabled=True),
        live_provider_name="state_business",
        mock_provider_name="state_business_mock",
    )
    _register_dual_mode_integration(
        bindings=bindings,
        providers=providers,
        integration_id="usaspending",
        offered=_resolve_offered(
            config.enrichment_usaspending_offered,
            config.enrichment_usaspending_enabled or config.enrichment_usaspending_mock_enabled,
        ),
        live_enabled=config.enrichment_usaspending_enabled,
        mock_enabled=config.enrichment_usaspending_mock_enabled,
        endpoint=config.enrichment_usaspending_endpoint,
        timeout_seconds=config.enrichment_timeout_seconds,
        live_provider_factory=lambda endpoint: USAspendingProvider(
            enabled=True,
            adapter=USAspendingApiAdapter(endpoint, config.enrichment_timeout_seconds),
        ),
        mock_provider_factory=lambda: USAspendingMockProvider(enabled=True),
        live_provider_name="usaspending",
        mock_provider_name="usaspending_mock",
    )
    _register_dual_mode_integration(
        bindings=bindings,
        providers=providers,
        integration_id="ofac",
        offered=_resolve_offered(
            config.enrichment_ofac_offered,
            config.enrichment_ofac_enabled or config.enrichment_ofac_mock_enabled,
        ),
        live_enabled=config.enrichment_ofac_enabled,
        mock_enabled=config.enrichment_ofac_mock_enabled,
        endpoint=config.enrichment_ofac_endpoint,
        timeout_seconds=config.enrichment_timeout_seconds,
        live_provider_factory=lambda endpoint: OFACProvider(
            enabled=True,
            adapter=OFACApiAdapter(endpoint, config.enrichment_timeout_seconds),
        ),
        mock_provider_factory=lambda: OFACMockProvider(enabled=True),
        live_provider_name="ofac",
        mock_provider_name="ofac_mock",
    )

    registry = ProviderRegistry(providers=providers)
    return EnrichmentService(registry=registry, integration_bindings=bindings)


def _resolve_offered(offered: bool | None, fallback: bool) -> bool:
    if offered is not None:
        return offered
    return bool(fallback)


def _register_dual_mode_integration(
    *,
    bindings: list[IntegrationBinding],
    providers: list[object],
    integration_id: str,
    offered: bool,
    live_enabled: bool,
    mock_enabled: bool,
    endpoint: str | None,
    timeout_seconds: int,
    live_provider_factory,
    mock_provider_factory,
    live_provider_name: str,
    mock_provider_name: str,
) -> None:
    del timeout_seconds
    if not offered:
        return

    if mock_enabled:
        providers.append(mock_provider_factory())
        bindings.append(
            IntegrationBinding(
                integration_id=integration_id,
                provider_name=mock_provider_name,
                offered=True,
                driver="mock",
                credentials_present=True,
                endpoint=endpoint,
            )
        )
        return

    credentials_present = bool(live_enabled and endpoint)
    if credentials_present:
        providers.append(live_provider_factory(str(endpoint)))
    bindings.append(
        IntegrationBinding(
            integration_id=integration_id,
            provider_name=live_provider_name if credentials_present else None,
            offered=True,
            driver="live" if live_enabled else "none",
            credentials_present=credentials_present,
            endpoint=endpoint,
        )
    )
