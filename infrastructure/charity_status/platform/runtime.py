from __future__ import annotations

from dataclasses import dataclass

from charity_status.enrichments import EnrichmentService, ProviderRegistry
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
    enrichment_mock_enabled: bool = False
    enrichment_candid_enabled: bool = False
    enrichment_candid_api_key: str | None = None
    enrichment_candid_endpoint: str | None = None
    enrichment_timeout_seconds: int = 5
    enrichment_state_registry_enabled: bool = False
    enrichment_state_registry_mock_enabled: bool = False
    enrichment_state_registry_endpoint: str | None = None
    enrichment_state_business_enabled: bool = False
    enrichment_state_business_mock_enabled: bool = False
    enrichment_state_business_endpoint: str | None = None
    enrichment_usaspending_enabled: bool = False
    enrichment_usaspending_mock_enabled: bool = False
    enrichment_usaspending_endpoint: str | None = None
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
    registry = ProviderRegistry(
        providers=[
            MockProvider(enabled=config.enrichment_mock_enabled),
            CandidProvider(
                enabled=config.enrichment_candid_enabled,
                api_key=config.enrichment_candid_api_key,
                endpoint=config.enrichment_candid_endpoint,
                timeout_seconds=config.enrichment_timeout_seconds,
            ),
            StateRegistryProvider(
                enabled=config.enrichment_state_registry_enabled,
                adapter=StateRegistryApiAdapter(config.enrichment_state_registry_endpoint, config.enrichment_timeout_seconds)
                if config.enrichment_state_registry_enabled and config.enrichment_state_registry_endpoint
                else None,
            ),
            StateRegistryMockProvider(enabled=config.enrichment_state_registry_mock_enabled),
            StateBusinessProvider(
                enabled=config.enrichment_state_business_enabled,
                adapter=StateBusinessApiAdapter(config.enrichment_state_business_endpoint, config.enrichment_timeout_seconds)
                if config.enrichment_state_business_enabled and config.enrichment_state_business_endpoint
                else None,
            ),
            StateBusinessMockProvider(enabled=config.enrichment_state_business_mock_enabled),
            USAspendingProvider(
                enabled=config.enrichment_usaspending_enabled,
                adapter=USAspendingApiAdapter(config.enrichment_usaspending_endpoint, config.enrichment_timeout_seconds)
                if config.enrichment_usaspending_enabled and config.enrichment_usaspending_endpoint
                else None,
            ),
            USAspendingMockProvider(enabled=config.enrichment_usaspending_mock_enabled),
            OFACProvider(
                enabled=config.enrichment_ofac_enabled,
                adapter=OFACApiAdapter(config.enrichment_ofac_endpoint, config.enrichment_timeout_seconds)
                if config.enrichment_ofac_enabled and config.enrichment_ofac_endpoint
                else None,
            ),
            OFACMockProvider(enabled=config.enrichment_ofac_mock_enabled),
        ]
    )
    return EnrichmentService(registry=registry)
