from __future__ import annotations

import importlib
import json
import sys

from verification.backend.shared.customer_accounts import (
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoUserRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationContextService,
    OrganizationRecord,
    UserRecord,
)


def _load_module_with_identity_store(monkeypatch):
    import verification.backend.shared.customer_accounts.dynamodb_identity as identity_module

    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    monkeypatch.setenv("IDENTITY_TABLE_NAME", "identity")
    monkeypatch.setenv("PORTAL_AUTH_TOKEN_SECRET", "test-secret")
    monkeypatch.setattr(identity_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("verification.backend.customer.api.runtime", None)
    module = importlib.import_module("verification.backend.customer.api.runtime")
    module.portal_auth_service = None
    module.portal_organization_service = None
    module.portal_organization_context_service = None
    return module


def _response_body(response):
    return json.loads(response["body"])


def test_register_flow_returns_user_and_access_token(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)

    response = module.handle_api_event(
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

    first = module.handle_api_event(event, None)
    duplicate = module.handle_api_event(event, None)
    payload = _response_body(duplicate)

    assert first["statusCode"] == 201
    assert duplicate["statusCode"] == 400
    assert payload["errors"][0]["message"] == "Email is already registered"


def test_login_validation_requires_password(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)

    response = module.handle_api_event(
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
    register_response = module.handle_api_event(
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

    response = module.handle_api_event(
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


def test_auth_me_returns_current_user_and_active_organization_context(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)
    register_response = module.handle_api_event(
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
    organization_response = module.handle_api_event(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    organization_payload = _response_body(organization_response)

    response = module.handle_api_event(
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
    assert payload["data"]["organization_context"]["organization_name"] == "Verify For Good Org"
    assert len(payload["data"]["available_organizations"]) == 1
    assert (
        payload["data"]["available_organizations"][0]["organization_name"]
        == "Verify For Good Org"
    )
    assert (
        payload["data"]["organization_context"]["organization_id"]
        == organization_payload["data"]["organization_id"]
    )
    assert payload["data"]["organization_context"]["membership"]["role"] == "admin"


def test_auth_me_excludes_soft_deleted_organizations(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)
    register_response = module.handle_api_event(
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
    organization_response = module.handle_api_event(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    organization_payload = _response_body(organization_response)
    delete_response = module.handle_api_event(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/organizations/current",
            "path": "/v1/organizations/current",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Portal-Account-Id": organization_payload["data"]["account_id"],
                "X-Portal-Workspace-Id": organization_payload["data"]["workspace_id"],
            },
            "body": json.dumps({"slug": organization_payload["data"]["slug"]}),
        },
        None,
    )

    response = module.handle_api_event(
        {
            "httpMethod": "GET",
            "resource": "/v1/auth/me",
            "path": "/v1/auth/me",
            "headers": {"Authorization": f"Bearer {access_token}"},
        },
        None,
    )
    payload = _response_body(response)

    assert delete_response["statusCode"] == 200
    assert response["statusCode"] == 200
    assert payload["data"]["available_organizations"] == []
    assert payload["data"]["organization_context"] is None


def test_auth_me_returns_null_organization_context_without_membership(monkeypatch):
    module = _load_module_with_identity_store(monkeypatch)
    register_response = module.handle_api_event(
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

    response = module.handle_api_event(
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
    assert payload["data"]["available_organizations"] == []
    assert payload["data"]["organization_context"] is None


def test_organization_context_service_prefers_latest_active_membership():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)

    users.create(
        UserRecord(
            user_id="user_portal_person",
            email="person@example.com",
            normalized_email="person@example.com",
            full_name="Portal Person",
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_older",
            name="Older Org",
            slug="older-org",
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_newer",
            name="Newer Org",
            slug="newer-org",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )
    memberships.create(
        MembershipRecord(
            organization_id="org_older",
            user_id="user_portal_person",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    memberships.create(
        MembershipRecord(
            organization_id="org_newer",
            user_id="user_portal_person",
            role=MembershipRole.USER,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-27T00:00:00+00:00",
        )
    )

    resolved = OrganizationContextService(
        organizations=organizations,
        memberships=memberships,
    ).resolve_for_user(user_id="user_portal_person")

    assert resolved is not None
    assert resolved.organization_id == "org_newer"
    assert resolved.organization_name == "Newer Org"
    assert resolved.membership["role"] == "user"


def test_organization_context_service_lists_active_memberships_in_priority_order():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)

    users.create(
        UserRecord(
            user_id="user_portal_person",
            email="person@example.com",
            normalized_email="person@example.com",
            full_name="Portal Person",
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_alpha",
            name="Alpha Org",
            slug="alpha-org",
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_beta",
            name="Beta Org",
            slug="beta-org",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )
    memberships.create(
        MembershipRecord(
            organization_id="org_alpha",
            user_id="user_portal_person",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    memberships.create(
        MembershipRecord(
            organization_id="org_beta",
            user_id="user_portal_person",
            role=MembershipRole.USER,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-27T00:00:00+00:00",
        )
    )

    resolved = OrganizationContextService(
        organizations=organizations,
        memberships=memberships,
    ).list_for_user(user_id="user_portal_person")

    assert [item.organization_id for item in resolved] == ["org_beta", "org_alpha"]
    assert resolved[0].membership["role"] == "user"
    assert resolved[1].membership["role"] == "admin"


def test_organization_context_service_ignores_soft_deleted_organizations():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)

    users.create(
        UserRecord(
            user_id="user_portal_person",
            email="person@example.com",
            normalized_email="person@example.com",
            full_name="Portal Person",
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_alpha",
            name="Alpha Org",
            slug="alpha-org",
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    memberships.create(
        MembershipRecord(
            organization_id="org_alpha",
            user_id="user_portal_person",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
        )
    )
    organizations.soft_delete(
        "org_alpha",
        deleted_at="2026-03-27T00:00:00+00:00",
        deleted_by_user_id="user_portal_person",
    )

    resolved = OrganizationContextService(
        organizations=organizations,
        memberships=memberships,
    ).list_for_user(user_id="user_portal_person")

    assert resolved == []


