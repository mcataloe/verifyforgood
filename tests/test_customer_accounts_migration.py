from __future__ import annotations

from pathlib import Path

from verification.backend.shared.customer_accounts import (
    ApiKeyRecord,
    ApiKeyStatus,
    AuditEventType,
    AuditLogService,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationRecord,
    PlanRecord,
    SubscriptionRecord,
    SubscriptionStatus,
    UserRecord,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
)
from verification.backend.shared.customer_accounts import (
    DynamoApiKeyRepository,
    DynamoAuditLogRepository,
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoPlanRepository,
    DynamoSubscriptionRepository,
    DynamoUserRepository,
)
from verification.backend.shared.runtime import run_customer_accounts_migration


def _sqlite_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+pysqlite:///{tmp_path / name}"


def test_customer_accounts_migration_dry_run_reports_missing_targets(tmp_path: Path):
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    DynamoUserRepository(dynamodb_resource=resource).create(
        UserRecord(
            user_id="user_1",
            email="person@example.com",
            normalized_email="person@example.com",
            full_name="Portal Person",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
            password_hash="hash",
        )
    )
    DynamoOrganizationRepository(dynamodb_resource=resource).create(
        OrganizationRecord(
            organization_id="org_1",
            name="Active Org",
            slug="active-org",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )

    report = run_customer_accounts_migration(
        identity_table_name="identity",
        sqlalchemy_url=_sqlite_url(tmp_path, "dry_run.sqlite3"),
        table=table,
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.scanned_items == 2
    assert report.source_counts.users == 1
    assert report.source_counts.organizations == 1
    assert report.target_counts.users == 0
    assert report.target_counts.organizations == 0
    assert report.validation["users"].missing == 1
    assert report.validation["organizations"].missing == 1


def test_customer_accounts_migration_applies_and_validates_identity_rows(tmp_path: Path):
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    DynamoUserRepository(dynamodb_resource=resource).create(
        UserRecord(
            user_id="user_1",
            email="person@example.com",
            normalized_email="person@example.com",
            full_name="Portal Person",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
            password_hash="hash",
        )
    )
    DynamoOrganizationRepository(dynamodb_resource=resource).create(
        OrganizationRecord(
            organization_id="org_1",
            name="Active Org",
            slug="active-org",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )
    DynamoMembershipRepository(dynamodb_resource=resource).create(
        MembershipRecord(
            organization_id="org_1",
            user_id="user_1",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )
    DynamoPlanRepository(dynamodb_resource=resource).seed_defaults(
        [
            PlanRecord(
                plan_id="growth",
                plan_name="Growth",
                monthly_price=14900,
                feature_flags=("verification",),
                request_limit=10000,
                description="Growth plan",
            )
        ]
    )
    DynamoSubscriptionRepository(dynamodb_resource=resource).put(
        SubscriptionRecord(
            subscription_id="sub_1",
            organization_id="org_1",
            plan_id="growth",
            status=SubscriptionStatus.ACTIVE,
            billing_cycle_start="2026-03-01T00:00:00+00:00",
            billing_cycle_end="2026-04-01T00:00:00+00:00",
            created_at="2026-03-01T00:00:00+00:00",
        )
    )
    DynamoApiKeyRepository(dynamodb_resource=resource).create(
        ApiKeyRecord(
            key_id="key_1",
            organization_id="org_1",
            hashed_key_value="hashed",
            display_name="Primary key",
            description="Primary integration key",
            created_at="2026-03-31T00:00:00+00:00",
            created_by_user_id="user_1",
            status=ApiKeyStatus.ACTIVE,
        )
    )
    AuditLogService(repository=DynamoAuditLogRepository(dynamodb_resource=resource)).record_event(
        event_type=AuditEventType.ORGANIZATION_CREATION,
        actor_user_id="user_1",
        organization_id="org_1",
        target_user_id="user_1",
        metadata={"slug": "active-org"},
        timestamp="2026-03-31T00:00:00+00:00",
    )

    report = run_customer_accounts_migration(
        identity_table_name="identity",
        sqlalchemy_url=_sqlite_url(tmp_path, "apply.sqlite3"),
        table=table,
    )

    assert report.dry_run is False
    assert report.source_counts.users == 1
    assert report.source_counts.organizations == 1
    assert report.source_counts.memberships == 1
    assert report.source_counts.plans == 1
    assert report.source_counts.subscriptions == 1
    assert report.source_counts.api_keys == 1
    assert report.source_counts.audit_logs == 1
    assert report.target_counts == report.source_counts
    assert all(entity_validation.missing == 0 for entity_validation in report.validation.values())

