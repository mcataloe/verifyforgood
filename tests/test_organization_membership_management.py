from __future__ import annotations

import importlib
import json
import sys

from charity_status.auth import InMemoryUsageStore
from charity_status.platform.auth import ApiKeyQuotaMeteringHook
from charity_status_platform.billing_usage import monthly_period_for
from charity_status_platform.customer_accounts import (
    DynamoOrganizationRepository,
    DynamoInvitationRepository,
    DynamoUsageRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    InvitationRecord,
    InvitationStatus,
    MembershipRole,
)


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
    module.portal_organization_service = None
    module.portal_membership_service = None
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
            "body": json.dumps(
                {
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                }
            ),
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


def _invite_member(module, *, access_token: str, organization_id: str, email: str, role: str = "user"):
    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/invitations",
            "path": "/v1/organizations/current/invitations",
            "headers": _current_org_headers(access_token, organization_id),
            "body": json.dumps({"email": email, "role": role}),
        },
        None,
    )
    return response, _response_body(response)


def _accept_invitation(module, *, access_token: str, token: str):
    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/invitations/accept",
            "path": "/v1/invitations/accept",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            "body": json.dumps({"token": token}),
        },
        None,
    )
    return response, _response_body(response)


def test_get_current_members_lists_bootstrap_admin(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, creator_user = _register_user(module, email="creator@example.com", full_name="Creator User")
    _, organization = _create_organization(module, access_token=creator_token)

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organizations/current/members",
            "path": "/v1/organizations/current/members",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 200
    assert len(payload["data"]["items"]) == 1
    assert payload["data"]["items"][0]["user_id"] == creator_user["user_id"]
    assert payload["data"]["items"][0]["role"] == "admin"
    assert payload["data"]["items"][0]["email"] == "creator@example.com"


def test_non_admin_cannot_modify_membership_state(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="member@example.com",
    )
    assert invite_response["statusCode"] == 201
    _, member_token, member_user = _register_user(module, email="member@example.com")
    accept_response, _accept_payload = _accept_invitation(
        module,
        access_token=member_token,
        token=invite_payload["data"]["token"],
    )
    assert accept_response["statusCode"] == 200

    response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/invitations",
            "path": "/v1/organizations/current/invitations",
            "headers": _current_org_headers(member_token, organization["organization_id"]),
            "body": json.dumps({"email": "another@example.com", "role": "user"}),
        },
        None,
    )
    payload = _response_body(response)

    assert member_user["email"] == "member@example.com"
    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "Only organization admins may modify membership state"


def test_invitation_token_lookup_and_acceptance_returns_membership_context(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token, name="Team Verify")
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="invitee@example.com",
        role="user",
    )
    assert invite_response["statusCode"] == 201
    assert invite_payload["data"]["token"].startswith("invtok_")
    _, invitee_token, invitee_user = _register_user(module, email="invitee@example.com")

    response, payload = _accept_invitation(
        module,
        access_token=invitee_token,
        token=invite_payload["data"]["token"],
    )

    assert response["statusCode"] == 200
    assert payload["data"]["invitation"]["status"] == "accepted"
    assert payload["data"]["membership"]["user_id"] == invitee_user["user_id"]
    assert payload["data"]["membership"]["role"] == "user"
    assert payload["data"]["membership"]["status"] == "active"
    assert payload["data"]["organization"]["organization_id"] == organization["organization_id"]
    assert payload["data"]["organization"]["organization_name"] == "Team Verify"


def test_invitation_acceptance_rejects_email_mismatch(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="invitee@example.com",
    )
    assert invite_response["statusCode"] == 201
    _, other_token, _other_user = _register_user(module, email="other@example.com")

    response, payload = _accept_invitation(
        module,
        access_token=other_token,
        token=invite_payload["data"]["token"],
    )

    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "Invitation email does not match the authenticated user"


def test_duplicate_membership_prevention_rejects_inviting_existing_active_member(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="member@example.com",
    )
    assert invite_response["statusCode"] == 201
    _, member_token, _member_user = _register_user(module, email="member@example.com")
    accept_response, _accept_payload = _accept_invitation(
        module,
        access_token=member_token,
        token=invite_payload["data"]["token"],
    )
    assert accept_response["statusCode"] == 200

    response, payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="member@example.com",
    )

    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "User is already an active member of this organization"


def test_patch_member_updates_role(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="member@example.com",
    )
    assert invite_response["statusCode"] == 201
    _, member_token, member_user = _register_user(module, email="member@example.com")
    accept_response, _accept_payload = _accept_invitation(
        module,
        access_token=member_token,
        token=invite_payload["data"]["token"],
    )
    assert accept_response["statusCode"] == 200

    response = module.handler(
        {
            "httpMethod": "PATCH",
            "resource": "/v1/organizations/current/members/{memberId}",
            "path": f"/v1/organizations/current/members/{member_user['user_id']}",
            "pathParameters": {"memberId": member_user["user_id"]},
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
            "body": json.dumps({"role": "admin"}),
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 200
    assert payload["data"]["user_id"] == member_user["user_id"]
    assert payload["data"]["role"] == "admin"
    assert payload["data"]["status"] == "active"


def test_delete_member_removes_membership(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="member@example.com",
    )
    assert invite_response["statusCode"] == 201
    _, member_token, member_user = _register_user(module, email="member@example.com")
    accept_response, _accept_payload = _accept_invitation(
        module,
        access_token=member_token,
        token=invite_payload["data"]["token"],
    )
    assert accept_response["statusCode"] == 200

    delete_response = module.handler(
        {
            "httpMethod": "DELETE",
            "resource": "/v1/organizations/current/members/{memberId}",
            "path": f"/v1/organizations/current/members/{member_user['user_id']}",
            "pathParameters": {"memberId": member_user["user_id"]},
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    delete_payload = _response_body(delete_response)
    list_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organizations/current/members",
            "path": "/v1/organizations/current/members",
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    list_payload = _response_body(list_response)

    assert delete_response["statusCode"] == 200
    assert delete_payload["data"]["removed_member_id"] == member_user["user_id"]
    assert [item["user_id"] for item in list_payload["data"]["items"]] == [organization["membership"]["user_id"]]


def test_current_organization_headers_are_required(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    assert organization["organization_id"]

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organizations/current/members",
            "path": "/v1/organizations/current/members",
            "headers": {"Authorization": f"Bearer {creator_token}"},
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "Current organization headers are required"


def test_accept_invitation_rejects_duplicate_existing_membership(monkeypatch):
    module, resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    _, member_token, member_user = _register_user(module, email="member@example.com")
    invite_response, invite_payload = _invite_member(
        module,
        access_token=creator_token,
        organization_id=organization["organization_id"],
        email="member@example.com",
    )
    assert invite_response["statusCode"] == 201
    first_accept_response, _first_accept_payload = _accept_invitation(
        module,
        access_token=member_token,
        token=invite_payload["data"]["token"],
    )
    assert first_accept_response["statusCode"] == 200

    repo = DynamoInvitationRepository(dynamodb_resource=resource)
    invitation = InvitationRecord(
        invitation_id="invite_duplicate",
        organization_id=organization["organization_id"],
        email="member@example.com",
        normalized_email="member@example.com",
        token="duplicate-membership-token",
        role=MembershipRole.USER,
        status=InvitationStatus.PENDING,
        invited_by_user_id=organization["membership"]["user_id"],
        created_at="2026-03-26T00:00:00+00:00",
        expires_at="2099-03-26T00:00:00+00:00",
    )
    repo.create(invitation)

    response, payload = _accept_invitation(
        module,
        access_token=member_token,
        token="duplicate-membership-token",
    )

    assert member_user["email"] == "member@example.com"
    assert response["statusCode"] == 400
    assert payload["errors"][0]["message"] == "User is already a member of this organization"


def test_portal_session_can_query_nonprofit_when_membership_is_active(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    module.athena_client = type(
        "_Client",
        (),
        {
            "lookup_nonprofit": staticmethod(
                lambda ein, subsection=None: (
                    "qid-1",
                    {
                        "ein": ein,
                        "name": "Tenant Query Org",
                        "state": "IL",
                        "status": "1",
                        "deductibility": "1",
                        "subsection": subsection or "03",
                        "ntee_cd": "P20",
                        "tax_period": "202501",
                        "filing_req_cd": "1",
                        "asset_amt": "",
                        "income_amt": "",
                        "revenue_amt": "",
                    },
                )
            ),
            "lookup_form990_enrichment": staticmethod(lambda ein: ({}, {}, {}, {})),
            "lookup_peer_benchmark": staticmethod(lambda group: {"count": 0, "metrics": {}}),
            "list_form990_filings": staticmethod(lambda ein, limit=10: ("qid-f", [])),
            "search_nonprofits": staticmethod(lambda **kwargs: ("qid-s", [])),
        },
    )()
    module.enrichment_service = type(
        "_Enrichment",
        (),
        {
            "enrich": staticmethod(
                lambda **kwargs: type(
                    "_Payload",
                    (),
                    {"to_dict": staticmethod(lambda: {"providers": [], "failures": []})},
                )()
            )
        },
    )()
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    usage_service = module.UsageService(
        organizations=DynamoOrganizationRepository(dynamodb_resource=_resource),
        usage=DynamoUsageRepository(dynamodb_resource=_resource),
    )
    module.quota_metering_hook = ApiKeyQuotaMeteringHook(
        InMemoryUsageStore(),
        organization_usage_tracker=module._PortalOrganizationUsageTracker(usage_service),
    )

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": _current_org_headers(creator_token, organization["organization_id"]),
        },
        None,
    )
    payload = _response_body(response)
    usage = DynamoUsageRepository(dynamodb_resource=_resource).list_for_period(organization["organization_id"], monthly_period_for())

    assert response["statusCode"] == 200
    assert payload["data"]["organization"]["name"] == "Tenant Query Org"
    assert {item.metric_type.value: item.request_count for item in usage} == {
        "api_requests": 1,
        "nonprofit_lookups": 1,
        "nonprofit_lookup_requests": 1,
    }


def test_portal_session_nonprofit_query_requires_current_org_headers(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _create_organization(module, access_token=creator_token)

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"Authorization": f"Bearer {creator_token}"},
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 403
    assert payload["errors"][0]["message"] == "Current organization headers are required"


def test_portal_session_nonprofit_query_rejects_non_member(monkeypatch):
    module, _resource = _load_module_with_identity_store(monkeypatch)
    _, creator_token, _creator = _register_user(module, email="creator@example.com")
    _, organization = _create_organization(module, access_token=creator_token)
    _, outsider_token, _outsider = _register_user(module, email="outsider@example.com")

    response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": _current_org_headers(outsider_token, organization["organization_id"]),
        },
        None,
    )
    payload = _response_body(response)

    assert response["statusCode"] == 403
    assert payload["errors"][0]["message"] == "Active membership is required for nonprofit queries"
