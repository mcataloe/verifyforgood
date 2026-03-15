import importlib
import json
import sys
from decimal import Decimal
from types import SimpleNamespace

from charity_status.enrichments import InMemoryOrganizationIntegrationSettingsStore, OrganizationIntegrationSettingsService, load_organization_integration_settings
from charity_status.scoring import SCORING_MODEL_VERSION


def _load_module():
    sys.modules.pop("infrastructure.lambda_query", None)
    return importlib.import_module("infrastructure.lambda_query")


def _sample_record(name="Test Org", status="1"):
    return {
        "name": name,
        "state": "IL",
        "status": status,
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "filing_req_cd": "1",
        "asset_amt": "",
        "income_amt": "",
        "revenue_amt": "",
    }


def _mock_client(
    record=None,
    filings=None,
    metrics=None,
    governance=None,
    quality=None,
    filing_rows=None,
    peer_stats=None,
    search_rows=None,
):
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", record),
        lookup_form990_enrichment=lambda ein: (filings, metrics, governance, quality),
        list_form990_filings=lambda ein, limit=10: ("qid-f", filing_rows or []),
        lookup_peer_benchmark=lambda group: peer_stats or {"count": 0, "metrics": {}},
        search_nonprofits=lambda **kwargs: ("qid-s", search_rows or []),
    )


def _mock_enrichment(providers=None, failures=None):
    return SimpleNamespace(to_dict=lambda: {"providers": providers or [], "failures": failures or []})


def test_invalid_ein_still_returns_400():
    module = _load_module()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "12-34A6789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "invalid characters" in body["message"]


def test_lookup_hit_path_returns_materialized_profile():
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active"},
            "scores": {"overall": 88},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION, "peer_benchmarking_used": False},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve"},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        }
    )

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Cached Org"
    assert body["scores"]["overall"] == 88
    assert body["evidence"]["model_version"] == SCORING_MODEL_VERSION
    assert body["state_compliance"]["registration_status"] == "active"


def test_lookup_hit_path_refreshes_stale_materialized_profile():
    module = _load_module()
    put_calls = []
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "unknown"},
            "scores": {"overall": 45},
            "score_explanation": {"model_version": "2.0.0", "peer_benchmarking_used": False, "eligibility": "INELIGIBLE", "factors": {"active_status": False}},
            "model_version": "2.0.0",
            "decision": {"status": "deny"},
            "audit": {"model_version": "2.0.0"},
            "summary": {"decision_status": "deny"},
            "evidence": {"model_version": "2.0.0", "factors": []},
        },
        put_profile=lambda item: put_calls.append(item),
    )
    module.athena_client = _mock_client(record=_sample_record("Fresh Org", status="01"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Fresh Org"
    assert body["verification"]["irs_status"] == "active"
    assert len(put_calls) == 1
    assert put_calls[0]["model_version"] == SCORING_MODEL_VERSION


def test_lookup_miss_then_fallback_materialize_nonprod_lazy():
    module = _load_module()
    put_calls = []
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.APP_ENV = "dev"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: None,
        put_profile=lambda item: put_calls.append(item),
    )
    module.athena_client = _mock_client(record=_sample_record("Fresh Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Fresh Org"
    assert len(put_calls) == 1
    assert put_calls[0]["pk"] == "EIN#123456789"


def test_post_verify_bypasses_cache_readthrough():
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {"organization": {"name": "Cached Org"}},
        put_profile=lambda item: None,
    )
    module.athena_client = _mock_client(record=_sample_record("Post Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Post Org"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Post Org"


def test_post_verify_accepts_policy_id_and_returns_policy_evaluation():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Policy Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Policy Org", "policy_id": "strict_deny"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["policy_evaluation"]["policy_id"] == "strict_deny"
    assert "final_recommendation" in body


def test_post_verify_accepts_weighting_profile():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Weighted Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Weighted Org", "weighting_profile": "compliance_heavy_v1"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["score_explanation"]["weighting_profile"]["applied"] == "compliance_heavy_v1"
    assert body["audit"]["weighting_profile"]["applied"] == "compliance_heavy_v1"


def test_response_shape_still_contains_core_fields():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Test Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    body = json.loads(module.handler(event, None)["body"])

    for key in [
        "organization",
        "verification",
        "scores",
        "score_explanation",
        "decision",
        "audit",
        "summary",
        "evidence",
        "policy_evaluation",
        "final_recommendation",
        "state_compliance",
    ]:
        assert key in body


def test_lookup_hit_path_with_dynamodb_decimal_values_is_serializable():
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active"},
            "scores": {"overall": Decimal("88.5")},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION, "peer_benchmarking_used": False},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve"},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        }
    )

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["scores"]["overall"] == 88.5


def test_lookup_hit_path_recomputes_tenant_required_integrations(monkeypatch):
    monkeypatch.setenv(
        "ORGANIZATION_INTEGRATION_SETTINGS_JSON",
        json.dumps(
            [
                {
                    "workspace_id": "ws_1",
                    "integrations": {
                        "candid": {"enabled": True, "requiredForEvaluation": True}
                    },
                }
            ]
        ),
    )
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active", "recent_990_on_file": True},
            "scores": {"overall": 88},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION, "peer_benchmarking_used": False, "eligibility": "ELIGIBLE", "factors": {}},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve", "risk_flags": [], "manual_review": {"reason_codes": []}},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        }
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(subject="tenant", scopes=(), metadata={}, workspace_id="ws_1", account_id="acct_1")

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["integration_evaluation"]["required_unmet_integrations"] == ["candid"]
    assert body["decision"]["status"] == "manual_review"


def test_get_organization_integrations_returns_current_settings():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore(
        [
            {
                "workspace_id": "ws_1",
                "account_id": "acct_1",
                "integrations": {
                    "candid": {"enabled": True, "requiredForEvaluation": False},
                },
            }
        ]
    )
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(subject="tenant", scopes=("verify:read",), metadata={}, workspace_id="ws_1", account_id="acct_1", plan_id="team")

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {"httpMethod": "GET", "resource": "/organizations/integrations", "path": "/organizations/integrations", "headers": {}}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["workspace_id"] == "ws_1"
    assert body["integrations"]["candid"]["enabled"] is True
    assert body["integrations"]["charityNavigator"]["enabled"] is False


def test_put_organization_integrations_updates_settings():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore()
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(subject="tenant", scopes=("verify:write",), metadata={}, workspace_id="ws_1", account_id="acct_1", plan_id="team")

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "PUT",
        "resource": "/organizations/integrations",
        "path": "/organizations/integrations",
        "headers": {},
        "body": json.dumps({"integrations": {"candid": {"enabled": True, "requiredForEvaluation": True}}}),
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["source"] == "stored"
    assert body["integrations"]["candid"]["requiredForEvaluation"] is True

    fetched = module.organization_integration_settings_store.get_settings(workspace_id="ws_1", account_id="acct_1")
    assert fetched["integrations"]["candid"]["enabled"] is True


def test_put_organization_integrations_rejects_required_disabled():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore()
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(subject="tenant", scopes=("verify:write",), metadata={}, workspace_id="ws_1", account_id="acct_1", plan_id="team")

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "PUT",
        "resource": "/organizations/integrations",
        "path": "/organizations/integrations",
        "headers": {},
        "body": json.dumps({"integrations": {"candid": {"enabled": False, "requiredForEvaluation": True}}}),
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "requiredForEvaluation" in body["message"]


def test_post_verify_batch_all_success():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/verify/batch",
        "path": "/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321", "name": "Batch Org"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["batch_summary"]["total"] == 2
    assert body["batch_summary"]["success"] == 2
    assert body["batch_summary"]["error"] == 0


def test_post_verify_batch_partial_invalid_input():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/verify/batch",
        "path": "/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "invalid"}, {"ein": "987654321"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    body = json.loads(module.handler(event, None)["body"])
    assert body["batch_summary"]["success"] == 2
    assert body["batch_summary"]["error"] == 1
    assert body["batch_summary"]["counts_by_error"]["invalid_ein"] == 1


def test_post_verify_batch_missing_ein_rows():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/verify/batch",
        "path": "/verify/batch",
        "body": json.dumps({"items": [{"name": "No EIN"}, {"ein": "123456789"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    body = json.loads(module.handler(event, None)["body"])
    assert body["batch_summary"]["error"] == 1
    assert body["batch_summary"]["counts_by_error"]["missing_ein"] == 1


def test_post_verify_batch_duplicate_eins_are_processed_independently():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/verify/batch",
        "path": "/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "123456789"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    body = json.loads(module.handler(event, None)["body"])
    assert body["batch_summary"]["total"] == 2
    assert body["batch_summary"]["success"] == 2
    assert len(body["items"]) == 2


def test_post_verify_batch_enforces_size_limit():
    module = _load_module()
    module.BATCH_VERIFY_MAX_SIZE = 1
    event = {
        "httpMethod": "POST",
        "resource": "/verify/batch",
        "path": "/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 400
    assert "maximum of 1" in body["message"]


def test_post_verify_batch_reuses_cache_for_get_style_item():
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active"},
            "scores": {"overall": 88},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve"},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        },
        put_profile=lambda item: None,
    )

    event = {
        "httpMethod": "POST",
        "resource": "/verify/batch",
        "path": "/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["items"][0]["item"]["organization"]["name"] == "Cached Org"


def test_nonprofits_search_exactish_name():
    module = _load_module()
    module.SEARCH_DEFAULT_LIMIT = 20
    module.SEARCH_MAX_LIMIT = 50
    module.athena_client = _mock_client(
        search_rows=[
            {
                "ein": "123456789",
                "name": "Helping Hands Foundation",
                "state": "IL",
                "subsection": "03",
                "status": "1",
                "tax_period": "202501",
            }
        ]
    )
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/search",
        "path": "/nonprofits/search",
        "queryStringParameters": {"q": "helping hands"},
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["items"][0]["name"] == "Helping Hands Foundation"
    assert body["items"][0]["ein"] == "12-3456789"


def test_nonprofits_search_filtered_search():
    module = _load_module()
    captured = {}

    def search_nonprofits(**kwargs):
        captured.update(kwargs)
        return "qid-s", []

    module.athena_client = SimpleNamespace(search_nonprofits=search_nonprofits)
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/search",
        "path": "/nonprofits/search",
        "queryStringParameters": {"q": "org", "state": "il", "subsection": "03", "active_only": "true", "limit": "5"},
    }
    result = module.handler(event, None)
    assert result["statusCode"] == 200
    assert captured["state"] == "IL"
    assert captured["subsection"] == "03"
    assert captured["active_only"] is True
    assert captured["limit"] == 5


def test_nonprofits_search_pagination_cursor():
    module = _load_module()
    module.athena_client = _mock_client(
        search_rows=[
            {"ein": "123456789", "name": "A Org", "state": "IL", "subsection": "03", "status": "1", "tax_period": "202501"},
            {"ein": "223456789", "name": "B Org", "state": "IL", "subsection": "03", "status": "1", "tax_period": "202501"},
        ]
    )
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/search",
        "path": "/nonprofits/search",
        "queryStringParameters": {"q": "org", "limit": "2"},
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["pagination"]["next_cursor"] is not None


def test_nonprofits_search_invalid_limit_handling():
    module = _load_module()
    module.SEARCH_MAX_LIMIT = 10
    module.athena_client = _mock_client(search_rows=[])
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/search",
        "path": "/nonprofits/search",
        "queryStringParameters": {"q": "org", "limit": "100"},
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 400
    assert "between 1 and 10" in body["message"]


def test_nonprofits_sources_supported_source_lookup():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "state_registry_mock",
                        "status": "matched",
                        "fields": {
                            "registration_status": "active",
                            "registration_jurisdiction": "IL",
                            "registration_expiration_date": "2026-12-31",
                            "solicitation_permitted": True,
                            "compliance_flags": [],
                        },
                        "source": {"record_id": "sr-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    }
                ],
                "failures": [],
            }
        )
    )
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/{ein}/sources/{source_name}",
        "path": "/nonprofits/123456789/sources/state_registry_mock",
        "pathParameters": {"ein": "123456789", "source_name": "state_registry_mock"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["source"]["source_name"] == "state_registry_mock"
    assert body["source"]["normalized_data"]["registration_status"] == "active"


def test_nonprofits_sources_unsupported_source_name():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/{ein}/sources/{source_name}",
        "path": "/nonprofits/123456789/sources/unknown_source",
        "pathParameters": {"ein": "123456789", "source_name": "unknown_source"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 404
    assert "Unsupported source name" in body["message"]


def test_nonprofits_compliance_no_source_data_case():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/{ein}/compliance",
        "path": "/nonprofits/123456789/compliance",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["compliance"]["status"] == "unavailable"


def test_nonprofits_sources_no_source_data_case():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/{ein}/sources",
        "path": "/nonprofits/123456789/sources",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["sources"] == []
    assert body["failures"] == []


def test_nonprofits_compliance_summary_aggregation():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "state_registry_mock",
                        "status": "matched",
                        "fields": {
                            "registration_status": "active",
                            "registration_jurisdiction": "IL",
                            "registration_expiration_date": "2026-12-31",
                            "solicitation_permitted": True,
                            "compliance_flags": ["late_filing_notice"],
                        },
                        "source": {"record_id": "sr-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    },
                    {
                        "name": "state_business_mock",
                        "status": "matched",
                        "fields": {
                            "entity_status": "good_standing",
                            "good_standing": True,
                            "compliance_flags": ["registered_agent_issue"],
                        },
                        "source": {"record_id": "sb-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    },
                ],
                "failures": [],
            }
        )
    )
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/{ein}/compliance",
        "path": "/nonprofits/123456789/compliance",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["compliance"]["status"] == "available"
    assert body["compliance"]["registration_status"] == "active"
    assert body["compliance"]["state_business_status"] == "good_standing"
    assert body["compliance"]["compliance_flags"] == ["late_filing_notice", "registered_agent_issue"]


def test_nonprofits_federal_awards_summary_response():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "usaspending_mock",
                        "status": "matched",
                        "fields": {
                            "award_count": 5,
                            "total_obligations_usd": 320000.0,
                            "latest_award_date": "2025-11-01",
                        },
                        "source": {"record_id": None, "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    }
                ],
                "failures": [],
            }
        )
    )
    event = {
        "httpMethod": "GET",
        "resource": "/nonprofits/{ein}/federal-awards",
        "path": "/nonprofits/123456789/federal-awards",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["federal_awards"]["status"] == "available"
    assert body["federal_awards"]["award_count"] == 5


def test_handler_invokes_auth_and_quota_hooks():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Hook Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    calls = []

    class _AuthProvider:
        def extract_context(self, event):
            calls.append(("auth", event.get("httpMethod")))
            return SimpleNamespace(subject="anonymous", scopes=(), metadata={})

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            calls.append(("request", route_key, auth_context.subject))

        def on_response(self, auth_context, route_key, status_code):
            calls.append(("response", route_key, status_code))

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)

    assert result["statusCode"] == 200
    assert calls[0] == ("auth", "GET")
    assert calls[1][0] == "request"
    assert calls[-1][0] == "response"
    assert calls[-1][2] == 200


def test_ops_ingest_runs_listing_and_detail():
    module = _load_module()
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=50: [{"ingest_run_id": "ing-1", "status": "success"}] if run_type == "ingest" else [],
        get_run=lambda run_type, run_id: {"ingest_run_id": run_id, "status": "partial_success"} if run_type == "ingest" else None,
        get_run_items=lambda run_type, run_id, item_name: [{"ein": "123456789"}] if (run_type, item_name) == ("ingest", "filings") else None,
    )
    module.OPS_METADATA_BUCKET = "test-bucket"

    list_result = module.handler({"httpMethod": "GET", "resource": "/ops/ingest/runs", "headers": {}}, None)
    detail_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/ops/ingest/runs/{ingest_run_id}",
            "pathParameters": {"ingest_run_id": "ing-1"},
            "headers": {},
        },
        None,
    )
    filings_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/ops/ingest/runs/{ingest_run_id}/filings",
            "pathParameters": {"ingest_run_id": "ing-1"},
            "headers": {},
        },
        None,
    )
    assert list_result["statusCode"] == 200
    assert detail_result["statusCode"] == 200
    assert filings_result["statusCode"] == 200


def test_ops_refresh_runs_listing_and_not_found():
    module = _load_module()
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=50: [{"refresh_run_id": "ref-1", "status": "completed"}] if run_type == "refresh" else [],
        get_run=lambda run_type, run_id: None,
        get_run_items=lambda run_type, run_id, item_name: None,
    )
    module.OPS_METADATA_BUCKET = "test-bucket"
    list_result = module.handler({"httpMethod": "GET", "resource": "/ops/refresh/runs", "headers": {}}, None)
    detail_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/ops/refresh/runs/{refresh_run_id}",
            "pathParameters": {"refresh_run_id": "ref-missing"},
            "headers": {},
        },
        None,
    )
    assert list_result["statusCode"] == 200
    assert detail_result["statusCode"] == 404


def test_ops_pipeline_status_lookup_and_not_found():
    module = _load_module()
    module.OPS_METADATA_BUCKET = "test-bucket"
    module.profile_store = SimpleNamespace(get_profile=lambda ein: {"materialized_at": "2026-03-12T00:00:00Z", "source_hash": "abc", "model_version": SCORING_MODEL_VERSION, "environment": "dev"})
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=100: [{"ingest_run_id": "ing-1", "status": "success"}] if run_type == "ingest" else [{"refresh_run_id": "ref-1", "status": "completed"}],
        get_run_items=lambda run_type, run_id, item_name: [{"ein": "123456789"}],
        get_run=lambda run_type, run_id: None,
    )
    ok = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/ops/nonprofits/{ein}/pipeline-status",
            "pathParameters": {"ein": "123456789"},
            "headers": {},
        },
        None,
    )
    assert ok["statusCode"] == 200

    module.profile_store = SimpleNamespace(get_profile=lambda ein: None)
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=100: [],
        get_run_items=lambda run_type, run_id, item_name: [],
        get_run=lambda run_type, run_id: None,
    )
    missing = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/ops/nonprofits/{ein}/pipeline-status",
            "pathParameters": {"ein": "123456789"},
            "headers": {},
        },
        None,
    )
    assert missing["statusCode"] == 404
