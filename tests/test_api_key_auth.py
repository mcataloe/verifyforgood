from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace

from charity_status.auth import InMemoryUsageStore, StaticApiKeyStore, build_api_key_record
from charity_status.auth.errors import AuthenticationError, AuthorizationError, QuotaExceededError
from charity_status.auth.service import authenticate_api_key, enforce_quota_and_scope


def test_valid_key_authenticates():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="developer",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    assert principal.account_id == "acct_1"
    assert principal.plan.monthly_limit == 250


def test_invalid_key_rejected():
    _, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
    )
    try:
        authenticate_api_key({"x-api-key": "csk_dev_001.badsecret"}, StaticApiKeyStore([record]))
    except AuthenticationError as exc:
        assert "Invalid API key" in str(exc)
    else:
        assert False, "Expected AuthenticationError"


def test_revoked_key_rejected():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        revoked=True,
    )
    try:
        authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    except AuthenticationError as exc:
        assert "revoked" in str(exc)
    else:
        assert False, "Expected AuthenticationError"


def test_missing_key_rejected():
    try:
        authenticate_api_key({}, StaticApiKeyStore([]))
    except AuthenticationError as exc:
        assert "Missing API key" in str(exc)
    else:
        assert False, "Expected AuthenticationError"


def test_quota_exceeded():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="developer",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    store = InMemoryUsageStore()
    store._usage[("acct_1", "2099-01")] = 250
    try:
        # Force deterministic bucket for assertion by patching method inputs.
        # This uses service logic directly via helper contract by faking current month write after first pass.
        month_key, _, _ = enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", InMemoryUsageStore())
        store._usage[("acct_1", month_key)] = 250
        enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", store)
    except QuotaExceededError:
        pass
    else:
        assert False, "Expected QuotaExceededError"


def test_scoped_access_denied():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="developer",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    try:
        enforce_quota_and_scope(principal, "GET /v1/nonprofits/{ein}/federal-awards", InMemoryUsageStore())
    except AuthorizationError:
        pass
    else:
        assert False, "Expected AuthorizationError"


def test_lambda_query_enforces_auth_and_quota(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="developer",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", {"ein": ein, "name": "X", "state": "IL", "status": "1", "deductibility": "1", "subsection": "03", "ntee_cd": "P20", "tax_period": "202501", "filing_req_cd": "1", "asset_amt": "", "income_amt": "", "revenue_amt": ""}),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()

    ok = module.handler({"httpMethod": "GET", "resource": "/v1/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {"x-api-key": display_key}}, None)
    assert ok["statusCode"] == 200
    missing = module.handler({"httpMethod": "GET", "resource": "/v1/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {}}, None)
    assert missing["statusCode"] == 401


def test_entitlement_blocks_batch_for_developer(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:write"],
        plan_id="developer",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "headers": {"x-api-key": display_key},
        "body": json.dumps({"items": [{"ein": "123456789"}]}),
    }
    response = module.handler(event, None)
    assert response["statusCode"] == 403


def test_batch_metering_counts_items_for_team_plan(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="team_001",
        secret="test-secret",
        account_id="acct_2",
        workspace_id="ws_2",
        scopes=["verify:write"],
        plan_id="team",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", {"ein": ein, "name": "X", "state": "IL", "status": "1", "deductibility": "1", "subsection": "03", "ntee_cd": "P20", "tax_period": "202501", "filing_req_cd": "1", "asset_amt": "", "income_amt": "", "revenue_amt": ""}),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()
    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "headers": {"x-api-key": display_key},
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321"}]}),
    }
    response = module.handler(event, None)
    assert response["statusCode"] == 200
    assert sum(module.usage_store._usage.values()) == 2
