from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace

from charity_status.auth import build_admin_key_record, build_api_key_record
from charity_status.auth.errors import QuotaExceededError
from charity_status.auth.oauth import authenticate_oauth_client_credentials
from charity_status.auth.service import authenticate_api_key, enforce_quota_and_scope
from charity_status.control_plane import ControlPlaneService, DynamoControlPlaneStore, FakeDynamoResource, FakeDynamoTable


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


class _ApiKeyLookupStore:
    def __init__(self, store: DynamoControlPlaneStore) -> None:
        self._store = store

    def get(self, key_id: str):
        return self._store.get_api_key_record(key_id)


class _OAuthLookupStore:
    def __init__(self, store: DynamoControlPlaneStore) -> None:
        self._store = store

    def get(self, client_id: str):
        return self._store.get_oauth_client_record(client_id)


def test_dynamo_control_plane_persists_accounts_and_subscriptions_across_service_instances():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)

    service = ControlPlaneService(store=DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))
    created = service.create_account({"id": "acct_dynamo", "name": "Dynamo Account"})
    service.update_subscription(
        "acct_dynamo",
        {
            "plan_code": "pro",
            "status": "active",
            "effective_from": "2026-03-18T00:00:00+00:00",
        },
    )

    reloaded = ControlPlaneService(store=DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))

    assert reloaded.get_account("acct_dynamo")["name"] == "Dynamo Account"
    assert reloaded.get_subscription("acct_dynamo")["plan_code"] == "pro"
    assert reloaded.list_accounts()[0]["id"] == created["id"]


def test_dynamo_control_plane_managed_credentials_authenticate_from_lookup_records():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    service.create_account({"id": "acct_auth", "name": "Auth Account"})

    api_key_payload = service.create_api_key("acct_auth", {"key_id": "key_auth", "plan": "growth"})
    oauth_payload = service.create_oauth_client("acct_auth", {"client_id": "client_auth", "plan": "growth"})

    api_principal = authenticate_api_key({"x-api-key": api_key_payload["secret"]}, _ApiKeyLookupStore(store))
    oauth_principal = authenticate_oauth_client_credentials(
        "client_auth",
        oauth_payload["client_secret"],
        _OAuthLookupStore(store),
    )

    api_record = store.get_api_key_record("key_auth")
    oauth_record = store.get_oauth_client_record("client_auth")

    assert api_principal.account_id == "acct_auth"
    assert oauth_principal.account_id == "acct_auth"
    assert api_record is not None and api_record.secret_hash != api_key_payload["secret"]
    assert oauth_record is not None and oauth_record.client_secret_hash != oauth_payload["client_secret"]


def test_dynamo_usage_persists_quota_state_across_service_reinitialization():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    service.create_account({"id": "acct_quota", "name": "Quota Account"})
    api_key_payload = service.create_api_key("acct_quota", {"key_id": "key_quota", "plan": "free"})

    principal = authenticate_api_key({"x-api-key": api_key_payload["secret"]}, _ApiKeyLookupStore(store))
    month_key, _, _ = enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", store)
    store.increment_usage("acct_quota", month_key, 250)

    reloaded_store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    try:
        enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", reloaded_store)
    except QuotaExceededError:
        pass
    else:
        assert False, "Expected QuotaExceededError"


def test_lambda_query_uses_dynamo_control_plane_when_table_name_is_configured(monkeypatch):
    import charity_status.control_plane.dynamodb_store as dynamodb_module

    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    admin_key, admin_record = build_admin_key_record("root", secret="admin-secret")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    monkeypatch.setenv("API_KEY_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", "[]")
    monkeypatch.setenv("ADMIN_KEY_RECORDS_JSON", json.dumps([admin_record.__dict__]))
    monkeypatch.setenv("CONTROL_PLANE_TABLE_NAME", "control-plane")
    monkeypatch.setattr(dynamodb_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))

    created = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {"x-admin-key": admin_key, "Content-Type": "application/json"},
            "body": json.dumps({"id": "acct_lambda_dynamo", "name": "Lambda Dynamo"}),
        },
        None,
    )
    assert created["statusCode"] == 201

    module.control_plane_service = None

    listed = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    payload = json.loads(listed["body"])

    assert listed["statusCode"] == 200
    assert payload["data"]["items"][0]["id"] == "acct_lambda_dynamo"


def test_managed_api_key_takes_precedence_over_bootstrap_env_record(monkeypatch):
    import charity_status.control_plane.dynamodb_store as dynamodb_module

    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    admin_key, admin_record = build_admin_key_record("root", secret="admin-secret")
    bootstrap_secret, bootstrap_record = build_api_key_record(
        key_id="dup_key",
        secret="env-secret",
        account_id="acct_bootstrap",
        workspace_id="acct_bootstrap",
        scopes=["verify:read"],
        plan_id="free",
    )
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([bootstrap_record.__dict__]))
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", "[]")
    monkeypatch.setenv("ADMIN_KEY_RECORDS_JSON", json.dumps([admin_record.__dict__]))
    monkeypatch.setenv("CONTROL_PLANE_TABLE_NAME", "control-plane")
    monkeypatch.setattr(dynamodb_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))

    account_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {"x-admin-key": admin_key, "Content-Type": "application/json"},
            "body": json.dumps({"id": "acct_managed", "name": "Managed Account"}),
        },
        None,
    )
    assert account_response["statusCode"] == 201

    created_key = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/api-keys",
            "path": "/v1/admin/accounts/acct_managed/api-keys",
            "pathParameters": {"accountId": "acct_managed"},
            "headers": {"x-admin-key": admin_key, "Content-Type": "application/json"},
            "body": json.dumps({"key_id": "dup_key", "scopes": ["verify:read"], "plan": "growth"}),
        },
        None,
    )
    managed_secret = json.loads(created_key["body"])["data"]["secret"]

    managed_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": managed_secret},
        },
        None,
    )
    bootstrap_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": bootstrap_secret},
        },
        None,
    )

    assert managed_response["statusCode"] == 200
    assert bootstrap_response["statusCode"] == 401
