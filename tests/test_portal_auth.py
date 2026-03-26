from __future__ import annotations

import importlib
import json
import sys

from charity_status_platform.customer_accounts import FakeIdentityDynamoResource, FakeIdentityDynamoTable


def _load_module_with_identity_store(monkeypatch):
    import charity_status_platform.customer_accounts.dynamodb_identity as identity_module

    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    monkeypatch.setenv("IDENTITY_TABLE_NAME", "identity")
    monkeypatch.setenv("PORTAL_AUTH_TOKEN_SECRET", "test-secret")
    monkeypatch.setattr(identity_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.portal_auth_service = None
    return module


def _response_body(response):
    return json.loads(response["body"])


def test_register_flow_returns_user_and_access_token(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "email": "person@example.com",
                    "password": "top-secret-password",
                    "full_name": "Portal Person",
                }
            ),
        },
        None,
    )

    payload = _response_body(response)

    assert response["statusCode"] == 201
    assert payload["data"]["user"]["email"] == "person@example.com"
    assert payload["data"]["user"]["full_name"] == "Portal Person"
    assert payload["data"]["access_token"]
    assert payload["data"]["token_type"] == "Bearer"


def test_duplicate_email_rejection_returns_400(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)
    event = {
        "httpMethod": "POST",
        "resource": "/v1/auth/register",
        "path": "/v1/auth/register",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"email": "person@example.com", "password": "top-secret-password"}),
    }

    first = module.handler(event, None)
    duplicate = module.handler(event, None)
    payload = _response_body(duplicate)

    assert first["statusCode"] == 201
    assert duplicate["statusCode"] == 400
    assert payload["errors"][0]["message"] == "Email is already registered"


def test_login_validation_requires_password(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/login",
            "path": "/v1/auth/login",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "person@example.com"}),
        },
        None,
    )

    payload = _response_body(response)

    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "password must be at least 8 characters"


def test_invalid_password_returns_401(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)
    register_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "person@example.com", "password": "top-secret-password"}),
        },
        None,
    )
    assert register_response["statusCode"] == 201

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/login",
            "path": "/v1/auth/login",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "person@example.com", "password": "wrong-pass"}),
        },
        None,
    )

    payload = _response_body(response)

    assert response["statusCode"] == 401
    assert payload["errors"][0]["message"] == "Invalid email or password"


def test_auth_me_returns_current_user(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)
    register_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "email": "person@example.com",
                    "password": "top-secret-password",
                    "full_name": "Portal Person",
                }
            ),
        },
        None,
    )
    register_payload = _response_body(register_response)
    access_token = register_payload["data"]["access_token"]

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/auth/me",
            "path": "/v1/auth/me",
            "headers": {"Authorization": f"Bearer {access_token}"},
        },
        None,
    )

    payload = _response_body(response)

    assert response["statusCode"] == 200
    assert payload["data"]["user"]["email"] == "person@example.com"
    assert payload["data"]["user"]["full_name"] == "Portal Person"
