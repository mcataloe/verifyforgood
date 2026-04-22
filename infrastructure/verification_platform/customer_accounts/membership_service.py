from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .audit_logging import AuditEventType, AuditLogService
from .identity_models import InvitationRecord, InvitationStatus, MembershipRecord, MembershipRole, MembershipStatus
from .identity_repositories import InvitationRepository, MembershipRepository, OrganizationRepository, UserRepository


class MembershipManagementError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class MemberSummary:
    user_id: str
    email: str | None
    full_name: str | None
    role: str
    status: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class InvitationCreateRequest:
    email: str
    role: str


@dataclass(frozen=True)
class InvitationCreateResponse:
    invitation_id: str
    token: str
    email: str
    role: str
    status: str
    organization_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "invitation_id": self.invitation_id,
            "token": self.token,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "organization_id": self.organization_id,
        }


@dataclass(frozen=True)
class InvitationSummary:
    invitation_id: str
    email: str
    role: str
    status: str
    created_at: str
    expires_at: str
    accepted_at: str | None
    invited_by_user_id: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "invitation_id": self.invitation_id,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "accepted_at": self.accepted_at,
            "invited_by_user_id": self.invited_by_user_id,
        }


@dataclass(frozen=True)
class MemberUpdateRequest:
    role: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class InvitationAcceptRequest:
    token: str


class MembershipManagementService:
    def __init__(
        self,
        *,
        users: UserRepository,
        organizations: OrganizationRepository,
        memberships: MembershipRepository,
        invitations: InvitationRepository,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self._users = users
        self._organizations = organizations
        self._memberships = memberships
        self._invitations = invitations
        self._audit_log_service = audit_log_service

    def list_members(self, *, organization_id: str) -> list[MemberSummary]:
        if self._organizations.get(organization_id) is None:
            raise MembershipManagementError("Current organization was not found")
        results: list[MemberSummary] = []
        for membership in self._memberships.list_for_organization(organization_id):
            user = self._users.get(membership.user_id)
            results.append(
                MemberSummary(
                    user_id=membership.user_id,
                    email=(user.email if user else None),
                    full_name=(user.full_name if user else None),
                    role=membership.role.value,
                    status=membership.status.value,
                    created_at=membership.created_at,
                    updated_at=membership.updated_at,
                )
            )
        return results

    def list_invitations(self, *, organization_id: str) -> list[InvitationSummary]:
        if self._organizations.get(organization_id) is None:
            raise MembershipManagementError("Current organization was not found")
        return [
            InvitationSummary(
                invitation_id=invitation.invitation_id,
                email=invitation.email,
                role=invitation.role.value,
                status=_effective_invitation_status(invitation),
                created_at=invitation.created_at,
                expires_at=invitation.expires_at,
                accepted_at=invitation.accepted_at,
                invited_by_user_id=invitation.invited_by_user_id,
            )
            for invitation in self._invitations.list_for_organization(organization_id)
        ]

    def invite_member(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        request: InvitationCreateRequest,
    ) -> InvitationCreateResponse:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        normalized_email = _normalize_email(request.email)
        role = _validate_role(request.role)
        for membership in self._memberships.list_for_organization(organization_id):
            user = self._users.get(membership.user_id)
            if user and user.normalized_email == normalized_email and membership.status == MembershipStatus.ACTIVE:
                raise MembershipManagementError("User is already an active member of this organization")
        created_at = _utc_now()
        invitation = InvitationRecord(
            invitation_id=f"invite_{secrets.token_hex(16)}",
            organization_id=organization_id,
            email=normalized_email,
            normalized_email=normalized_email,
            token=f"invtok_{secrets.token_urlsafe(24)}",
            role=MembershipRole(role),
            status=InvitationStatus.PENDING,
            invited_by_user_id=actor_user_id,
            created_at=created_at,
            expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat(),
        )
        persisted = self._invitations.create(invitation)
        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.INVITATION_CREATION,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                metadata={
                    "invitation_id": persisted.invitation_id,
                    "email": persisted.email,
                    "role": persisted.role.value,
                    "status": persisted.status.value,
                    "expires_at": persisted.expires_at,
                },
            )
        return InvitationCreateResponse(
            invitation_id=persisted.invitation_id,
            token=persisted.token,
            email=persisted.email,
            role=persisted.role.value,
            status=persisted.status.value,
            organization_id=persisted.organization_id,
        )

    def update_member(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        member_user_id: str,
        request: MemberUpdateRequest,
    ) -> MemberSummary:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        role = _validate_role(request.role) if request.role is not None else None
        status = _validate_membership_status(request.status) if request.status is not None else None
        existing = self._memberships.get(organization_id, member_user_id)
        updated = self._memberships.update_membership(
            organization_id,
            member_user_id,
            role=role,
            status=status,
            updated_at=_utc_now(),
        )
        if updated is None:
            raise MembershipManagementError("Member was not found in the current organization")
        if (
            self._audit_log_service is not None
            and role is not None
            and existing is not None
            and existing.role.value != updated.role.value
        ):
            self._audit_log_service.record_event(
                event_type=AuditEventType.MEMBERSHIP_ROLE_CHANGE,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=member_user_id,
                metadata={
                    "role": updated.role.value,
                    "status": updated.status.value,
                },
            )
        user = self._users.get(updated.user_id)
        return MemberSummary(
            user_id=updated.user_id,
            email=(user.email if user else None),
            full_name=(user.full_name if user else None),
            role=updated.role.value,
            status=updated.status.value,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    def remove_member(self, *, organization_id: str, actor_user_id: str, member_user_id: str) -> dict[str, str]:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        removed = self._memberships.delete(organization_id, member_user_id)
        if not removed:
            raise MembershipManagementError("Member was not found in the current organization")
        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.MEMBER_REMOVAL,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=member_user_id,
                metadata={},
            )
        return {"removed_member_id": member_user_id, "organization_id": organization_id}

    def accept_invitation(self, *, user_id: str, request: InvitationAcceptRequest) -> dict[str, object]:
        user = self._users.get(user_id)
        if user is None:
            raise MembershipManagementError("Authenticated user was not found")
        invitation = self._invitations.get_by_token(request.token)
        if invitation is None:
            raise MembershipManagementError("Invitation token was not found")
        if invitation.status is not InvitationStatus.PENDING:
            raise MembershipManagementError("Invitation is not pending")
        if invitation.normalized_email != user.normalized_email:
            raise MembershipManagementError("Invitation email does not match the authenticated user")
        if datetime.fromisoformat(invitation.expires_at) <= datetime.now(timezone.utc):
            raise MembershipManagementError("Invitation has expired")
        existing = self._memberships.get(invitation.organization_id, user.user_id)
        if existing is not None:
            raise MembershipManagementError("User is already a member of this organization")
        membership = self._memberships.create(
            MembershipRecord(
                organization_id=invitation.organization_id,
                user_id=user.user_id,
                role=invitation.role,
                status=MembershipStatus.ACTIVE,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
        )
        accepted = self._invitations.mark_accepted(invitation.token, accepted_at=_utc_now())
        if accepted is None:
            raise MembershipManagementError("Invitation token was not found")
        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.INVITATION_ACCEPTANCE,
                actor_user_id=user.user_id,
                organization_id=invitation.organization_id,
                target_user_id=user.user_id,
                metadata={
                    "invitation_id": accepted.invitation_id,
                    "email": accepted.email,
                    "role": accepted.role.value,
                    "status": accepted.status.value,
                },
            )
        organization = self._organizations.get(invitation.organization_id)
        return {
            "invitation": {
                "invitation_id": accepted.invitation_id,
                "token": accepted.token,
                "email": accepted.email,
                "role": accepted.role.value,
                "status": accepted.status.value,
                "organization_id": accepted.organization_id,
            },
            "membership": {
                "user_id": membership.user_id,
                "role": membership.role.value,
                "status": membership.status.value,
            },
            "organization": {
                "organization_id": invitation.organization_id,
                "organization_name": organization.name if organization else invitation.organization_id,
                "account_id": invitation.organization_id,
                "workspace_id": invitation.organization_id,
            },
        }

    def _require_admin(self, *, organization_id: str, user_id: str) -> None:
        membership = self._memberships.get(organization_id, user_id)
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise MembershipManagementError("Active membership is required for this organization")
        if membership.role != MembershipRole.ADMIN:
            raise MembershipManagementError("Only organization admins may modify membership state")


def _normalize_email(email: str) -> str:
    candidate = str(email or "").strip().lower()
    if not candidate or "@" not in candidate:
        raise MembershipManagementError("email must be a valid email address")
    return candidate


def _validate_role(role: str) -> str:
    try:
        return MembershipRole(str(role or "").strip().lower()).value
    except Exception as exc:  # noqa: BLE001
        raise MembershipManagementError("role must be one of: admin, user") from exc


def _validate_membership_status(status: str) -> str:
    try:
        return MembershipStatus(str(status or "").strip().lower()).value
    except Exception as exc:  # noqa: BLE001
        raise MembershipManagementError("status must be one of: active, invited, suspended") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _effective_invitation_status(invitation: InvitationRecord) -> str:
    if invitation.status == InvitationStatus.PENDING and datetime.fromisoformat(invitation.expires_at) <= datetime.now(timezone.utc):
        return InvitationStatus.EXPIRED.value
    return invitation.status.value
