from __future__ import annotations

import importlib
import json
import sys

from charity_status_platform.billing_usage import monthly_period_for
from charity_status_platform.customer_accounts import (
    DynamoApiKeyRepository,
    DynamoUsageRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
)


def _load_module_with_identity_store(monkeypatch, *, api_auth_enabled: bool = False):
    import charity_status_platform.customer_accounts.dynamodb_identity as identity_module

    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    monkeypatch.setenv("API_AUTH_ENABLED", "true" if api_auth_enabled else "false")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    monkeypatch.setenv("IDENTITY_TABLE_NAME", "identity")
    monkeypatch.setenv("PORTAL_AUTH_TOKEN_SECRET", "test-secret")
    monkeypatch.setattr(identity_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.portal_auth_service = None
    module.portal_organization_service = None
    module.portal_membership_service = None
    module.portal_api_key_service = None
    module.auth_context_provider = None
    module.quota_metering_hook = None
    return module, resource


def _response_body(response):
    return json.loads(response["body"])


def _register_user(module, *, email: str, password: str = "top-secret-password", full_name: str | None = None):
    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": email, "password": password, "full_name": full_name}),
        },
        None,
    )
    payload = _response_body(response)
    return response, payload["data"]["access_token"], payload["data"]["user"]


def _create_organization(module, *, access_token: str, name: str = "Verify For Good Org", slug: str | None = None):
    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            "body": json.dumps({"name": name, "slug": slug}),
        },
        None,
    )
    payload = _response_body(response)
    return response, payload["data"]


def _current_org_headers(access_token: str, organization_id: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-Portal-Account-Id": organization_id,
        "X-Portal-Workspace-Id": organization_id,
    }


def test_admin_can_create_list_and_revoke_org_api_keys(monkeypatch):
    module, resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)

    create_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
            "body": json.dumps({"display_name": "Portal Automation"}),
        },
        None,
    )
    create_payload = _response_body(create_response)
    key_id = create_payload["data"]["api_key"]["key_id"]

    listed_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    listed_payload = _response_body(listed_response)

    revoked_response = module.handler(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/organizations/current/api-keys/{keyId}",
            "path": f"/v1/organizations/current/api-keys/{key_id}",
            "pathParameters": {"keyId": key_id},
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    revoked_payload = _response_body(revoked_response)

    persisted = DynamoApiKeyRepository(dynamodb_resource=resource).get_by_key_id(key_id)

    assert create_response["statusCode"] == 201
    assert create_payload["data"]["secret"].startswith(f"csk_{key_id}.")
    assert listed_payload["data"]["items"][0]["display_name"] == "Portal Automation"
    assert "secret" not in listed_payload["data"]["items"][0]
    assert revoked_response["statusCode"] == 200
    assert revoked_payload["data"]["status"] == "revoked"
    assert persisted is not None
    assert persisted.hashed_key_value != create_payload["data"]["secret"]
    assert persisted.status.value == "revoked"


def test_non_admin_cannot_manage_org_api_keys(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)

    invite_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/invitations",
            "path": "/v1/organizations/current/invitations",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
            "body": json.dumps({"email": "member@example.com", "role": "user"}),
        },
        None,
    )
    invite_payload = _response_body(invite_response)
    _, member_token, _member_user = _register_user(module, email="member@example.com")
    accept_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/invitations/accept",
            "path": "/v1/invitations/accept",
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {member_token}"},
            "body": json.dumps({"token": invite_payload["data"]["token"]}),
        },
        None,
    )
    assert accept_response["statusCode"] == 200

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": _current_org_headers(member_token, organization["organization_id"]),
            "body": json.dumps({"display_name": "No Access"}),
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "Only organization admins may manage API keys"


def test_org_api_key_authenticates_product_route_and_updates_last_used(monkeypatch):
    module, resource = _load_module_with_identity_store(monkeypatch, api_auth_enabled=True)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)

    create_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
            "body": json.dumps({"display_name": "CLI Key"}),
        },
        None,
    )
    create_payload = _response_body(create_response)
    api_key = create_payload["data"]["secret"]
    key_id = create_payload["data"]["api_key"]["key_id"]

    auth_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/12-34A6789",
            "pathParameters": {"ein": "12-34A6789"},
            "headers": {"x-api-key": api_key},
        },
        None,
    )
    auth_payload = _response_body(auth_response)
    persisted = DynamoApiKeyRepository(dynamodb_resource=resource).get_by_key_id(key_id)
    usage = DynamoUsageRepository(dynamodb_resource=resource).list_for_period(organization["organization_id"], monthly_period_for())

    assert auth_response["statusCode"] == 400
    assert "invalid characters" in auth_payload["errors"][0]["message"]
    assert persisted is not None
    assert persisted.last_used_at is not None
    assert {item.metric_type.value: item.request_count for item in usage} == {}


def test_org_api_key_cannot_access_org_api_key_management_routes(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch, api_auth_enabled=True)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)

    create_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
            "body": json.dumps({"display_name": "CLI Key"}),
        },
        None,
    )
    api_key = _response_body(create_response)["data"]["secret"]

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": {"x-api-key": api_key},
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 403
    assert payload["errors"][0]["message"] == "Portal session authentication is required for this organization route"


def test_revoked_org_api_key_is_rejected_for_product_auth(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch, api_auth_enabled=True)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)

    create_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
            "body": json.dumps({"display_name": "Revoked Key"}),
        },
        None,
    )
    create_payload = _response_body(create_response)
    api_key = create_payload["data"]["secret"]
    key_id = create_payload["data"]["api_key"]["key_id"]

    revoke_response = module.handler(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/organizations/current/api-keys/{keyId}",
            "path": f"/v1/organizations/current/api-keys/{key_id}",
            "pathParameters": {"keyId": key_id},
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    assert revoke_response["statusCode"] == 200

    auth_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": api_key},
        },
        None,
    )
    auth_payload = _response_body(auth_response)

    assert auth_response["statusCode"] == 401
    assert auth_payload["errors"][0]["message"] == "API key revoked"
