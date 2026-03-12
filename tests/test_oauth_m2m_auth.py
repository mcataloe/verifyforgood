from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace

from charity_status.auth import InMemoryUsageStore, build_api_key_record, build_oauth_token_record
from charity_status.auth.errors import AuthenticationError
from charity_status.auth.oauth import StaticOAuthTokenStore, authenticate_bearer_token


def _query_stub():
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: (
            "qid-1",
            {
                "ein": ein,
                "name": "X",
                "state": "IL",
                "status": "1",
                "deductibility": "1",
                "subsection": "03",
                "ntee_cd": "P20",
                "tax_period": "202501",
                "filing_req_cd": "1",
                "asset_amt": "",
                "income_amt": "",
                "revenue_amt": "",
            },
        ),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )


def test_valid_bearer_token_path():
    token, record = build_oauth_token_record(
        client_id="client_1",
        token="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="team",
    )
    principal = authenticate_bearer_token({"Authorization": f"Bearer {token}"}, StaticOAuthTokenStore([record]))
    assert principal.client_id == "client_1"
    assert principal.account_id == "acct_1"


def test_invalid_bearer_token_path():
    _, record = build_oauth_token_record(
        client_id="client_1",
        token="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
    )
    try:
        authenticate_bearer_token({"Authorization": "Bearer bad-token"}, StaticOAuthTokenStore([record]))
    except AuthenticationError:
        pass
    else:
        assert False, "Expected AuthenticationError"


def test_scope_enforcement_for_oauth(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    token, record = build_oauth_token_record(
        client_id="client_1",
        token="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="team",
    )
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", json.dumps([record.__dict__]))
    monkeypatch.setenv("API_KEY_RECORDS_JSON", "[]")
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()
    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/verify",
            "path": "/verify",
            "headers": {"Authorization": f"Bearer {token}"},
            "body": json.dumps({"ein": "123456789"}),
        },
        None,
    )
    assert response["statusCode"] == 403


def test_coexistence_api_key_and_oauth(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    api_key, key_record = build_api_key_record(
        key_id="dev_001",
        secret="key-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="developer",
    )
    token, oauth_record = build_oauth_token_record(
        client_id="client_1",
        token="oauth-secret",
        account_id="acct_2",
        workspace_id="ws_2",
        scopes=["verify:read"],
        plan_id="team",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([key_record.__dict__]))
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", json.dumps([oauth_record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()

    api_key_response = module.handler(
        {"httpMethod": "GET", "resource": "/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {"x-api-key": api_key}},
        None,
    )
    oauth_response = module.handler(
        {"httpMethod": "GET", "resource": "/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {"Authorization": f"Bearer {token}"}},
        None,
    )
    assert api_key_response["statusCode"] == 200
    assert oauth_response["statusCode"] == 200
