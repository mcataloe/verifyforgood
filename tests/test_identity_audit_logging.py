from __future__ import annotations

import logging

from verification_platform.customer_accounts import (
    AuditEventType,
    AuditLogService,
    DynamoAuditLogRepository,
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
from verification_platform.identity_access import (
    AuthService,
    BcryptPasswordHasher,
    HmacBearerTokenCodec,
    IdentityProviderType,
    LocalPasswordIdentityProviderService,
    UserCreateRequest,
    UserLoginRequest,
)


class FailingAuditRepository:
    def create(self, record):
        raise RuntimeError("audit unavailable")

    def list_for_organization(self, organization_id: str):
        return []

    def list_identity_events(self):
        return []


def _audit_service_for(resource: FakeIdentityDynamoResource) -> AuditLogService:
    return AuditLogService(
        repository=DynamoAuditLogRepository(dynamodb_resource=resource),
        logger=logging.getLogger("test.identity.audit"),
    )


def test_register_user_creates_audit_event():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    auth_service = AuthService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
        audit_log_service=_audit_service_for(resource),
    )

    session = auth_service.register_user(
        UserCreateRequest(
            email="person@example.com",
            password="top-secret-password",
            full_name="Portal Person",
        )
    )
    audit_items = DynamoAuditLogRepository(dynamodb_resource=resource).list_identity_events()

    assert session.user.email == "person@example.com"
    assert len(audit_items) == 1
    assert audit_items[0].event_type is AuditEventType.USER_REGISTRATION
    assert audit_items[0].target_user_id == session.user.user_id
    assert audit_items[0].metadata["email"] == "person@example.com"


def test_organization_and_membership_changes_create_audit_events():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    audit_log_service = _audit_service_for(resource)
    auth_service = AuthService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
        audit_log_service=audit_log_service,
    )
    admin_session = auth_service.register_user(
        UserCreateRequest(
            email="admin@example.com",
            password="top-secret-password",
            full_name="Admin User",
        )
    )
    invitee_session = auth_service.register_user(
        UserCreateRequest(
            email="invitee@example.com",
            password="top-secret-password",
            full_name="Invitee User",
        )
    )
    organization_service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
        audit_log_service=audit_log_service,
    )
    membership_service = MembershipManagementService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
        invitations=DynamoInvitationRepository(dynamodb_resource=resource),
        audit_log_service=audit_log_service,
    )

    organization = organization_service.create_organization(
        creator_user_id=admin_session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org"),
    )
    invitation = membership_service.invite_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        request=InvitationCreateRequest(email="invitee@example.com", role="user"),
    )
    accepted = membership_service.accept_invitation(
        user_id=invitee_session.user.user_id,
        request=type("Accept", (), {"token": invitation.token})(),
    )
    updated = membership_service.update_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        member_user_id=invitee_session.user.user_id,
        request=MemberUpdateRequest(role="admin"),
    )
    removal = membership_service.remove_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        member_user_id=invitee_session.user.user_id,
    )
    audit_items = DynamoAuditLogRepository(dynamodb_resource=resource).list_for_organization(
        organization.organization_id
    )
    audit_by_type = {item.event_type: item for item in audit_items}
    event_types = {item.event_type for item in audit_items}

    assert organization.organization_name == "Verify For Good Org"
    assert accepted["membership"]["status"] == "active"
    assert updated.role == "admin"
    assert removal["removed_member_id"] == invitee_session.user.user_id
    assert event_types == {
        AuditEventType.ORGANIZATION_CREATION,
        AuditEventType.INVITATION_CREATION,
        AuditEventType.INVITATION_ACCEPTANCE,
        AuditEventType.MEMBERSHIP_ROLE_CHANGE,
        AuditEventType.MEMBER_REMOVAL,
    }
    assert audit_by_type[AuditEventType.ORGANIZATION_CREATION].metadata["slug"] == "verify-for-good-org"
    assert audit_by_type[AuditEventType.INVITATION_CREATION].metadata["email"] == "invitee@example.com"
    assert audit_by_type[AuditEventType.INVITATION_ACCEPTANCE].target_user_id == invitee_session.user.user_id
    assert audit_by_type[AuditEventType.MEMBERSHIP_ROLE_CHANGE].metadata["role"] == "admin"


def test_audit_failures_do_not_interrupt_primary_flows():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    failing_audit_service = AuditLogService(
        repository=FailingAuditRepository(),
        logger=logging.getLogger("test.identity.audit.failures"),
    )

    auth_service = AuthService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
        audit_log_service=failing_audit_service,
    )
    admin_session = auth_service.register_user(
        UserCreateRequest(
            email="admin@example.com",
            password="top-secret-password",
            full_name="Admin User",
        )
    )
    invitee_session = auth_service.register_user(
        UserCreateRequest(
            email="invitee@example.com",
            password="top-secret-password",
            full_name="Invitee User",
        )
    )
    organization_service = OrganizationService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
        audit_log_service=failing_audit_service,
    )
    membership_service = MembershipManagementService(
        users=DynamoUserRepository(dynamodb_resource=resource),
        organizations=DynamoOrganizationRepository(dynamodb_resource=resource),
        memberships=DynamoMembershipRepository(dynamodb_resource=resource),
        invitations=DynamoInvitationRepository(dynamodb_resource=resource),
        audit_log_service=failing_audit_service,
    )

    organization = organization_service.create_organization(
        creator_user_id=admin_session.user.user_id,
        request=OrganizationCreateRequest(name="Verify For Good Org"),
    )
    invitation = membership_service.invite_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        request=InvitationCreateRequest(email="invitee@example.com", role="user"),
    )
    accepted = membership_service.accept_invitation(
        user_id=invitee_session.user.user_id,
        request=type("Accept", (), {"token": invitation.token})(),
    )
    updated = membership_service.update_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        member_user_id=invitee_session.user.user_id,
        request=MemberUpdateRequest(role="admin"),
    )
    removed = membership_service.remove_member(
        organization_id=organization.organization_id,
        actor_user_id=admin_session.user.user_id,
        member_user_id=invitee_session.user.user_id,
    )

    assert organization.organization_id.startswith("org_")
    assert invitation.status == "pending"
    assert accepted["invitation"]["status"] == "accepted"
    assert updated.role == "admin"
    assert removed["removed_member_id"] == invitee_session.user.user_id


def test_auth_service_registers_local_password_users_with_provider_defaults():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)
    auth_service = AuthService(
        users=users,
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
    )

    session = auth_service.register_user(
        UserCreateRequest(
            email="person@example.com",
            password="top-secret-password",
            full_name="Portal Person",
        )
    )
    persisted = users.get(session.user.user_id)

    assert persisted is not None
    assert persisted.identity_provider_type is IdentityProviderType.LOCAL_PASSWORD
    assert persisted.external_subject_id is None
    assert persisted.password_hash is not None


def test_auth_service_login_uses_local_identity_provider_abstraction():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    users = DynamoUserRepository(dynamodb_resource=resource)
    auth_service = AuthService(
        users=users,
        password_hasher=BcryptPasswordHasher(),
        token_codec=HmacBearerTokenCodec(secret="test-secret"),
        identity_provider_services=(LocalPasswordIdentityProviderService(BcryptPasswordHasher()),),
    )

    registered = auth_service.register_user(
        UserCreateRequest(
            email="person@example.com",
            password="top-secret-password",
            full_name="Portal Person",
        )
    )
    logged_in = auth_service.login_user(
        UserLoginRequest(
            email="person@example.com",
            password="top-secret-password",
        )
    )

    assert logged_in.user.user_id == registered.user.user_id
    assert logged_in.user.email == "person@example.com"

