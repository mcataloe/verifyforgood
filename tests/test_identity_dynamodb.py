from __future__ import annotations

import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


from charity_status_platform.customer_accounts import (  # noqa: E402
    DuplicateMembershipError,
    DuplicateUserEmailError,
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
    UserRecord,
)


def test_customer_accounts_exports_identity_phase_surface():
    import charity_status_platform.customer_accounts as customer_accounts

    assert customer_accounts.IDENTITY_TABLE_NAME == "identity"
    assert hasattr(customer_accounts, "UserRepository")
    assert hasattr(customer_accounts, "OrganizationRepository")
    assert hasattr(customer_accounts, "MembershipRepository")
    assert hasattr(customer_accounts, "InvitationRepository")
    assert hasattr(customer_accounts, "DynamoUserRepository")
    assert hasattr(customer_accounts, "DynamoOrganizationRepository")
    assert hasattr(customer_accounts, "DynamoMembershipRepository")
    assert hasattr(customer_accounts, "DynamoInvitationRepository")
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
