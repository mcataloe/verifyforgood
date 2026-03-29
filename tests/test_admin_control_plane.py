from __future__ import annotations

import importlib
import json
import re
import sys
from types import SimpleNamespace

from charity_status.auth import build_admin_key_record
from charity_status.control_plane import Account, ControlPlaneService, InMemoryControlPlaneStore, ManagedSubscription


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


def _body(response):
    return json.loads(response["body"])


def _data(response):
    return _body(response)["data"]


def _load_module(monkeypatch):
    admin_key, admin_record = build_admin_key_record("root", secret="admin-secret")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    monkeypatch.setenv("API_KEY_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", "[]")
    monkeypatch.setenv("ADMIN_KEY_RECORDS_JSON", json.dumps([admin_record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    return module, admin_key


def test_admin_routes_require_separate_admin_key(monkeypatch):
    module, _admin_key = _load_module(monkeypatch)

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {},
        },
        None,
    )

    assert response["statusCode"] == 401
    assert _body(response)["plan"] == "public"


def test_admin_account_crud_and_status_transitions(monkeypatch):
    module, admin_key = _load_module(monkeypatch)
    headers = {"x-admin-key": admin_key, "Content-Type": "application/json"}

    created = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": headers,
            "body": json.dumps({"name": "Acme Giving", "ein": "12-3456789"}),
        },
        None,
    )
    account = _data(created)
    account_id = account["id"]
    assert created["statusCode"] == 201
    assert _body(created)["plan"] == "admin"
    assert account["status"] == "active"
    assert account["subscription"] == "free"
    assert account["ein"] == "123456789"
    assert re.fullmatch(r"acct_[0-9a-f]{32}", account_id)

    listed = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert listed["statusCode"] == 200
    assert listed["headers"]["Content-Type"] == "application/json"
    assert len(_data(listed)["items"]) == 1
    assert _data(listed)["items"][0]["subscription"] == "free"

    fetched = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts/{accountId}",
            "path": f"/v1/admin/accounts/{account_id}",
            "pathParameters": {"accountId": account_id},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert _data(fetched)["id"] == account_id
    assert _data(fetched)["subscription"] == "free"

    updated = module.handler(
        {
            "httpMethod": "PATCH",
            "resource": "/v1/admin/accounts/{accountId}",
            "path": f"/v1/admin/accounts/{account_id}",
            "pathParameters": {"accountId": account_id},
            "headers": headers,
            "body": json.dumps({"name": "Acme Foundation"}),
        },
        None,
    )
    assert _data(updated)["name"] == "Acme Foundation"
    assert _data(updated)["subscription"] == "free"

    suspended = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/suspend",
            "path": f"/v1/admin/accounts/{account_id}/suspend",
            "pathParameters": {"accountId": account_id},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert _data(suspended)["status"] == "suspended"
    assert _data(suspended)["subscription"] == "free"

    activated = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/activate",
            "path": f"/v1/admin/accounts/{account_id}/activate",
            "pathParameters": {"accountId": account_id},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert _data(activated)["status"] == "active"
    assert _data(activated)["subscription"] == "free"


def test_admin_api_key_lifecycle_and_customer_auth(monkeypatch):
    module, admin_key = _load_module(monkeypatch)
    headers = {"x-admin-key": admin_key, "Content-Type": "application/json"}
    account = _data(
        module.handler(
            {
                "httpMethod": "POST",
                "resource": "/v1/admin/accounts",
                "path": "/v1/admin/accounts",
                "headers": headers,
                "body": json.dumps({"name": "Live Account", "ein": "123456789"}),
            },
            None,
        )
    )

    created = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/api-keys",
            "path": f"/v1/admin/accounts/{account['id']}/api-keys",
            "pathParameters": {"accountId": account["id"]},
            "headers": headers,
            "body": json.dumps({"scopes": ["verify:read"], "plan": "free"}),
        },
        None,
    )
    payload = _data(created)
    key_id = payload["api_key"]["key_id"]
    secret = payload["secret"]
    assert created["statusCode"] == 201
    assert secret.startswith("csk_")
    assert re.fullmatch(r"key_[0-9a-f]{32}", key_id)

    listed = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts/{accountId}/api-keys",
            "path": f"/v1/admin/accounts/{account['id']}/api-keys",
            "pathParameters": {"accountId": account["id"]},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    listed_item = _data(listed)["items"][0]
    assert "secret" not in listed_item
    assert listed_item["key_id"] == key_id

    customer_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": secret},
        },
        None,
    )
    assert customer_response["statusCode"] == 403

    rotated = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/api-keys/{keyId}/rotate",
            "path": f"/v1/admin/accounts/{account['id']}/api-keys/{key_id}/rotate",
            "pathParameters": {"accountId": account["id"], "keyId": key_id},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    rotated_secret = _data(rotated)["secret"]
    assert rotated_secret != secret

    old_key_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": secret},
        },
        None,
    )
    assert old_key_response["statusCode"] == 401

    deleted = module.handler(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/admin/accounts/{accountId}/api-keys/{keyId}",
            "path": f"/v1/admin/accounts/{account['id']}/api-keys/{key_id}",
            "pathParameters": {"accountId": account["id"], "keyId": key_id},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert _data(deleted)["status"] == "revoked"


def test_admin_oauth_client_lifecycle_and_token_issue(monkeypatch):
    module, admin_key = _load_module(monkeypatch)
    headers = {"x-admin-key": admin_key, "Content-Type": "application/json"}
    account = _data(
        module.handler(
            {
                "httpMethod": "POST",
                "resource": "/v1/admin/accounts",
                "path": "/v1/admin/accounts",
                "headers": headers,
                "body": json.dumps({"name": "OAuth Account", "ein": "123456789"}),
            },
            None,
        )
    )

    created = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/oauth-clients",
            "path": f"/v1/admin/accounts/{account['id']}/oauth-clients",
            "pathParameters": {"accountId": account["id"]},
            "headers": headers,
            "body": json.dumps({"scopes": ["oauth:token", "verify:read"], "plan": "growth"}),
        },
        None,
    )
    payload = _data(created)
    client_id = payload["oauth_client"]["client_id"]
    client_secret = payload["client_secret"]
    assert created["statusCode"] == 201
    assert re.fullmatch(r"client_[0-9a-f]{32}", client_id)

    listed = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts/{accountId}/oauth-clients",
            "path": f"/v1/admin/accounts/{account['id']}/oauth-clients",
            "pathParameters": {"accountId": account["id"]},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    listed_item = _data(listed)["items"][0]
    assert "client_secret" not in listed_item
    assert listed_item["client_id"] == client_id

    token_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/oauth/token",
            "path": "/v1/oauth/token",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"client_id": client_id, "client_secret": client_secret}),
        },
        None,
    )
    assert token_response["statusCode"] == 200
    assert _data(token_response)["access_token"].startswith("oct_")

    deleted = module.handler(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/admin/accounts/{accountId}/oauth-clients/{clientId}",
            "path": f"/v1/admin/accounts/{account['id']}/oauth-clients/{client_id}",
            "pathParameters": {"accountId": account["id"], "clientId": client_id},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert _data(deleted)["status"] == "revoked"


def test_control_plane_service_stores_only_hashed_secrets():
    service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = service.create_account({"name": "Hash Account", "ein": "123456789"})

    api_key_payload = service.create_api_key(account["id"], {})
    oauth_payload = service.create_oauth_client(account["id"], {})

    api_key_id = api_key_payload["api_key"]["key_id"]
    oauth_client_id = oauth_payload["oauth_client"]["client_id"]
    api_key_record = service.store.api_keys[api_key_id][1]
    oauth_record = service.store.oauth_clients[oauth_client_id][1]

    assert api_key_payload["secret"] != api_key_record.secret_hash
    assert oauth_payload["client_secret"] != oauth_record.client_secret_hash
    assert not hasattr(api_key_record, "secret")
    assert not hasattr(oauth_record, "client_secret")
    assert re.fullmatch(r"acct_[0-9a-f]{32}", account["id"])
    assert re.fullmatch(r"key_[0-9a-f]{32}", api_key_id)
    assert re.fullmatch(r"client_[0-9a-f]{32}", oauth_client_id)


def test_control_plane_service_requires_name_and_valid_ein():
    service = ControlPlaneService(store=InMemoryControlPlaneStore())

    try:
        service.create_account({"ein": "123456789"})
    except ValueError as exc:
        assert str(exc) == "name is required"
    else:
        assert False, "Expected name validation error"

    try:
        service.create_account({"name": "Missing EIN"})
    except ValueError as exc:
        assert str(exc) == "ein is required"
    else:
        assert False, "Expected EIN validation error"

    try:
        service.create_account({"name": "Bad EIN", "ein": "12-34"})
    except ValueError as exc:
        assert str(exc) == "ein must be a valid EIN"
    else:
        assert False, "Expected invalid EIN error"

    account = service.create_account({"name": "Normalized EIN", "ein": "12-3456789"})
    assert account["ein"] == "123456789"


def test_control_plane_service_rejects_ein_updates():
    service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = service.create_account({"name": "Immutable Account", "ein": "123456789"})

    try:
        service.update_account(account["id"], {"ein": "987654321"})
    except ValueError as exc:
        assert str(exc) == "ein cannot be updated"
    else:
        assert False, "Expected immutable EIN error"


def test_control_plane_service_returns_null_subscription_for_legacy_account_without_subscription():
    service = ControlPlaneService(store=InMemoryControlPlaneStore())
    service.store.put_account(
        Account(
            id="acct_legacy",
            name="Legacy Account",
            status="active",
            created_at="2026-03-18T00:00:00+00:00",
        )
    )

    account = service.get_account("acct_legacy")

    assert account["subscription"] is None


def test_control_plane_service_normalizes_account_subscription_aliases():
    service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = service.create_account({"name": "Alias Account", "ein": "123456789"})
    service.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="business",
            status="active",
            effective_from="2026-03-18T00:00:00+00:00",
        )
    )

    fetched = service.get_account(account["id"])

    assert fetched["subscription"] == "pro"


def test_create_routes_reject_caller_supplied_identifiers(monkeypatch):
    module, admin_key = _load_module(monkeypatch)
    headers = {"x-admin-key": admin_key, "Content-Type": "application/json"}

    account_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": headers,
            "body": json.dumps({"id": "acct_custom", "name": "Custom Account", "ein": "123456789"}),
        },
        None,
    )
    assert account_response["statusCode"] == 400
    assert "system-generated" in _body(account_response)["errors"][0]["message"]

    account = _data(
        module.handler(
            {
                "httpMethod": "POST",
                "resource": "/v1/admin/accounts",
                "path": "/v1/admin/accounts",
                "headers": headers,
                "body": json.dumps({"name": "Generated Account", "ein": "123456789"}),
            },
            None,
        )
    )

    api_key_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/api-keys",
            "path": f"/v1/admin/accounts/{account['id']}/api-keys",
            "pathParameters": {"accountId": account["id"]},
            "headers": headers,
            "body": json.dumps({"key_id": "key_custom", "scopes": ["verify:read"]}),
        },
        None,
    )
    assert api_key_response["statusCode"] == 400
    assert "system-generated" in _body(api_key_response)["errors"][0]["message"]

    oauth_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts/{accountId}/oauth-clients",
            "path": f"/v1/admin/accounts/{account['id']}/oauth-clients",
            "pathParameters": {"accountId": account["id"]},
            "headers": headers,
            "body": json.dumps({"client_id": "client_custom", "scopes": ["oauth:token", "verify:read"]}),
        },
        None,
    )
    assert oauth_response["statusCode"] == 400
    assert "system-generated" in _body(oauth_response)["errors"][0]["message"]


def test_admin_subscription_routes(monkeypatch):
    module, admin_key = _load_module(monkeypatch)
    headers = {"x-admin-key": admin_key, "Content-Type": "application/json"}
    account = _data(
        module.handler(
            {
                "httpMethod": "POST",
                "resource": "/v1/admin/accounts",
                "path": "/v1/admin/accounts",
                "headers": headers,
                "body": json.dumps({"name": "Subscription Account", "ein": "123456789"}),
            },
            None,
        )
    )

    fetched = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts/{accountId}/subscription",
            "path": f"/v1/admin/accounts/{account['id']}/subscription",
            "pathParameters": {"accountId": account["id"]},
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    assert fetched["statusCode"] == 200
    assert _data(fetched)["plan_code"] == "free"

    updated = module.handler(
        {
            "httpMethod": "PUT",
            "resource": "/v1/admin/accounts/{accountId}/subscription",
            "path": f"/v1/admin/accounts/{account['id']}/subscription",
            "pathParameters": {"accountId": account["id"]},
            "headers": headers,
            "body": json.dumps(
                {
                    "plan_code": "pro",
                    "status": "active",
                    "effective_from": "2026-03-18T00:00:00+00:00",
                }
            ),
        },
        None,
    )
    assert updated["statusCode"] == 200
    payload = _data(updated)
    assert payload["plan_code"] == "pro"
    assert payload["status"] == "active"


def test_admin_account_create_requires_valid_ein_and_patch_rejects_it(monkeypatch):
    module, admin_key = _load_module(monkeypatch)
    headers = {"x-admin-key": admin_key, "Content-Type": "application/json"}

    missing_ein = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": headers,
            "body": json.dumps({"name": "Missing EIN"}),
        },
        None,
    )
    assert missing_ein["statusCode"] == 400
    assert "ein is required" in _body(missing_ein)["errors"][0]["message"]

    invalid_ein = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": headers,
            "body": json.dumps({"name": "Bad EIN", "ein": "12-34"}),
        },
        None,
    )
    assert invalid_ein["statusCode"] == 400
    assert "valid EIN" in _body(invalid_ein)["errors"][0]["message"]

    created = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": headers,
            "body": json.dumps({"name": "Immutable EIN", "ein": "123456789"}),
        },
        None,
    )
    account_id = _data(created)["id"]

    patched = module.handler(
        {
            "httpMethod": "PATCH",
            "resource": "/v1/admin/accounts/{accountId}",
            "path": f"/v1/admin/accounts/{account_id}",
            "pathParameters": {"accountId": account_id},
            "headers": headers,
            "body": json.dumps({"ein": "987654321"}),
        },
        None,
    )
    assert patched["statusCode"] == 400
    assert "cannot be updated" in _body(patched)["errors"][0]["message"]
