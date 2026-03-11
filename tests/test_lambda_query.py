import importlib
import json
import sys
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


def test_get_handler_invalid_ein_returns_400():
    module = _load_module()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "12-34A6789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "invalid characters" in body["message"]


def test_get_handler_not_found_returns_404():
    module = _load_module()
    module.athena_client = _mock_client(record=None)

    event = {"httpMethod": "GET", "pathParameters": {"ein": "12-3456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert body["ein"] == "123456789"


def test_post_verify_success_with_enrichment_and_peer():
    module = _load_module()
    module.athena_client = _mock_client(
        record=_sample_record("Helping Hands Inc."),
        filings={"tax_year": "2023", "return_type": "990", "filing_date": "2024-05-15", "amended_return": "false", "parse_status": "parsed", "mission_description_present": True, "program_accomplishments_present": True, "leadership_disclosed": True, "total_revenue": "1500000"},
        metrics={"programExpenseRatio": 0.8, "liabilitiesToAssetsRatio": 0.4, "monthsOfRunway": 8, "operatingMargin": 0.06},
        governance={"whistleblower_policy": True, "material_diversion_reported": False, "public_disclosure_available": True},
        quality={"narrativeMissing": False, "scoreConfidence": "high"},
        peer_stats={
            "count": 100,
            "metrics": {
                "programExpenseRatio": {"p25": 0.6, "median": 0.7, "p75": 0.78},
                "liabilitiesToAssetsRatio": {"p25": 0.3, "median": 0.45, "p75": 0.6},
                "operatingMargin": {"p25": 0.0, "median": 0.03, "p75": 0.08},
                "monthsOfRunway": {"p25": 4, "median": 6, "p75": 9},
            },
        },
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment(
        providers=[{"name": "mock_provider", "status": "matched", "fields": {"transparency_level": "gold"}, "source": {"record_id": "mock-123", "fetched_at": "x", "licensed": False}}],
        failures=[]
    ))

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "12-3456789", "name": "Helping Hands"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["score_explanation"]["model_version"] == "2.0.0"
    assert body["score_explanation"]["peer_benchmarking_used"] is True
    assert body["score_explanation"]["peer_group_size"] == 100
    assert "program_expense_ratio" in body["score_explanation"]["benchmarked_metrics"]


def test_get_fallback_without_990_data():
    module = _load_module()
    module.athena_client = _mock_client(record=_sample_record("Test Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["score_explanation"]["score_data_sources"] == ["irs_eo_bmf_athena"]
    assert body["score_explanation"]["peer_benchmarking_used"] is False


def test_post_verify_invalid_request_body():
    module = _load_module()

    event = {
        "httpMethod": "POST",
        "body": "{bad json",
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "valid JSON" in body["message"]


def test_get_nonprofit_filings_endpoint_shape():
    module = _load_module()
    module.athena_client = _mock_client(
        record=_sample_record("Test Org"),
        filing_rows=[
            {"tax_year": "2023", "return_type": "990", "filing_date": "2024-05-01", "amended_return": "false", "parse_status": "parsed"},
            {"tax_year": "2022", "return_type": "990", "filing_date": "2023-05-01", "amended_return": "true", "parse_status": "parsed"},
        ],
    )

    event = {
        "httpMethod": "GET",
        "resource": "/nonprofit/{ein}/filings",
        "path": "/nonprofit/123456789/filings",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["ein"] == "123456789"
    assert len(body["filings"]) == 2
