import importlib
import json
import sys
from decimal import Decimal
from types import SimpleNamespace


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


def _mock_client(record=None, filings=None, metrics=None, governance=None, quality=None, filing_rows=None, peer_stats=None):
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", record),
        lookup_form990_enrichment=lambda ein: (filings, metrics, governance, quality),
        list_form990_filings=lambda ein, limit=10: ("qid-f", filing_rows or []),
        lookup_peer_benchmark=lambda group: peer_stats or {"count": 0, "metrics": {}},
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
            "score_explanation": {"model_version": "2.0.0", "peer_benchmarking_used": False},
            "model_version": "2.0.0",
            "decision": {"status": "approve"},
            "audit": {"model_version": "2.0.0"},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": "2.0.0", "factors": []},
        }
    )

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Cached Org"
    assert body["scores"]["overall"] == 88
    assert body["evidence"]["model_version"] == "2.0.0"


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
            "score_explanation": {"model_version": "2.0.0", "peer_benchmarking_used": False},
            "model_version": "2.0.0",
            "decision": {"status": "approve"},
            "audit": {"model_version": "2.0.0"},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": "2.0.0", "factors": []},
        }
    )

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["scores"]["overall"] == 88.5


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
            "score_explanation": {"model_version": "2.0.0"},
            "model_version": "2.0.0",
            "decision": {"status": "approve"},
            "audit": {"model_version": "2.0.0"},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": "2.0.0", "factors": []},
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
