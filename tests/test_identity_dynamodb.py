from __future__ import annotations

import pathlib
import sys
from datetime import datetime

import pytest

from charity_status.enrichments import EvaluationContext


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


from charity_status_platform.customer_accounts import (  # noqa: E402
    API_KEY_LOOKUP_INDEX,
    AUDIT_GLOBAL_PARTITION_KEY,
    ApiKeyCreateRequest,
    ApiKeyService,
    ApiKeyStatus,
    AuditEventType,
    AuditRecord,
    DEFAULT_PORTAL_PLANS,
    DynamoFeatureFlagRepository,
    FeatureFlagKey,
    FeatureFlagRecord,
    FeatureFlagService,
    IdentityProviderType,
    DynamoApiKeyRepository,
    DynamoPlanRepository,
    DynamoSubscriptionRepository,
    DynamoUsageRepository,
    DuplicateMembershipError,
    DuplicateOrganizationSlugError,
    DuplicateUserEmailError,
    DynamoAuditLogRepository,
    DynamoInvitationRepository,
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoUserRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    InvitationRecord,
    InvitationStatus,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationRecord,
    PlanRecord,
    PLAN_LOOKUP_INDEX,
    PLAN_DEFAULT_FEATURE_FLAGS,
    ResolvedFeatureFlag,
    SubscriptionResolvedResponse,
    SubscriptionRecord,
    SubscriptionScaffoldingError,
    SubscriptionService,
    SubscriptionStatus,
    UsageMetricType,
    UsageService,
    UsageTrackingError,
    UserRecord,
)
from charity_status_platform.customer_accounts.billing_calendar import prorated_amount_cents  # noqa: E402


def test_customer_accounts_exports_identity_phase_surface():
    import charity_status_platform.customer_accounts as customer_accounts

    assert customer_accounts.IDENTITY_TABLE_NAME == "identity"
    assert customer_accounts.API_KEY_LOOKUP_INDEX == API_KEY_LOOKUP_INDEX
    assert customer_accounts.PLAN_LOOKUP_INDEX == PLAN_LOOKUP_INDEX
    assert hasattr(customer_accounts, "UserRepository")
    assert hasattr(customer_accounts, "OrganizationRepository")
    assert hasattr(customer_accounts, "MembershipRepository")
    assert hasattr(customer_accounts, "InvitationRepository")
    assert hasattr(customer_accounts, "ApiKeyRepository")
    assert hasattr(customer_accounts, "PlanRepository")
    assert hasattr(customer_accounts, "SubscriptionRepository")
    assert hasattr(customer_accounts, "UsageRepository")
    assert hasattr(customer_accounts, "AuditLogRepository")
    assert hasattr(customer_accounts, "DynamoApiKeyRepository")
    assert hasattr(customer_accounts, "DynamoPlanRepository")
    assert hasattr(customer_accounts, "DynamoUsageRepository")
    assert hasattr(customer_accounts, "DynamoSubscriptionRepository")
    assert hasattr(customer_accounts, "DynamoUserRepository")
    assert hasattr(customer_accounts, "DynamoOrganizationRepository")
    assert hasattr(customer_accounts, "DynamoMembershipRepository")
    assert hasattr(customer_accounts, "DynamoInvitationRepository")
    assert hasattr(customer_accounts, "DynamoAuditLogRepository")
    assert hasattr(customer_accounts, "AuditLogService")
    assert hasattr(customer_accounts, "ApiKeyService")
    assert hasattr(customer_accounts, "FeatureFlagService")
    assert hasattr(customer_accounts, "SubscriptionService")
    assert hasattr(customer_accounts, "UsageService")
    assert hasattr(customer_accounts, "AuditRecord")
    assert hasattr(customer_accounts, "FeatureFlagRecord")
    assert hasattr(customer_accounts, "IdentityProviderType")
    assert customer_accounts.AUDIT_GLOBAL_PARTITION_KEY == AUDIT_GLOBAL_PARTITION_KEY
    assert hasattr(customer_accounts, "FakeIdentityDynamoTable")
    assert hasattr(customer_accounts, "FakeIdentityDynamoResource")


def test_membership_creation_supports_org_and_user_lookup_patterns():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)

    created = memberships.create(
        MembershipRecord(
            organization_id="org_1",
            user_id="user_1",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )

    org_members = memberships.list_for_organization("org_1")
    user_orgs = memberships.list_for_user("user_1")

    assert created.role is MembershipRole.ADMIN
    assert len(org_members) == 1
    assert len(user_orgs) == 1
    assert org_members[0].user_id == "user_1"
    assert user_orgs[0].organization_id == "org_1"


def test_duplicate_membership_prevention_raises_domain_error():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)
    membership = MembershipRecord(
        organization_id="org_1",
        user_id="user_1",
        role=MembershipRole.USER,
        status=MembershipStatus.ACTIVE,
        created_at="2026-03-26T00:00:00+00:00",
        updated_at="2026-03-26T00:00:00+00:00",
    )

    memberships.create(membership)

    with pytest.raises(DuplicateMembershipError):
        memberships.create(membership)


def test_membership_role_update_returns_updated_shape():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)
    memberships.create(
        MembershipRecord(
            organization_id="org_1",
            user_id="user_1",
            role=MembershipRole.USER,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )

    updated = memberships.update_role("org_1", "user_1", "admin")
    reloaded = memberships.get("org_1", "user_1")

    assert updated is not None
    assert updated.role is MembershipRole.ADMIN
    assert reloaded is not None
    assert reloaded.role is MembershipRole.ADMIN


def test_email_uniqueness_logic_uses_normalized_lookup():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)

    users.create(
        UserRecord(
            user_id="user_1",
            email="Alice@Example.com",
            normalized_email="alice@example.com",
            full_name="Alice",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )

    with pytest.raises(DuplicateUserEmailError):
        users.create(
            UserRecord(
                user_id="user_2",
                email="alice@example.com",
                normalized_email="alice@example.com",
                full_name="Alice Two",
                created_at="2026-03-26T00:00:00+00:00",
                updated_at="2026-03-26T00:00:00+00:00",
            )
        )

    loaded = users.get_by_email("ALICE@example.com")

    assert loaded is not None
    assert loaded.user_id == "user_1"


def test_user_round_trip_includes_identity_provider_metadata_and_legacy_defaults():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)

    users.create(
        UserRecord(
            user_id="user_1",
            email="alice@example.com",
            normalized_email="alice@example.com",
            full_name="Alice",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
            password_hash="hashed",
            identity_provider_type=IdentityProviderType.OIDC_FUTURE,
            external_subject_id="oidc|alice",
        )
    )
    loaded = users.get("user_1")

    legacy_key = ("USER#legacy_user", "USER")
    table._items[legacy_key] = {
        "pk": "USER#legacy_user",
        "sk": "USER",
        "type": "USER",
        "user_id": "legacy_user",
        "email": "legacy@example.com",
        "normalized_email": "legacy@example.com",
        "full_name": "Legacy User",
        "created_at": "2026-03-26T00:00:00+00:00",
        "updated_at": "2026-03-26T00:00:00+00:00",
        "password_hash": "legacy-hash",
        "gsi1pk": "EMAIL#legacy@example.com",
        "gsi1sk": "USER#legacy_user",
    }
    legacy_loaded = users.get("legacy_user")

    assert loaded is not None
    assert loaded.identity_provider_type is IdentityProviderType.OIDC_FUTURE
    assert loaded.external_subject_id == "oidc|alice"
    assert legacy_loaded is not None
    assert legacy_loaded.identity_provider_type is IdentityProviderType.LOCAL_PASSWORD
    assert legacy_loaded.external_subject_id is None


def test_invitation_lookup_by_token_and_acceptance_round_trip():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    invitations = DynamoInvitationRepository(dynamodb_resource=resource)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)

    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )
    invitations.create(
        InvitationRecord(
            invitation_id="invite_1",
            organization_id="org_1",
            email="invitee@example.com",
            normalized_email="invitee@example.com",
            token="token_123",
            role=MembershipRole.USER,
            status=InvitationStatus.PENDING,
            invited_by_user_id="user_admin",
            created_at="2026-03-26T00:00:00+00:00",
            expires_at="2026-04-02T00:00:00+00:00",
        )
    )

    pending = invitations.get_by_token("token_123")
    accepted = invitations.mark_accepted("token_123", accepted_at="2026-03-27T00:00:00+00:00")

    assert pending is not None
    assert pending.organization_id == "org_1"
    assert accepted is not None
    assert accepted.status is InvitationStatus.ACCEPTED
    assert accepted.accepted_at == "2026-03-27T00:00:00+00:00"


def test_organization_lookup_by_slug_and_duplicate_slug_rejection():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )

    loaded = organizations.get_by_slug("VERIFY-FOR-GOOD-ORG")

    assert loaded is not None
    assert loaded.organization_id == "org_1"

    with pytest.raises(DuplicateOrganizationSlugError):
        organizations.create(
            OrganizationRecord(
                organization_id="org_2",
                name="Second Org",
                slug="verify-for-good-org",
                created_at="2026-03-26T00:00:00+00:00",
                updated_at="2026-03-26T00:00:00+00:00",
            )
        )


def test_soft_deleted_organization_is_hidden_from_standard_lookups():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-26T00:00:00+00:00",
            updated_at="2026-03-26T00:00:00+00:00",
        )
    )

    deleted = organizations.soft_delete(
        "org_1",
        deleted_at="2026-03-27T00:00:00+00:00",
        deleted_by_user_id="user_admin",
    )

    assert deleted is not None
    assert deleted.deleted_at == "2026-03-27T00:00:00+00:00"
    assert deleted.deleted_by_user_id == "user_admin"
    assert organizations.get("org_1") is None
    assert organizations.get_by_slug("verify-for-good-org") is None


def test_audit_record_round_trips_with_metadata_and_scope_partitioning():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    audits = DynamoAuditLogRepository(dynamodb_resource=resource)

    org_event = audits.create(
        AuditRecord(
            audit_id="audit_org_1",
            event_type=AuditEventType.ORGANIZATION_CREATION,
            actor_user_id="user_admin",
            organization_id="org_1",
            target_user_id="user_admin",
            timestamp="2026-03-27T00:00:00+00:00",
            metadata={"slug": "verify-for-good-org", "bootstrap_role": "admin"},
        )
    )
    identity_event = audits.create(
        AuditRecord(
            audit_id="audit_user_1",
            event_type=AuditEventType.USER_REGISTRATION,
            actor_user_id="user_1",
            organization_id=None,
            target_user_id="user_1",
            timestamp="2026-03-27T00:05:00+00:00",
            metadata={"email": "person@example.com"},
        )
    )

    org_items = audits.list_for_organization("org_1")
    identity_items = audits.list_identity_events()

    assert org_event.event_type is AuditEventType.ORGANIZATION_CREATION
    assert org_items[0].metadata["slug"] == "verify-for-good-org"
    assert org_items[0].organization_id == "org_1"
    assert identity_event.event_type is AuditEventType.USER_REGISTRATION
    assert identity_items[0].metadata["email"] == "person@example.com"
    assert identity_items[0].organization_id is None


def test_nonprofit_audit_record_round_trips_with_structured_metadata():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    audits = DynamoAuditLogRepository(dynamodb_resource=resource)

    created = audits.create(
        AuditRecord(
            audit_id="audit_nonprofit_lookup_1",
            event_type=AuditEventType.NONPROFIT_LOOKUP,
            actor_user_id=None,
            organization_id="org_1",
            target_user_id=None,
            timestamp="2026-03-29T12:00:00+00:00",
            metadata={
                "endpoint": "GET /v1/nonprofit/{ein}",
                "ein": "123456789",
                "organization_id": "org_1",
                "response_sources": ["candid", "irs"],
                "user_id": None,
            },
        )
    )

    items = audits.list_for_organization("org_1")

    assert created.event_type is AuditEventType.NONPROFIT_LOOKUP
    assert items[0].event_type is AuditEventType.NONPROFIT_LOOKUP
    assert items[0].metadata["endpoint"] == "GET /v1/nonprofit/{ein}"
    assert items[0].metadata["ein"] == "123456789"
    assert items[0].metadata["response_sources"] == ["candid", "irs"]
    assert items[0].metadata["user_id"] is None


def test_org_api_key_round_trips_with_lookup_revocation_and_last_used():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    memberships = DynamoMembershipRepository(dynamodb_resource=resource)
    api_keys = DynamoApiKeyRepository(dynamodb_resource=resource)
    service = ApiKeyService(
        organizations=organizations,
        memberships=memberships,
        api_keys=api_keys,
    )

    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    memberships.create(
        MembershipRecord(
            organization_id="org_1",
            user_id="user_admin",
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )

    created = service.create_key(
        organization_id="org_1",
        actor_user_id="user_admin",
        request=ApiKeyCreateRequest(display_name="CI Key"),
    )
    persisted = api_keys.get_by_key_id(created.api_key.key_id)
    listed = service.list_keys(organization_id="org_1", actor_user_id="user_admin")
    touched = api_keys.touch_last_used(created.api_key.key_id, used_at="2026-03-28T01:00:00+00:00")
    revoked = service.revoke_key(
        organization_id="org_1",
        actor_user_id="user_admin",
        key_id=created.api_key.key_id,
    )

    assert created.secret.startswith(f"csk_{created.api_key.key_id}.")
    assert persisted is not None
    assert persisted.hashed_key_value != created.secret
    assert persisted.display_name == "CI Key"
    assert len(listed) == 1
    assert listed[0].key_id == created.api_key.key_id
    assert touched is not None
    assert touched.last_used_at == "2026-03-28T01:00:00+00:00"
    assert revoked.status == ApiKeyStatus.REVOKED.value
    reloaded = api_keys.get_by_key_id(created.api_key.key_id)
    assert reloaded is not None
    assert reloaded.status is ApiKeyStatus.REVOKED


def test_seeded_portal_plans_round_trip_through_plan_repository():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    plans = DynamoPlanRepository(dynamodb_resource=resource)

    assert plans.list_all() == []

    plans.seed_defaults(list(DEFAULT_PORTAL_PLANS))

    loaded = plans.list_all()
    growth = plans.get("growth")

    assert [plan.plan_id for plan in loaded] == ["enterprise", "growth", "starter"]
    assert growth is not None
    assert growth.plan_name == "Growth"
    assert "financial_trends" in growth.feature_flags
    assert growth.request_limit == 10000


def test_subscription_service_links_subscription_to_organization_and_resolves_plan():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    plans = DynamoPlanRepository(dynamodb_resource=resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=resource)
    service = SubscriptionService(
        organizations=organizations,
        plans=plans,
        subscriptions=subscriptions,
    )

    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )

    created = service.upsert_subscription(
        organization_id="org_1",
        plan_id="growth",
        billing_cycle_start="2026-03-28T00:00:00+00:00",
        billing_cycle_end="2026-04-27T00:00:00+00:00",
    )
    loaded = service.get_subscription_for_organization("org_1")

    assert isinstance(created, SubscriptionResolvedResponse)
    assert created.subscription.organization_id == "org_1"
    assert created.subscription.status is SubscriptionStatus.ACTIVE
    assert created.plan.plan_id == "growth"
    assert loaded.subscription.subscription_id == created.subscription.subscription_id
    assert loaded.plan.plan_name == "Growth"


def test_subscription_service_uses_month_boundary_proration_for_new_subscription():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    plans = DynamoPlanRepository(dynamodb_resource=resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=resource)
    service = SubscriptionService(
        organizations=organizations,
        plans=plans,
        subscriptions=subscriptions,
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    plans.seed_defaults(
        [
            PlanRecord(
                plan_id="growth",
                plan_name="Growth",
                monthly_price=9900,
                feature_flags=("verification",),
                request_limit=10000,
                description="Growth plan",
            )
        ]
    )

    created = service.create_or_activate_subscription(
        organization_id="org_1",
        plan_id="growth",
        effective_at="2026-03-16T00:00:00+00:00",
    )

    assert created.subscription.billing_cycle_start == "2026-03-16T00:00:00+00:00"
    assert created.subscription.billing_cycle_end == "2026-04-01T00:00:00+00:00"
    assert created.current_charge_cents == 5110
    assert created.is_prorated is True
    assert created.billable_days == 16
    assert created.days_in_month == 31
    assert created.next_renewal_at == "2026-04-01T00:00:00+00:00"


def test_subscription_service_supports_upgrade_downgrade_and_cancellation_metadata():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    plans = DynamoPlanRepository(dynamodb_resource=resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=resource)
    service = SubscriptionService(
        organizations=organizations,
        plans=plans,
        subscriptions=subscriptions,
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    plans.seed_defaults(
        [
            PlanRecord(
                plan_id="starter",
                plan_name="Starter",
                monthly_price=4900,
                feature_flags=("verification",),
                request_limit=1000,
                description="Starter plan",
            ),
            PlanRecord(
                plan_id="growth",
                plan_name="Growth",
                monthly_price=9900,
                feature_flags=("verification", "risk_flags"),
                request_limit=10000,
                description="Growth plan",
            ),
            PlanRecord(
                plan_id="enterprise",
                plan_name="Enterprise",
                monthly_price=49900,
                feature_flags=("verification", "risk_flags"),
                request_limit=250000,
                description="Enterprise plan",
            ),
        ]
    )
    service.create_or_activate_subscription(
        organization_id="org_1",
        plan_id="starter",
        effective_at="2026-03-01T00:00:00+00:00",
    )

    upgraded = service.apply_immediate_upgrade(
        organization_id="org_1",
        plan_id="growth",
        effective_at="2026-03-16T00:00:00+00:00",
    )
    downgraded = service.schedule_downgrade(
        organization_id="org_1",
        plan_id="starter",
        effective_at="2026-03-20T00:00:00+00:00",
    )
    canceled = service.schedule_cancellation(organization_id="org_1")
    loaded = service.get_subscription_for_organization("org_1")

    assert upgraded.current_charge_cents == prorated_amount_cents(5000, datetime.fromisoformat("2026-03-16T00:00:00+00:00"))
    assert upgraded.quota_delta == 4646
    assert downgraded.pending_plan_id == "starter"
    assert downgraded.pending_plan_effective_at == "2026-04-01T00:00:00+00:00"
    assert canceled.cancel_at_period_end is True
    assert loaded.subscription.pending_plan_id == "starter"
    assert loaded.subscription.cancel_at_period_end is True


def test_dynamo_subscription_repository_round_trips_extended_fields():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    repository = DynamoSubscriptionRepository(dynamodb_resource=resource)

    stored = repository.put(
        SubscriptionRecord(
            subscription_id="sub_1",
            organization_id="org_1",
            plan_id="growth",
            status=SubscriptionStatus.ACTIVE,
            billing_cycle_start="2026-03-16T00:00:00+00:00",
            billing_cycle_end="2026-04-01T00:00:00+00:00",
            created_at="2026-03-16T00:00:00+00:00",
            pending_plan_id="starter",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            cancel_at_period_end=True,
            updated_at="2026-03-20T00:00:00+00:00",
            grace_period_ends_at="2026-03-27T00:00:00+00:00",
            billing_status="past_due",
        )
    )

    loaded = repository.get_by_organization("org_1")

    assert stored.pending_plan_id == "starter"
    assert loaded is not None
    assert loaded.pending_plan_effective_at == "2026-04-01T00:00:00+00:00"
    assert loaded.cancel_at_period_end is True
    assert loaded.grace_period_ends_at == "2026-03-27T00:00:00+00:00"
    assert loaded.billing_status == "past_due"


def test_subscription_service_rejects_unknown_plan_and_unknown_organization():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    service = SubscriptionService(
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        plans=DynamoPlanRepository(dynamodb_resource=resource),
        subscriptions=DynamoSubscriptionRepository(dynamodb_resource=resource),
    )

    with pytest.raises(SubscriptionScaffoldingError, match="organization_id must reference an existing organization"):
        service.upsert_subscription(organization_id="org_missing", plan_id="growth")

    with pytest.raises(SubscriptionScaffoldingError, match="known portal subscription plan"):
        service.get_plan("unknown")


def test_usage_service_tracks_monthly_metrics_and_supports_reset():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    usage = DynamoUsageRepository(dynamodb_resource=resource)
    service = UsageService(
        organizations=organizations,
        usage=usage,
    )

    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )

    first = service.increment_metric(
        organization_id="org_1",
        metric_type=UsageMetricType.API_REQUESTS.value,
        period_month="2026-03",
        units=1,
    )
    second = service.increment_metric(
        organization_id="org_1",
        metric_type=UsageMetricType.API_REQUESTS.value,
        period_month="2026-03",
        units=2,
    )
    lookups = service.increment_metric(
        organization_id="org_1",
        metric_type=UsageMetricType.NONPROFIT_LOOKUPS.value,
        period_month="2026-03",
        units=1,
    )
    search = service.increment_metric(
        organization_id="org_1",
        metric_type=UsageMetricType.SEARCH_REQUESTS.value,
        period_month="2026-03",
        units=2,
    )
    april = service.increment_metric(
        organization_id="org_1",
        metric_type=UsageMetricType.API_REQUESTS.value,
        period_month="2026-04",
        units=1,
    )
    reset = service.reset_metric(
        organization_id="org_1",
        metric_type=UsageMetricType.API_REQUESTS.value,
        period_month="2026-04",
    )
    march_usage = service.get_monthly_usage(organization_id="org_1", period_month="2026-03")

    assert first.request_count == 1
    assert second.request_count == 3
    assert lookups.request_count == 1
    assert search.request_count == 2
    assert april.request_count == 1
    assert reset.request_count == 0
    assert {(item.metric_type.value, item.request_count) for item in march_usage} == {
        ("api_requests", 3),
        ("nonprofit_lookups", 1),
        ("search_requests", 2),
    }


def test_usage_service_rejects_unknown_organization():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    service = UsageService(
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        usage=DynamoUsageRepository(dynamodb_resource=resource),
    )

    with pytest.raises(UsageTrackingError, match="existing organization"):
        service.increment_metric(
            organization_id="org_missing",
            metric_type=UsageMetricType.API_REQUESTS.value,
            period_month="2026-03",
            units=1,
        )


def test_feature_flag_repository_round_trips_org_override():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    flags = DynamoFeatureFlagRepository(dynamodb_resource=resource)

    stored = flags.put(
        FeatureFlagRecord(
            organization_id="org_1",
            flag_key=FeatureFlagKey.ENABLE_CANDID,
            enabled=True,
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    loaded = flags.get("org_1", "enable_candid")
    listed = flags.list_for_organization("org_1")

    assert stored.flag_key is FeatureFlagKey.ENABLE_CANDID
    assert loaded is not None
    assert loaded.enabled is True
    assert len(listed) == 1
    assert listed[0].flag_key is FeatureFlagKey.ENABLE_CANDID


def test_feature_flag_service_resolves_plan_defaults_and_overrides():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    plans = DynamoPlanRepository(dynamodb_resource=resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=resource)
    flags = DynamoFeatureFlagRepository(dynamodb_resource=resource)
    subscription_service = SubscriptionService(
        organizations=organizations,
        plans=plans,
        subscriptions=subscriptions,
    )
    feature_service = FeatureFlagService(
        organizations=organizations,
        subscriptions=subscriptions,
        flags=flags,
        subscription_service=subscription_service,
    )

    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    subscription_service.upsert_subscription(
        organization_id="org_1",
        plan_id="growth",
        billing_cycle_start="2026-03-28T00:00:00+00:00",
        billing_cycle_end="2026-04-27T00:00:00+00:00",
    )

    assert PLAN_DEFAULT_FEATURE_FLAGS["growth"] == (
        FeatureFlagKey.ENABLE_BULK_LOOKUP,
        FeatureFlagKey.ENABLE_ADVANCED_REPORTING,
    )

    default_bulk = feature_service.resolve_flag(
        organization_id="org_1",
        flag_key=FeatureFlagKey.ENABLE_BULK_LOOKUP.value,
    )
    default_candid = feature_service.resolve_flag(
        organization_id="org_1",
        flag_key=FeatureFlagKey.ENABLE_CANDID.value,
    )
    override = feature_service.set_override(
        organization_id="org_1",
        flag_key=FeatureFlagKey.ENABLE_CANDID.value,
        enabled=True,
    )
    overridden = feature_service.resolve_flag(
        organization_id="org_1",
        flag_key=FeatureFlagKey.ENABLE_CANDID.value,
    )
    resolved = feature_service.list_resolved_flags(organization_id="org_1")

    assert isinstance(default_bulk, ResolvedFeatureFlag)
    assert default_bulk.plan_default is True
    assert default_bulk.enabled is True
    assert default_candid.plan_default is False
    assert default_candid.enabled is False
    assert override.enabled is True
    assert overridden.override_enabled is True
    assert overridden.enabled is True
    assert {item.flag_key.value for item in resolved} == {
        "enable_charity_navigator",
        "enable_candid",
        "enable_bulk_lookup",
        "enable_advanced_reporting",
    }


def test_feature_flag_service_applies_integration_overrides_for_premium_sources():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    plans = DynamoPlanRepository(dynamodb_resource=resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=resource)
    flags = DynamoFeatureFlagRepository(dynamodb_resource=resource)
    subscription_service = SubscriptionService(
        organizations=organizations,
        plans=plans,
        subscriptions=subscriptions,
    )
    feature_service = FeatureFlagService(
        organizations=organizations,
        subscriptions=subscriptions,
        flags=flags,
        subscription_service=subscription_service,
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Verify For Good Org",
            slug="verify-for-good-org",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    subscription_service.upsert_subscription(
        organization_id="org_1",
        plan_id="enterprise",
        billing_cycle_start="2026-03-28T00:00:00+00:00",
        billing_cycle_end="2026-04-27T00:00:00+00:00",
    )
    feature_service.set_override(
        organization_id="org_1",
        flag_key=FeatureFlagKey.ENABLE_CANDID.value,
        enabled=False,
    )

    context = feature_service.apply_evaluation_context_overrides(
        organization_id="org_1",
        context=EvaluationContext(),
    )

    assert context.setting_for("charity_navigator").enabled is True
    assert context.setting_for("candid").enabled is False
