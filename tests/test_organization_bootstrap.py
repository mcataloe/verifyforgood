from __future__ import annotations

import importlib
import json
import sys

import pytest

from verification_platform.customer_accounts import (
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoUserRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    OrganizationCreateRequest,
    OrganizationDeleteRequest,
    OrganizationService,
    AuditEventType,
    AuditLogService,
    DynamoAuditLogRepository,
    UserRecord,
)
from verification_platform.identity_access import AuthService, BcryptPasswordHasher, HmacBearerTokenCodec, UserCreateRequest


def _seed_user_and_token(table: FakeIdentityDynamoTable):
    resource = FakeIdentityDynamoResource(table)
    auth_service = AuthService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
    )
    session = auth_service.register_user(
        UserCreateRequest(
            email="creator@example.com",
            password="top-secret-password",
            full_name="Creator User",
        )
    )
    return resource, session


def test_organization_creation_service_bootstraps_admin_membership():
    table = FakeIdentityDynamoTable()
    resource, session = _seed_user_and_token(table)
    service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
    )

    created = service.create_organization(
        creator_user_id=session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org"),
    )

    memberships = DynamoMembershipRepository(dynamodb_resource=resource).list_for_user(session.user.user_id)

    assert created.organization_name == "Verify For Good Org"
    assert created.slug == "verify-for-good-org"
    assert created.account_id == created.organization_id
    assert created.workspace_id == created.organization_id
    assert created.membership["role"] == "admin"
    assert memberships[0].organization_id == created.organization_id
    assert memberships[0].role.value == "admin"


def test_organization_creation_service_rejects_duplicate_slug():
    table = FakeIdentityDynamoTable()
    resource, session = _seed_user_and_token(table)
    service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
    )
    service.create_organization(
        creator_user_id=session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org", slug="verify-for-good-org"),
    )

    with pytest.raises(ValueError, match="Organization slug is already in use"):
        service.create_organization(
            creator_user_id=session.user.user_id,
            request=OrganizationCreateRequest(name="Another Org", slug="verify-for-good-org"),
        )


def test_organization_delete_service_soft_deletes_and_records_audit_event():
    table = FakeIdentityDynamoTable()
    resource, session = _seed_user_and_token(table)
    audits = DynamoAuditLogRepository(dynamodb_resource=resource)
    service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
        audit_log_service=AuditLogService(repository=audits),
    )
    created = service.create_organization(
        creator_user_id=session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org"),
    )

    deleted = service.delete_organization(
        actor_user_id=session.user.user_id,
        organization_id=created.organization_id,
        request=OrganizationDeleteRequest(slug=created.slug),
    )

    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    audit_items = audits.list_for_organization(created.organization_id)

    assert deleted.organization_id == created.organization_id
    assert organizations.get(created.organization_id) is None
    assert any(
        item.event_type is AuditEventType.ORGANIZATION_DELETION
        and item.metadata["slug"] == created.slug
        for item in audit_items
    )


def test_organization_delete_service_requires_matching_slug_confirmation():
    table = FakeIdentityDynamoTable()
    resource, session = _seed_user_and_token(table)
    service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
    )
    created = service.create_organization(
        creator_user_id=session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org"),
    )

    with pytest.raises(ValueError, match="slug confirmation"):
        service.delete_organization(
            actor_user_id=session.user.user_id,
            organization_id=created.organization_id,
            request=OrganizationDeleteRequest(slug="wrong-slug"),
        )


def test_post_organizations_bootstraps_admin_membership(monkeypatch):
    import verification_platform.customer_accounts.dynamodb_identity as identity_module

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
    module.portal_organization_service = None

    register_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "email": "creator@example.com",
                    "password": "top-secret-password",
                    "full_name": "Creator User",
                }
            ),
        },
        None,
    )
    register_payload = json.loads(register_response["body"])
    access_token = register_payload["data"]["access_token"]

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    payload = json.loads(response["body"])

    assert response["statusCode"] == 201
    assert payload["data"]["organization_name"] == "Verify For Good Org"
    assert payload["data"]["slug"] == "verify-for-good-org"
    assert payload["data"]["account_id"] == payload["data"]["organization_id"]
    assert payload["data"]["workspace_id"] == payload["data"]["organization_id"]
    assert payload["data"]["membership"]["role"] == "admin"


def test_delete_current_organization_soft_deletes_and_returns_success(monkeypatch):
    import verification_platform.customer_accounts.dynamodb_identity as identity_module

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
    module.portal_organization_service = None

    register_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "email": "creator@example.com",
                    "password": "top-secret-password",
                    "full_name": "Creator User",
                }
            ),
        },
        None,
    )
    register_payload = json.loads(register_response["body"])
    access_token = register_payload["data"]["access_token"]
    organization_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    organization_payload = json.loads(organization_response["body"])

    response = module.handler(
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
            "body": json.dumps({"slug": "verify-for-good-org"}),
        },
        None,
    )
    payload = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert payload["data"]["deleted"] is True
    assert payload["data"]["organization"]["slug"] == "verify-for-good-org"

