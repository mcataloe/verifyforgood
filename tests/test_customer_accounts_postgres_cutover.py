from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from sqlalchemy import select

from charity_status_platform.customer_accounts import (
    ApiKeyRecord,
    ApiKeyStatus,
    AuditEventType,
    AuditLogService,
    CustomerAccountsBase,
    DynamoApiKeyRepository,
    DynamoAuditLogRepository,
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoPlanRepository,
    DynamoSubscriptionRepository,
    DynamoUserRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationModel,
    OrganizationRecord,
    PlanRecord,
    SqlAlchemyApiKeyRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyInvitationRepository,
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyUserRepository,
    SubscriptionRecord,
    SubscriptionStatus,
    UserRecord,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
)
from charity_status.control_plane.sqlalchemy_store import ControlPlaneBase
from charity_status.enrichments.organization_settings_stores import OrganizationSettingsBase
from charity_status_platform.runtime import (
    backfill_customer_accounts_from_dynamodb,
    build_customer_accounts_repositories,
)


def _sqlite_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+pysqlite:///{tmp_path / name}"


def _session_factory(tmp_path: Path, name: str = "customer_accounts.sqlite3"):
    engine = build_customer_accounts_engine(_sqlite_url(tmp_path, name))
    CustomerAccountsBase.metadata.create_all(engine)
    return build_customer_accounts_session_factory(engine)


def _response_body(response):
    return json.loads(response["body"])


def _load_module_with_postgres_identity_store(monkeypatch, tmp_path: Path, *, api_auth_enabled: bool = False):
    sqlite_url = _sqlite_url(tmp_path, "lambda_query_postgres.sqlite3")
    engine = build_customer_accounts_engine(sqlite_url)
    CustomerAccountsBase.metadata.create_all(engine)
    ControlPlaneBase.metadata.create_all(engine)
    OrganizationSettingsBase.metadata.create_all(engine)

    monkeypatch.setenv("API_AUTH_ENABLED", "true" if api_auth_enabled else "false")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    monkeypatch.setenv("PORTAL_AUTH_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("PLATFORM_POSTGRES_ENABLED", "true")
    monkeypatch.setenv("PLATFORM_POSTGRES_URL", sqlite_url)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.portal_auth_service = None
    module.portal_organization_service = None
    module.portal_organization_context_service = None
    module.portal_membership_service = None
    module.portal_api_key_service = None
    module.portal_subscription_service = None
    module.portal_feature_flag_service = None
    module.portal_usage_service = None
    module.portal_audit_log_service = None
    module.portal_customer_accounts_repositories = None
    module.auth_context_provider = None
    module.quota_metering_hook = None
    return module, None, sqlite_url


def test_repository_builder_selects_postgres_with_narrow_dynamo_compatibility(tmp_path: Path):
    bundle = build_customer_accounts_repositories(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": _sqlite_url(tmp_path, "builder.sqlite3"),
        },
    )

    assert bundle.identity_backend == "postgres"
    assert bundle.users.__class__.__name__ == "SqlAlchemyUserRepository"
    assert bundle.organizations.__class__.__name__ == "SqlAlchemyOrganizationRepository"
    assert bundle.memberships.__class__.__name__ == "SqlAlchemyMembershipRepository"
    assert bundle.plans.__class__.__name__ == "SqlAlchemyPlanRepository"
    assert bundle.subscriptions.__class__.__name__ == "SqlAlchemySubscriptionRepository"
    assert bundle.api_keys.__class__.__name__ == "SqlAlchemyApiKeyRepository"
    assert bundle.audits.__class__.__name__ == "SqlAlchemyAuditLogRepository"
    assert bundle.invitations.__class__.__name__ == "SqlAlchemyInvitationRepository"
    assert bundle.usage.__class__.__name__ == "SqlAlchemyUsageRepository"
    assert bundle.flags.__class__.__name__ == "SqlAlchemyFeatureFlagRepository"


def test_backfill_customer_accounts_from_dynamodb_copies_migrated_identity_records(tmp_path: Path):
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)
    plans = DynamoPlanRepository(dynamodb_resource=resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=resource)
    api_keys = DynamoApiKeyRepository(dynamodb_resource=resource)
    audits = AuditLogService(repository=DynamoAuditLogRepository(dynamodb_resource=resource))

    user = UserRecord(
        user_id="user_1",
        email="person@example.com",
        normalized_email="person@example.com",
        full_name="Portal Person",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
        password_hash="hash",
    )
    active_org = OrganizationRecord(
        organization_id="org_1",
        name="Active Org",
        slug="active-org",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
        contact_email="ops@active.org",
    )
    deleted_org = OrganizationRecord(
        organization_id="org_2",
        name="Deleted Org",
        slug="deleted-org",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-04-02T00:00:00+00:00",
        contact_email="ops@deleted.org",
        deleted_at="2026-04-02T00:00:00+00:00",
        deleted_by_user_id="user_1",
    )
    plan = PlanRecord(
        plan_id="growth",
        plan_name="Growth",
        monthly_price=14900,
        feature_flags=("verification", "benchmarking"),
        request_limit=10000,
        description="Growth plan",
    )
    subscription = SubscriptionRecord(
        subscription_id="sub_1",
        organization_id="org_1",
        plan_id="growth",
        status=SubscriptionStatus.ACTIVE,
        billing_cycle_start="2026-03-01T00:00:00+00:00",
        billing_cycle_end="2026-04-01T00:00:00+00:00",
        created_at="2026-03-01T00:00:00+00:00",
    )
    api_key = ApiKeyRecord(
        key_id="key_1",
        organization_id="org_1",
        hashed_key_value="hashed",
        display_name="Primary key",
        created_at="2026-03-31T00:00:00+00:00",
        created_by_user_id="user_1",
        status=ApiKeyStatus.ACTIVE,
        last_used_at="2026-04-01T00:00:00+00:00",
    )

    users.create(user)
    organizations.create(active_org)
    organizations.create(deleted_org)
    memberships.create(
        MembershipRecord(
            organization_id="org_1",
            user_id="user_1",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )
    plans.seed_defaults([plan])
    subscriptions.put(subscription)
    api_keys.create(api_key)
    audits.record_event(
        event_type=AuditEventType.ORGANIZATION_CREATION,
        actor_user_id="user_1",
        organization_id="org_1",
        target_user_id="user_1",
        metadata={"slug": "active-org"},
        timestamp="2026-03-31T00:00:00+00:00",
    )
    audits.record_event(
        event_type=AuditEventType.USER_REGISTRATION,
        actor_user_id="user_1",
        organization_id=None,
        target_user_id="user_1",
        metadata={"email": "person@example.com"},
        timestamp="2026-03-30T00:00:00+00:00",
    )

    stats = backfill_customer_accounts_from_dynamodb(
        identity_table_name="identity",
        sqlalchemy_url=_sqlite_url(tmp_path, "backfill.sqlite3"),
        table=table,
    )

    session_factory = _session_factory(tmp_path, "backfill.sqlite3")
    assert stats.users == 1
    assert stats.organizations == 2
    assert stats.memberships == 1
    assert stats.plans == 1
    assert stats.subscriptions == 1
    assert stats.api_keys == 1
    assert stats.audit_logs == 2

    assert SqlAlchemyUserRepository(session_factory).get_by_email("person@example.com") is not None
    assert SqlAlchemyOrganizationRepository(session_factory).get_by_slug("active-org") is not None
    assert SqlAlchemyOrganizationRepository(session_factory).get_by_slug("deleted-org") is None
    active_org = SqlAlchemyOrganizationRepository(session_factory).get_by_slug("active-org")
    migrated_user = SqlAlchemyUserRepository(session_factory).get_by_email("person@example.com")
    assert active_org is not None and migrated_user is not None
    assert SqlAlchemyMembershipRepository(session_factory).get(active_org.organization_id, migrated_user.user_id) is not None
    assert SqlAlchemyPlanRepository(session_factory).get("growth") is not None
    assert SqlAlchemySubscriptionRepository(session_factory).get_by_organization(active_org.organization_id) is not None
    assert len(SqlAlchemyApiKeyRepository(session_factory).list_for_organization(active_org.organization_id)) == 1
    assert len(SqlAlchemyAuditLogRepository(session_factory).list_identity_events()) == 1
    assert len(SqlAlchemyAuditLogRepository(session_factory).list_for_organization(active_org.organization_id)) == 1

    session = session_factory()
    try:
        deleted_model = session.scalar(select(OrganizationModel).where(OrganizationModel.slug == "deleted-org").limit(1))
        assert deleted_model is not None
        assert deleted_model.deleted_at is not None
    finally:
        session.close()


def test_postgres_identity_backend_registers_orgs_and_restores_context(monkeypatch, tmp_path: Path):
    module, _resource, _sqlite_url = _load_module_with_postgres_identity_store(monkeypatch, tmp_path)

    register_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"email": "person@example.com", "password": "top-secret-password", "full_name": "Portal Person"}
            ),
        },
        None,
    )
    register_payload = _response_body(register_response)
    access_token = register_payload["data"]["access_token"]

    create_org_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    org_payload = _response_body(create_org_response)

    auth_me_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/auth/me",
            "path": "/v1/auth/me",
            "headers": {"Authorization": f"Bearer {access_token}"},
        },
        None,
    )
    auth_me_payload = _response_body(auth_me_response)

    assert module._get_portal_customer_accounts_repositories().identity_backend == "postgres"
    assert register_response["statusCode"] == 201
    assert create_org_response["statusCode"] == 201
    assert auth_me_response["statusCode"] == 200
    assert auth_me_payload["data"]["user"]["email"] == "person@example.com"
    assert auth_me_payload["data"]["organization_context"]["organization_id"] == org_payload["data"]["organization_id"]
    assert len(auth_me_payload["data"]["available_organizations"]) == 1


def test_postgres_identity_backend_creates_invitations_and_memberships_in_postgres(monkeypatch, tmp_path: Path):
    module, _resource, sqlite_url = _load_module_with_postgres_identity_store(monkeypatch, tmp_path)

    admin_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "admin@example.com", "password": "top-secret-password", "full_name": "Admin User"}),
        },
        None,
    )
    admin_token = _response_body(admin_response)["data"]["access_token"]
    create_org_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"},
            "body": json.dumps({"name": "Verify For Good Org"}),
        },
        None,
    )
    org_payload = _response_body(create_org_response)["data"]

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
    invitation_payload = _response_body(invite_response)["data"]

    invitee_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "invitee@example.com", "password": "top-secret-password", "full_name": "Invitee User"}),
        },
        None,
    )
    invitee_payload = _response_body(invitee_response)["data"]

    accept_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/invitations/accept",
            "path": "/v1/invitations/accept",
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {invitee_payload['access_token']}"},
            "body": json.dumps({"token": invitation_payload["token"]}),
        },
        None,
    )

    session_factory = _session_factory(tmp_path, "lambda_query_postgres.sqlite3")
    membership = SqlAlchemyMembershipRepository(session_factory).get(
        org_payload["organization_id"],
        invitee_payload["user"]["user_id"],
    )
    invitation = SqlAlchemyInvitationRepository(session_factory).get_by_token(invitation_payload["token"])

    assert accept_response["statusCode"] == 200
    assert membership is not None
    assert membership.role is MembershipRole.USER
    assert invitation is not None
    assert invitation.status.value == "accepted"


def test_postgres_identity_backend_manages_org_api_keys_and_updates_last_used(monkeypatch, tmp_path: Path):
    module, _resource, _sqlite_url = _load_module_with_postgres_identity_store(monkeypatch, tmp_path, api_auth_enabled=True)

    register_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"email": "creator@example.com", "password": "top-secret-password", "full_name": "Creator"}),
        },
        None,
    )
    creator_token = _response_body(register_response)["data"]["access_token"]
    create_org_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations",
            "path": "/v1/organizations",
            "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {creator_token}"},
            "body": json.dumps({"name": "API Org"}),
        },
        None,
    )
    org_payload = _response_body(create_org_response)["data"]

    create_key_response = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organizations/current/api-keys",
            "path": "/v1/organizations/current/api-keys",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {creator_token}",
                "X-Portal-Account-Id": org_payload["organization_id"],
                "X-Portal-Workspace-Id": org_payload["organization_id"],
            },
            "body": json.dumps({"display_name": "CLI Key"}),
        },
        None,
    )
    create_key_payload = _response_body(create_key_response)["data"]

    auth_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/12-34A6789",
            "pathParameters": {"ein": "12-34A6789"},
            "headers": {"x-api-key": create_key_payload["secret"]},
        },
        None,
    )

    session_factory = _session_factory(tmp_path, "lambda_query_postgres.sqlite3")
    persisted = SqlAlchemyApiKeyRepository(session_factory).get_by_key_id(create_key_payload["api_key"]["key_id"])

    assert create_key_response["statusCode"] == 201
    assert auth_response["statusCode"] == 400
    assert persisted is not None
    assert persisted.last_used_at is not None
