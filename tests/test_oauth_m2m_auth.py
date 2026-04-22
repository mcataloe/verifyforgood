from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace

from verification.backend.shared.auth import InMemoryUsageStore, build_api_key_record, build_oauth_client_record, build_oauth_token_record
from verification.backend.shared.auth.errors import AuthenticationError
from verification.backend.shared.auth.oauth import StaticOAuthClientStore, StaticOAuthTokenStore, authenticate_bearer_token, authenticate_oauth_client_credentials
from verification.backend.shared.platform.auth import OAuthClientCredentialsService


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


def _response_data(response):
    return json.loads(response["body"])["data"]


def test_valid_bearer_token_path():
    token, record = build_oauth_token_record(
        client_id="client_1",
        token="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="growth",
    )
    principal = authenticate_bearer_token({"Authorization": f"Bearer {token}"}, StaticOAuthTokenStore([record]))
    assert principal.client_id == "client_1"
    assert principal.account_id == "acct_1"
    assert principal.auth_method == "oauth_client_credentials"


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


def test_oauth_client_secret_plaintext_only_returned_at_creation():
    client_secret, record = build_oauth_client_record(
        client_id="client_1",
        client_secret="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
    )
    assert client_secret == "oauth-secret"
    assert record.client_secret_hash != "oauth-secret"
    assert not hasattr(record, "client_secret")


def test_oauth_client_credentials_issue_signed_access_token():
    client_secret, record = build_oauth_client_record(
        client_id="client_1",
        client_secret="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["oauth:token", "verify:read"],
        plan_id="growth",
    )
    principal = authenticate_oauth_client_credentials("client_1", client_secret, StaticOAuthClientStore([record]))
    service = OAuthClientCredentialsService(StaticOAuthClientStore([record]), token_ttl_seconds=1800)

    context, token_payload = service.issue_token("client_1", client_secret)
    bearer_principal = authenticate_bearer_token(
        {"Authorization": f"Bearer {token_payload['access_token']}"},
        client_store=StaticOAuthClientStore([record]),
    )

    assert principal.client_id == "client_1"
    assert context.credential_id == "client_1"
    assert context.auth_method == "oauth_client_credentials"
    assert context.plan == "growth"
    assert context.subscription is not None
    assert context.subscription.plan_code == "growth"
    assert token_payload["token_type"] == "Bearer"
    assert token_payload["expires_in"] == 1800
    assert bearer_principal.client_id == "client_1"


def test_scope_enforcement_for_oauth(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    token, record = build_oauth_token_record(
        client_id="client_1",
        token="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="growth",
    )
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", json.dumps([record.__dict__]))
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", "[]")
    monkeypatch.setenv("API_KEY_RECORDS_JSON", "[]")
    sys.modules.pop("verification.backend.customer.api.runtime", None)
    module = importlib.import_module("verification.backend.customer.api.runtime")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()
    response = module.handle_api_event(
        {
            "httpMethod": "POST",
            "resource": "/v1/verify",
            "path": "/v1/verify",
            "headers": {"Authorization": f"Bearer {token}"},
            "body": json.dumps({"ein": "123456789"}),
        },
        None,
    )
    assert response["statusCode"] == 403


def test_oauth_token_endpoint_returns_access_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    client_secret, client_record = build_oauth_client_record(
        client_id="client_1",
        client_secret="oauth-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["oauth:token", "verify:read"],
        plan_id="growth",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", json.dumps([client_record.__dict__]))
    sys.modules.pop("verification.backend.customer.api.runtime", None)
    module = importlib.import_module("verification.backend.customer.api.runtime")

    response = module.handle_api_event(
        {
            "httpMethod": "POST",
            "resource": "/v1/oauth/token",
            "path": "/v1/oauth/token",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"client_id": "client_1", "client_secret": client_secret}),
        },
        None,
    )
    body = _response_data(response)

    assert response["statusCode"] == 200
    assert body["token_type"] == "Bearer"
    assert body["access_token"].startswith("oct_")
    assert body["expires_in"] == 3600


def test_coexistence_api_key_and_oauth(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    api_key, key_record = build_api_key_record(
        key_id="dev_001",
        secret="key-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    client_secret, oauth_client_record = build_oauth_client_record(
        client_id="client_1",
        client_secret="oauth-secret",
        account_id="acct_2",
        workspace_id="ws_2",
        scopes=["oauth:token", "verify:read"],
        plan_id="growth",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([key_record.__dict__]))
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", json.dumps([oauth_client_record.__dict__]))
    sys.modules.pop("verification.backend.customer.api.runtime", None)
    module = importlib.import_module("verification.backend.customer.api.runtime")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()

    token_response = module.handle_api_event(
        {
            "httpMethod": "POST",
            "resource": "/v1/oauth/token",
            "path": "/v1/oauth/token",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"client_id": "client_1", "client_secret": client_secret}),
        },
        None,
    )
    token = _response_data(token_response)["access_token"]

    api_key_response = module.handle_api_event(
        {"httpMethod": "GET", "resource": "/v1/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {"x-api-key": api_key}},
        None,
    )
    oauth_response = module.handle_api_event(
        {"httpMethod": "GET", "resource": "/v1/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {"Authorization": f"Bearer {token}"}},
        None,
    )
    assert api_key_response["statusCode"] == 403
    assert oauth_response["statusCode"] == 403


