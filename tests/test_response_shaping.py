from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace

from charity_status.auth import InMemoryUsageStore, build_api_key_record


def _query_stub():
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: (
            "qid-1",
            {
                "ein": ein,
                "name": "Shaped Org",
                "state": "IL",
                "status": "1",
                "deductibility": "1",
                "subsection": "03",
                "ntee_cd": "P20",
                "tax_period": "202501",
                "filing_req_cd": "1",
                "asset_amt": "100",
                "income_amt": "200",
                "revenue_amt": "300",
            },
        ),
        lookup_form990_enrichment=lambda ein: (
            {"tax_year": 2024, "return_type": "990", "filing_date": "2025-02-01", "amended_return": False, "parse_status": "parsed", "total_revenue": 1000},
            {"program_ratio": 0.8},
            {"independent_board_members": 5},
            {"completeness": 0.9},
        ),
        lookup_peer_benchmark=lambda group: {"count": 10, "metrics": {"program_ratio": {"median": 0.7}}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )


def _enrichment_stub():
    return SimpleNamespace(
        to_dict=lambda: {
            "providers": [
                {"name": "state_registry_mock", "status": "matched"},
                {"name": "usaspending_mock", "status": "matched"},
            ],
            "failures": [],
            "integration_evaluation": {
                "integrations": [{"integration_id": "state_registry", "attempted": True}],
                "attempted_integrations": ["state_registry"],
                "used_integrations": ["state_registry"],
                "required_unmet_integrations": [],
                "failure_integrations": [],
            },
        }
    )


def _load_module(monkeypatch, *, plan_code: str):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    api_key, record = build_api_key_record(
        key_id=f"{plan_code}_001",
        secret="shape-secret",
        account_id=f"acct_{plan_code}",
        workspace_id=f"ws_{plan_code}",
        scopes=["verify:read", "verify:write", "compliance:read"],
        plan_id=plan_code,
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda **kwargs: _enrichment_stub())
    module.usage_store = InMemoryUsageStore()
    return module, api_key


def _data(response):
    return json.loads(response["body"])["data"]


def _meta(response):
    return json.loads(response["body"])["meta"]


def test_free_plan_shapes_nonprofit_lookup_with_upgrade_hints(monkeypatch):
    module, api_key = _load_module(monkeypatch, plan_code="free")

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/{ein}",
            "path": "/v1/nonprofits/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": api_key},
        },
        None,
    )
    payload = _data(response)

    assert response["statusCode"] == 200
    assert "scores" not in payload
    assert "score_explanation" not in payload
    assert "state_compliance" not in payload
    assert payload["upgrade_hints"]["risk_flags"] == "available_on_growth"
    assert payload["upgrade_hints"]["financial_trends"] == "available_on_growth"


def test_growth_plan_includes_risk_and_financial_fields_but_redacts_monitoring(monkeypatch):
    module, api_key = _load_module(monkeypatch, plan_code="growth")

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/nonprofits/verify",
            "path": "/v1/nonprofits/verify",
            "headers": {"x-api-key": api_key, "Content-Type": "application/json"},
            "body": json.dumps({"ein": "123456789", "name": "Shaped Org"}),
        },
        None,
    )
    payload = _data(response)

    assert response["statusCode"] == 200
    assert "scores" in payload
    assert "score_explanation" in payload
    assert "state_compliance" in payload
    assert "audit" not in payload
    assert payload["upgrade_hints"]["state_registry"] == "available_on_pro"
    assert payload["upgrade_hints"]["monitoring"] == "available_on_pro"


def test_feature_unavailable_error_includes_upgrade_plan(monkeypatch):
    module, api_key = _load_module(monkeypatch, plan_code="free")

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/{ein}/compliance",
            "path": "/v1/nonprofits/123456789/compliance",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": api_key},
        },
        None,
    )
    body = json.loads(response["body"])

    assert response["statusCode"] == 403
    assert body["errors"][0]["code"] == "feature_unavailable"
    assert _meta(response)["feature_flag"] == "risk_flags"
    assert _meta(response)["upgrade_plan"] == "growth"
