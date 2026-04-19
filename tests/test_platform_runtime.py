from verification.enrichments import EvaluationContext, TenantIntegrationSetting
from verification.platform.runtime import QueryRuntimeConfig, RefreshRuntimeConfig, build_athena_client, build_enrichment_service


def test_build_athena_client_from_runtime_config(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    client = build_athena_client(
        QueryRuntimeConfig(
            database="db",
            table="table",
            workgroup="wg",
            form990_filings_table="f1",
            form990_metrics_table="f2",
            form990_governance_table="f3",
            form990_quality_table="f4",
        )
    )
    assert client._database == "db"
    assert client._table == "table"


def test_build_enrichment_service_from_runtime_config():
    service = build_enrichment_service(
        RefreshRuntimeConfig(
            database="db",
            table="table",
            workgroup=None,
            form990_filings_table="f1",
            form990_metrics_table="f2",
            form990_governance_table="f3",
            form990_quality_table="f4",
            enrichment_mock_enabled=True,
            enrichment_state_registry_mock_enabled=True,
        )
    )
    result = service.enrich("123456789")
    payload = result.to_dict()
    assert "providers" in payload
    assert "source_catalog" in payload


def test_build_enrichment_service_defaults_to_no_offered_integrations():
    service = build_enrichment_service(
        RefreshRuntimeConfig(
            database="db",
            table="table",
            workgroup=None,
            form990_filings_table="f1",
            form990_metrics_table="f2",
            form990_governance_table="f3",
            form990_quality_table="f4",
        )
    )
    payload = service.enrich("123456789").to_dict()
    assert payload["providers"] == []
    assert payload["integration_evaluation"]["integrations"] == []
    assert payload["source_catalog"]["provider_capabilities"] == []


def test_build_enrichment_service_distinguishes_offered_from_credentials():
    service = build_enrichment_service(
        RefreshRuntimeConfig(
            database="db",
            table="table",
            workgroup=None,
            form990_filings_table="f1",
            form990_metrics_table="f2",
            form990_governance_table="f3",
            form990_quality_table="f4",
            enrichment_candid_offered=True,
            enrichment_candid_enabled=True,
        )
    )
    payload = service.enrich(
        "123456789",
        evaluation_context=EvaluationContext(
            integration_settings={"candid": TenantIntegrationSetting(enabled=True, required_for_eligibility=True)}
        ),
    ).to_dict()
    assert payload["providers"] == []
    assert payload["integration_evaluation"]["required_unmet_integrations"] == ["candid"]
    assert payload["integration_evaluation"]["integrations"][0]["availability_status"] == "missing_credentials"


def test_build_enrichment_service_supports_state_registry_adapter_path_without_legacy_endpoint():
    service = build_enrichment_service(
        RefreshRuntimeConfig(
            database="db",
            table="table",
            workgroup=None,
            form990_filings_table="f1",
            form990_metrics_table="f2",
            form990_governance_table="f3",
            form990_quality_table="f4",
            enrichment_state_registry_offered=True,
            enrichment_state_registry_enabled=True,
            enrichment_state_registry_colorado_enabled=True,
        )
    )
    payload = service.enrich(
        "123456789",
        organization_name="Colorado Example Org",
        jurisdiction_state="CO",
    ).to_dict()
    integrations = payload["integration_evaluation"]["integrations"]
    assert integrations[0]["integration_id"] == "state_registry"
    assert integrations[0]["credentials_present"] is True
    assert integrations[0]["availability_status"] == "tenant_disabled"


def test_build_enrichment_service_skips_disabled_premium_integrations_without_provider_failures():
    service = build_enrichment_service(
        RefreshRuntimeConfig(
            database="db",
            table="table",
            workgroup=None,
            form990_filings_table="f1",
            form990_metrics_table="f2",
            form990_governance_table="f3",
            form990_quality_table="f4",
            enrichment_candid_offered=True,
            enrichment_candid_enabled=True,
        )
    )
    payload = service.enrich(
        "123456789",
        evaluation_context=EvaluationContext(
            organization_integration_settings={
                "candid": TenantIntegrationSetting(enabled=False, required_for_eligibility=False)
            }
        ),
    ).to_dict()

    assert payload["providers"] == []
    assert payload["failures"] == []
    assert payload["integration_evaluation"]["integrations"][0]["integration_id"] == "candid"
    assert payload["integration_evaluation"]["integrations"][0]["availability_status"] == "tenant_disabled"

