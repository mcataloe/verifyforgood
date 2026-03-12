from charity_status.platform.runtime import QueryRuntimeConfig, RefreshRuntimeConfig, build_athena_client, build_enrichment_service


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
