from __future__ import annotations

from pathlib import Path

from verification_platform.customer_accounts import (
    ApiKeyRecord,
    ApiKeyStatus,
    AuditEventType,
    AuditRecord,
    CustomerAccountsBase,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationRecord,
    PlanRecord,
    SqlAlchemyApiKeyRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemySupportTicketRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyUserRepository,
    SubscriptionRecord,
    SubscriptionStatus,
    SupportDeliveryMode,
    SupportTicketDeliveryStatus,
    SupportTicketRecord,
    UserRecord,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
)
from verification_platform.runtime import build_customer_accounts_postgres_repositories


def _session_factory(tmp_path: Path):
    db_path = tmp_path / "identity.sqlite3"
    engine = build_customer_accounts_engine(f"sqlite+pysqlite:///{db_path}")
    CustomerAccountsBase.metadata.create_all(engine)
    return build_customer_accounts_session_factory(engine)


def _user() -> UserRecord:
    return UserRecord(
        user_id="user_1",
        email="Person@example.com",
        normalized_email="person@example.com",
        full_name="Person Example",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
        password_hash="hash",
    )


def _organization() -> OrganizationRecord:
    return OrganizationRecord(
        organization_id="org_1",
        name="Example Org",
        slug="example-org",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
        contact_email="ops@example.org",
    )


def test_customer_accounts_metadata_contains_foundational_tables():
    table_names = set(CustomerAccountsBase.metadata.tables.keys())

    assert "users" in table_names
    assert "organizations" in table_names
    assert "organization_memberships" in table_names
    assert "plans" in table_names
    assert "organization_subscriptions" in table_names
    assert "organization_api_keys" in table_names
    assert "organization_audit_logs" in table_names
    assert "organization_support_tickets" in table_names


def test_sqlalchemy_user_repository_create_and_get(tmp_path: Path):
    repository = SqlAlchemyUserRepository(_session_factory(tmp_path))
    created = repository.create(_user())

    fetched = repository.get(created.user_id)
    by_email = repository.get_by_email("PERSON@example.com")

    assert fetched == created
    assert by_email == created


def test_sqlalchemy_organization_repository_handles_slug_and_soft_delete(tmp_path: Path):
    repository = SqlAlchemyOrganizationRepository(_session_factory(tmp_path))
    created = repository.create(_organization())

    updated = repository.update_profile(
        created.organization_id,
        name="Renamed Org",
        slug="renamed-org",
        contact_email="support@example.org",
        updated_at="2026-04-01T00:00:00+00:00",
    )

    assert updated is not None
    assert updated.name == "Renamed Org"
    assert updated.slug == "renamed-org"
    assert repository.get_by_slug("example-org") is None
    assert repository.get_by_slug("renamed-org") is not None

    repository.soft_delete(created.organization_id, deleted_at="2026-04-02T00:00:00+00:00", deleted_by_user_id="user_1")

    assert repository.get(created.organization_id) is None
    assert repository.get_by_slug("renamed-org") is None


def test_sqlalchemy_membership_repository_create_list_update_and_delete(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    created_user = SqlAlchemyUserRepository(session_factory).create(_user())
    created_org = SqlAlchemyOrganizationRepository(session_factory).create(_organization())
    repository = SqlAlchemyMembershipRepository(session_factory)

    created = repository.create(
        MembershipRecord(
            organization_id=created_org.organization_id,
            user_id=created_user.user_id,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )

    assert repository.get(created_org.organization_id, created_user.user_id) == created
    assert repository.list_for_organization(created_org.organization_id) == [created]
    assert repository.list_for_user(created_user.user_id) == [created]

    updated = repository.update_membership(
        created_org.organization_id,
        created_user.user_id,
        role=MembershipRole.USER.value,
        status=MembershipStatus.SUSPENDED.value,
        updated_at="2026-04-01T00:00:00+00:00",
    )

    assert updated is not None
    assert updated.role is MembershipRole.USER
    assert updated.status is MembershipStatus.SUSPENDED
    assert repository.delete(created_org.organization_id, created_user.user_id) is True
    assert repository.get(created_org.organization_id, created_user.user_id) is None


def test_sqlalchemy_plan_subscription_and_api_key_repositories(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    SqlAlchemyOrganizationRepository(session_factory).create(_organization())
    plan_repository = SqlAlchemyPlanRepository(session_factory)
    subscription_repository = SqlAlchemySubscriptionRepository(session_factory)
    api_key_repository = SqlAlchemyApiKeyRepository(session_factory)

    plan = PlanRecord(
        plan_id=None,
        plan_code="growth",
        plan_name="Growth",
        monthly_price=4900,
        feature_flags=("enable_bulk_lookup",),
        request_limit=10000,
        description="Growth plan",
    )
    plan_repository.seed_defaults([plan])

    persisted_plan = plan_repository.get("growth")
    assert persisted_plan is not None
    assert persisted_plan.plan_code == "growth"
    assert plan_repository.list_all() == [persisted_plan]

    subscription = SubscriptionRecord(
        subscription_id=None,
        organization_id=1,
        plan_id=persisted_plan.plan_id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle_start="2026-03-01T00:00:00+00:00",
        billing_cycle_end="2026-04-01T00:00:00+00:00",
        created_at="2026-03-01T00:00:00+00:00",
        pending_plan_id=persisted_plan.plan_id,
        pending_plan_effective_at="2026-04-01T00:00:00+00:00",
        cancel_at_period_end=True,
        updated_at="2026-03-20T00:00:00+00:00",
        grace_period_ends_at="2026-03-27T00:00:00+00:00",
        billing_status="past_due",
    )
    persisted_subscription = subscription_repository.put(subscription)
    assert subscription_repository.get_by_organization(1) == persisted_subscription

    api_key = ApiKeyRecord(
        key_id=None,
        organization_id=1,
        hashed_key_value="hashed",
        display_name="Primary key",
        description="Primary integration key",
        created_at="2026-03-31T00:00:00+00:00",
        created_by_user_id=1,
        status=ApiKeyStatus.ACTIVE,
    )
    persisted_api_key = api_key_repository.create(api_key)
    touched = api_key_repository.touch_last_used(persisted_api_key.key_id, used_at="2026-04-01T00:00:00+00:00")
    revoked = api_key_repository.revoke(1, persisted_api_key.key_id)

    assert api_key_repository.get_by_key_id(persisted_api_key.key_id) is not None
    assert len(api_key_repository.list_for_organization(1)) == 1
    assert touched is not None and touched.last_used_at == "2026-04-01T00:00:00+00:00"
    assert revoked is not None and revoked.status is ApiKeyStatus.REVOKED


def test_sqlalchemy_audit_repository_lists_and_pages(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    created_org = SqlAlchemyOrganizationRepository(session_factory).create(_organization())
    repository = SqlAlchemyAuditLogRepository(session_factory)

    first = AuditRecord(
        audit_id="audit_1",
        event_type=AuditEventType.ORGANIZATION_CREATION,
        actor_user_id=1,
        organization_id=created_org.organization_id,
        target_user_id=None,
        timestamp="2026-03-31T00:00:00+00:00",
        metadata={"step": 1},
    )
    second = AuditRecord(
        audit_id="audit_2",
        event_type=AuditEventType.ORGANIZATION_SETTINGS_UPDATE,
        actor_user_id=1,
        organization_id=created_org.organization_id,
        target_user_id=None,
        timestamp="2026-04-01T00:00:00+00:00",
        metadata={"step": 2},
    )
    identity_event = AuditRecord(
        audit_id="audit_3",
        event_type=AuditEventType.USER_REGISTRATION,
        actor_user_id=1,
        organization_id=None,
        target_user_id=1,
        timestamp="2026-04-02T00:00:00+00:00",
        metadata={},
    )
    repository.create(first)
    repository.create(second)
    repository.create(identity_event)

    org_items = repository.list_for_organization(created_org.organization_id)
    page, cursor = repository.list_for_organization_page(created_org.organization_id, limit=1)
    page_two, next_cursor = repository.list_for_organization_page(created_org.organization_id, limit=1, cursor=cursor)

    assert len(org_items) == 2
    assert org_items[0].timestamp > org_items[1].timestamp
    assert len(page) == 1
    assert cursor is not None
    assert len(page_two) == 1
    assert next_cursor is None
    assert len(repository.list_identity_events()) == 1


def test_sqlalchemy_support_ticket_repository_round_trips_ticket_state(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    created_org = SqlAlchemyOrganizationRepository(session_factory).create(_organization())
    repository = SqlAlchemySupportTicketRepository(session_factory)

    created = repository.create(
        SupportTicketRecord(
            ticket_id=None,
            support_request_id="support_req_123",
            organization_id=created_org.organization_id,
            actor_user_id=1,
            account_id="acct_1",
            workspace_id="ws_1",
            category="recommendation",
            subject="Token issue",
            description="The API token request is failing with a 401 response.",
            reply_email="submitter@example.org",
            watchers=("ops@example.org", "reviewer@example.org"),
            route_hash="#/settings?nav=customer-admin-settings",
            user_agent="Portal Browser",
            current_plan="growth",
            membership_role="admin",
            delivery_mode=SupportDeliveryMode.RECORDED_AND_EMAILED,
            delivery_provider="gmail_smtp",
            delivery_status=SupportTicketDeliveryStatus.PENDING,
            delivery_recipient="support@example.com",
            provider_message_id=None,
            delivery_error=None,
            created_at="2026-04-20T00:00:00+00:00",
        )
    )

    sent = repository.mark_sent(
        "support_req_123",
        provider_message_id="message-123",
        delivery_recipient="support@example.com",
        emailed_at="2026-04-20T00:01:00+00:00",
    )

    assert created.ticket_id is not None
    assert sent is not None
    assert sent.delivery_status is SupportTicketDeliveryStatus.SENT
    assert sent.provider_message_id == "message-123"
    assert repository.get_by_support_request_id("support_req_123") == sent


def test_runtime_builder_returns_postgres_bundle_only_when_selected(tmp_path: Path):
    sqlite_url = f"sqlite+pysqlite:///{tmp_path / 'runtime.sqlite3'}"
    engine = build_customer_accounts_engine(sqlite_url)
    CustomerAccountsBase.metadata.create_all(engine)

    bundle = build_customer_accounts_postgres_repositories(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": sqlite_url,
        }
    )

    assert bundle is not None
    assert bundle.users.__class__.__name__ == "SqlAlchemyUserRepository"
    assert bundle.support_tickets.__class__.__name__ == "SqlAlchemySupportTicketRepository"

