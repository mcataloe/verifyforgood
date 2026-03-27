from __future__ import annotations

import importlib
import json
import sys

import pytest

from charity_status_platform.customer_accounts import (
    DynamoInvitationRepository,
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoUserRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    InvitationCreateRequest,
    MemberUpdateRequest,
    MembershipManagementService,
    OrganizationCreateRequest,
    OrganizationService,
)
from charity_status_platform.identity_access import AuthService, BcryptPasswordHasher, HmacBearerTokenCodec, UserCreateRequest


def _seed_bootstrapped_org(table: FakeIdentityDynamoTable, *, admin_email: str = "admin@example.com"):
    resource = FakeIdentityDynamoResource(table)
    auth_service = AuthService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
    )
    admin_session = auth_service.register_user(
        UserCreateRequest(
            email=admin_email,
            password="top-secret-password",
            full_name="Admin User",
        )
    )
    organization_service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
    )
    organization = organization_service.create_organization(
        creator_user_id=admin_session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org"),
    )
    membership_service = MembershipManagementService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
        invitations=DynamoInvitationRepository(dynamodb_resource=resource),
    )
    return resource, auth_service, admin_session, organization, membership_service


def test_invitation_token_lookup_and_acceptance_round_trip():
    table = FakeIdentityDynamoTable()
    resource, auth_service, admin_session, organization, membership_service = _seed_bootstrapped_org(table)
    invited_session = auth_service.register_user(
        UserCreateRequest(
            email="invitee@example.com",
            password="top-secret-password",
            full_name="Invited User",
        )
    )

    invitation = membership_service.invite_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        request=InvitationCreateRequest(email="invitee@example.com", role="user"),
    )
    accepted = membership_service.accept_invitation(
        user_id=invited_session.user.user_id,
        request=type("Accept", (), {"token": invitation.token})(),
    )

    lookup = DynamoInvitationRepository(dynamodb_resource=resource).get_by_token(invitation.token)
    membership = DynamoMembershipRepository(dynamodb_resource=resource).get(
        organization.organization_id,
        invited_session.user.user_id,
    )

    assert invitation.status == "pending"
    assert lookup is not None
    assert accepted["invitation"]["status"] == "accepted"
    assert accepted["membership"]["role"] == "user"
    assert membership is not None
    assert membership.role.value == "user"


def test_admin_only_modification_rules():
    table = FakeIdentityDynamoTable()
    resource, auth_service, admin_session, organization, membership_service = _seed_bootstrapped_org(table)
    member_session = auth_service.register_user(
        UserCreateRequest(
            email="member@example.com",
            password="top-secret-password",
            full_name="Member User",
        )
    )
    membership_service.invite_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        request=InvitationCreateRequest(email="member@example.com", role="user"),
    )
    first_invitation = None
    for item in DynamoInvitationRepository(dynamodb_resource=resource)._table._items.values():  # type: ignore[attr-defined]
        if item.get("type") == "INVITATION":
            first_invitation = item.get("token")
            break
    membership_service.accept_invitation(
        user_id=member_session.user.user_id,
        request=type("Accept", (), {"token": first_invitation})(),
    )

    with pytest.raises(ValueError, match="Only organization admins may modify membership state"):
        membership_service.update_member(
            organization_id=organization.organization_id,
            actor_user_id=member_session.user.user_id,
            member_user_id=admin_session.user.user_id,
            request=MemberUpdateRequest(role="user"),
        )


def test_role_update_behavior_and_duplicate_membership_prevention():
    table = FakeIdentityDynamoTable()
    resource, auth_service, admin_session, organization, membership_service = _seed_bootstrapped_org(table)
    member_session = auth_service.register_user(
        UserCreateRequest(
            email="member@example.com",
            password="top-secret-password",
            full_name="Member User",
        )
    )
    invitation = membership_service.invite_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        request=InvitationCreateRequest(email="member@example.com", role="user"),
    )
    membership_service.accept_invitation(
        user_id=member_session.user.user_id,
        request=type("Accept", (), {"token": invitation.token})(),
    )

    updated = membership_service.update_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        member_user_id=member_session.user.user_id,
        request=MemberUpdateRequest(role="admin"),
    )

    assert updated.role == "admin"
    with pytest.raises(ValueError, match="User is already an active member of this organization"):
        membership_service.invite_member(
            organization_id=organization.organization_id,
            actor_user_id=admin_session.user.user_id,
            request=InvitationCreateRequest(email="member@example.com", role="user"),
        )


def test_post_membership_routes_and_accept_endpoint(monkeypatch):
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
    module.portal_organization_service = None
    module.portal_membership_service = None

    register_admin = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "admin@example.com", "password": "top-secret-password", "full_name": "Admin User"}),
        },
        None,
    )
    admin_token = json.loads(register_admin["body"])["data"]["access_token"]
    create_org = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"},
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    org_payload = json.loads(create_org["body"])["data"]

    invite_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/invitations",
            "path": "/v1/organizations/current/invitations",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}",
                "X-Portal-Account-Id": org_payload["account_id"],
                "X-Portal-Workspace-Id": org_payload["workspace_id"],
            },
            "body": json.dumps({"email": "invitee@example.com", "role": "user"}),
        },
        None,
    )
    invite_payload = json.loads(invite_response["body"])["data"]
    assert invite_response["statusCode"] == 201

    register_invited = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "invitee@example.com", "password": "top-secret-password", "full_name": "Invitee User"}),
        },
        None,
    )
    invited_token = json.loads(register_invited["body"])["data"]["access_token"]

    accept_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/invitations/accept",
            "path": "/v1/invitations/accept",
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {invited_token}"},
            "body": json.dumps({"token": invite_payload["token"]}),
        },
        None,
    )
    accept_payload = json.loads(accept_response["body"])["data"]
    assert accept_response["statusCode"] == 200
    assert accept_payload["membership"]["status"] == "active"

    list_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organizations/current/members",
            "path": "/v1/organizations/current/members",
            "headers": {
                "Authorization": f"Bearer {admin_token}",
                "X-Portal-Account-Id": org_payload["account_id"],
                "X-Portal-Workspace-Id": org_payload["workspace_id"],
            },
        },
        None,
    )
    list_payload = json.loads(list_response["body"])["data"]
    assert list_response["statusCode"] == 200
    assert len(list_payload["items"]) == 2

    patch_response = module.handler(
        {
            "httpMethod": "PATCH",
            "resource": "/v1/organizations/current/members/{memberId}",
            "path": f"/v1/organizations/current/members/{accept_payload['membership']['user_id']}",
            "pathParameters": {"memberId": accept_payload["membership"]["user_id"]},
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_token}",
                "X-Portal-Account-Id": org_payload["account_id"],
                "X-Portal-Workspace-Id": org_payload["workspace_id"],
            },
            "body": json.dumps({"role": "admin"}),
        },
        None,
    )
    assert patch_response["statusCode"] == 200
    assert json.loads(patch_response["body"])["data"]["role"] == "admin"

    delete_response = module.handler(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/organizations/current/members/{memberId}",
            "path": f"/v1/organizations/current/members/{accept_payload['membership']['user_id']}",
            "pathParameters": {"memberId": accept_payload["membership"]["user_id"]},
            "headers": {
                "Authorization": f"Bearer {admin_token}",
                "X-Portal-Account-Id": org_payload["account_id"],
                "X-Portal-Workspace-Id": org_payload["workspace_id"],
            },
        },
        None,
    )
    assert delete_response["statusCode"] == 200
