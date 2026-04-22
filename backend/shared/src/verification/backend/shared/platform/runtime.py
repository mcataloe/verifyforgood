from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from verification.backend.shared.enrichments import EnrichmentService, ProviderRegistry
from verification.backend.shared.enrichments.models import IntegrationBinding, OrganizationIntegrationSetting, normalize_integration_id
from verification.backend.shared.enrichments.providers import (
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
from verification.backend.ingest.state import StateRegistryLookupService, build_state_registry_adapter_registry
from verification.backend.ingest.state.adapters import (
    ColoradoBusinessRegistryAdapter,
    ColoradoRegistryClient,
    KentuckyBusinessRegistryAdapter,
    KentuckyBulkDataClient,
)


@dataclass(frozen=True)
class RefreshRuntimeConfig:
    platform_integrations: "PlatformIntegrationsConfig" = field(default_factory=lambda: PlatformIntegrationsConfig())
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
    enrichment_state_registry_colorado_enabled: bool = False
    enrichment_state_registry_colorado_app_token: str | None = None
    enrichment_state_registry_kentucky_enabled: bool = False
    enrichment_state_registry_kentucky_companies_url: str | None = None
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


@dataclass(frozen=True)
class PlatformIntegrationConfig:
    integration_id: str
    available: bool = False
    credentials_present: bool = False
    default_required_for_evaluation: bool = False
    provider_name: str | None = None
    driver: str = "none"
    endpoint: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    api_key: str | None = None
    implementation_available: bool = True


@dataclass(frozen=True)
class PlatformIntegrationsConfig:
    globally_enabled: bool = False
    integrations: dict[str, PlatformIntegrationConfig] = field(default_factory=dict)

    def integration(self, integration_id: str) -> PlatformIntegrationConfig:
        normalized = normalize_integration_id(integration_id)
        return self.integrations.get(
            normalized,
            PlatformIntegrationConfig(integration_id=normalized),
        )

    def organization_default_settings(self) -> dict[str, OrganizationIntegrationSetting]:
        return {
            integration_id: OrganizationIntegrationSetting(
                enabled=False,
                required_for_eligibility=config.default_required_for_evaluation,
            )
            for integration_id, config in self.integrations.items()
            if config.default_required_for_evaluation
        }


def load_platform_integrations_config(env: Mapping[str, str] | None = None) -> PlatformIntegrationsConfig:
    source = env or {}
    global_flag = _mapping_optional_bool(source, "THIRD_PARTY_INTEGRATIONS_ENABLED")
    if global_flag is None:
        global_flag = _legacy_global_integrations_enabled(source)
    globally_enabled = bool(global_flag)

    integrations = {
        "candid": _build_candid_platform_config(source, globally_enabled),
        "charity_navigator": _build_charity_navigator_platform_config(source, globally_enabled),
    }
    return PlatformIntegrationsConfig(globally_enabled=globally_enabled, integrations=integrations)


def build_enrichment_service(config: RefreshRuntimeConfig) -> EnrichmentService:
    providers = []
    bindings: list[IntegrationBinding] = []
    platform_integrations = _resolved_platform_integrations(config)

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

    candid_platform_config = platform_integrations.integration("candid")
    candid_offered = candid_platform_config.available
    candid_credentials_present = bool(candid_platform_config.credentials_present)
    if candid_offered:
        if candid_credentials_present and candid_platform_config.provider_name == "candid":
            providers.append(
                CandidProvider(
                    enabled=True,
                    api_key=candid_platform_config.api_key,
                    endpoint=candid_platform_config.endpoint,
                    timeout_seconds=config.enrichment_timeout_seconds,
                )
            )
        bindings.append(
            IntegrationBinding(
                integration_id="candid",
                provider_name=candid_platform_config.provider_name,
                offered=True,
                driver=candid_platform_config.driver,
                credentials_present=candid_credentials_present,
                endpoint=candid_platform_config.endpoint,
            )
        )

    _register_state_registry_integration(bindings=bindings, providers=providers, config=config)
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


def _register_state_registry_integration(
    *,
    bindings: list[IntegrationBinding],
    providers: list[object],
    config: RefreshRuntimeConfig,
) -> None:
    offered = _resolve_offered(
        config.enrichment_state_registry_offered,
        config.enrichment_state_registry_enabled or config.enrichment_state_registry_mock_enabled,
    )
    if not offered:
        return

    if config.enrichment_state_registry_mock_enabled:
        providers.append(StateRegistryMockProvider(enabled=True))
        bindings.append(
            IntegrationBinding(
                integration_id="state_registry",
                provider_name="state_registry_mock",
                offered=True,
                driver="mock",
                credentials_present=True,
                endpoint=config.enrichment_state_registry_endpoint,
            )
        )
        return

    endpoint = _clean_text(config.enrichment_state_registry_endpoint)
    lookup_service = _build_state_registry_lookup_service(config)
    credentials_present = bool(
        config.enrichment_state_registry_enabled
        and (endpoint or lookup_service is not None)
    )
    if credentials_present:
        providers.append(
            StateRegistryProvider(
                enabled=True,
                adapter=StateRegistryApiAdapter(endpoint, config.enrichment_timeout_seconds) if endpoint else None,
                lookup_service=lookup_service,
            )
        )
    bindings.append(
        IntegrationBinding(
            integration_id="state_registry",
            provider_name="state_registry" if credentials_present else None,
            offered=True,
            driver="live" if config.enrichment_state_registry_enabled else "none",
            credentials_present=credentials_present,
            endpoint=endpoint,
        )
    )


def _resolved_platform_integrations(config: RefreshRuntimeConfig) -> PlatformIntegrationsConfig:
    if config.platform_integrations.integrations:
        return config.platform_integrations

    candid_offered = _resolve_offered(config.enrichment_candid_offered, config.enrichment_candid_enabled)
    candid_api_key = _clean_text(config.enrichment_candid_api_key)
    candid_endpoint = _clean_text(config.enrichment_candid_endpoint)
    return PlatformIntegrationsConfig(
        globally_enabled=candid_offered,
        integrations={
            "candid": PlatformIntegrationConfig(
                integration_id="candid",
                available=candid_offered,
                credentials_present=bool(config.enrichment_candid_enabled and candid_api_key and candid_endpoint),
                default_required_for_evaluation=False,
                provider_name="candid" if config.enrichment_candid_enabled and candid_api_key and candid_endpoint else None,
                driver="live" if config.enrichment_candid_enabled else "none",
                endpoint=candid_endpoint,
                api_key=candid_api_key,
            ),
            "charity_navigator": PlatformIntegrationConfig(
                integration_id="charity_navigator",
                available=False,
                credentials_present=False,
                default_required_for_evaluation=False,
                implementation_available=False,
            ),
        },
    )


def _build_state_registry_lookup_service(config: RefreshRuntimeConfig) -> StateRegistryLookupService | None:
    adapters = []
    if config.enrichment_state_registry_colorado_enabled:
        adapters.append(
            ColoradoBusinessRegistryAdapter(
                client=ColoradoRegistryClient(
                    app_token=_clean_text(config.enrichment_state_registry_colorado_app_token),
                    timeout_seconds=config.enrichment_timeout_seconds,
                )
            )
        )
    if config.enrichment_state_registry_kentucky_enabled and _clean_text(config.enrichment_state_registry_kentucky_companies_url):
        adapters.append(
            KentuckyBusinessRegistryAdapter(
                client=KentuckyBulkDataClient(
                    companies_url=_clean_text(config.enrichment_state_registry_kentucky_companies_url),
                    timeout_seconds=config.enrichment_timeout_seconds,
                )
            )
        )
    if not adapters:
        return None
    return StateRegistryLookupService(adapter_registry=build_state_registry_adapter_registry(adapters))


def _build_candid_platform_config(source: Mapping[str, str], globally_enabled: bool) -> PlatformIntegrationConfig:
    available = globally_enabled and _resolve_enabled_with_fallback(
        source,
        primary_key="INTEGRATION_CANDID_ENABLED",
        legacy_keys=("ENRICHMENT_CANDID_OFFERED", "ENRICHMENT_CANDID_ENABLED"),
    )
    client_id = _mapping_text(source, "INTEGRATION_CANDID_CLIENT_ID")
    client_secret = _mapping_text(source, "INTEGRATION_CANDID_CLIENT_SECRET")
    legacy_api_key = _mapping_text(source, "ENRICHMENT_CANDID_API_KEY")
    endpoint = _mapping_text(source, "INTEGRATION_CANDID_ENDPOINT") or _mapping_text(source, "ENRICHMENT_CANDID_ENDPOINT")
    api_key = legacy_api_key or client_secret
    credentials_present = bool((client_id and client_secret) or legacy_api_key)
    provider_name = "candid" if available and api_key and endpoint else None
    return PlatformIntegrationConfig(
        integration_id="candid",
        available=available,
        credentials_present=credentials_present,
        default_required_for_evaluation=_mapping_bool(source, "DEFAULT_REQUIRE_CANDID_FOR_EVALUATION", False),
        provider_name=provider_name,
        driver="live" if available else "none",
        endpoint=endpoint,
        client_id=client_id,
        client_secret=client_secret,
        api_key=api_key,
    )


def _build_charity_navigator_platform_config(source: Mapping[str, str], globally_enabled: bool) -> PlatformIntegrationConfig:
    available = globally_enabled and _mapping_bool(source, "INTEGRATION_CHARITY_NAVIGATOR_ENABLED", False)
    api_key = _mapping_text(source, "INTEGRATION_CHARITY_NAVIGATOR_API_KEY")
    endpoint = _mapping_text(source, "INTEGRATION_CHARITY_NAVIGATOR_ENDPOINT")
    return PlatformIntegrationConfig(
        integration_id="charity_navigator",
        available=available,
        credentials_present=bool(api_key),
        default_required_for_evaluation=_mapping_bool(source, "DEFAULT_REQUIRE_CHARITY_NAVIGATOR_FOR_EVALUATION", False),
        provider_name=None,
        driver="none",
        endpoint=endpoint,
        api_key=api_key,
        implementation_available=False,
    )


def _legacy_global_integrations_enabled(source: Mapping[str, str]) -> bool:
    legacy_keys = (
        "ENRICHMENT_CANDID_OFFERED",
        "ENRICHMENT_CANDID_ENABLED",
        "ENRICHMENT_STATE_REGISTRY_OFFERED",
        "ENRICHMENT_STATE_REGISTRY_ENABLED",
        "ENRICHMENT_STATE_BUSINESS_OFFERED",
        "ENRICHMENT_STATE_BUSINESS_ENABLED",
        "ENRICHMENT_USASPENDING_OFFERED",
        "ENRICHMENT_USASPENDING_ENABLED",
        "ENRICHMENT_OFAC_OFFERED",
        "ENRICHMENT_OFAC_ENABLED",
        "ENRICHMENT_MOCK_OFFERED",
        "ENRICHMENT_MOCK_ENABLED",
    )
    return any(_mapping_optional_bool(source, key) is True for key in legacy_keys)


def _resolve_enabled_with_fallback(source: Mapping[str, str], primary_key: str, legacy_keys: tuple[str, ...]) -> bool:
    primary = _mapping_optional_bool(source, primary_key)
    if primary is not None:
        return primary
    for key in legacy_keys:
        candidate = _mapping_optional_bool(source, key)
        if candidate is not None:
            return candidate
    return False


def _mapping_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    candidate = _mapping_optional_bool(source, key)
    if candidate is None:
        return default
    return candidate


def _mapping_optional_bool(source: Mapping[str, str], key: str) -> bool | None:
    raw = source.get(key)
    if raw is None:
        return None
    candidate = str(raw).strip().lower()
    if candidate == "":
        return None
    return candidate == "true"


def _mapping_text(source: Mapping[str, str], key: str) -> str | None:
    return _clean_text(source.get(key))


def _clean_text(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None

