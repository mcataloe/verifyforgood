from __future__ import annotations

from typing import Protocol

from .identity_models import InvitationRecord, MembershipRecord, OrganizationRecord, UserRecord


class IdentityRepositoryError(Exception):
    """Base error for identity repository operations."""


class DuplicateUserEmailError(IdentityRepositoryError):
    """Raised when attempting to create a user with an email already in use."""


class DuplicateMembershipError(IdentityRepositoryError):
    """Raised when attempting to create the same user/org membership twice."""


class DuplicateOrganizationSlugError(IdentityRepositoryError):
    """Raised when attempting to create an organization with an existing slug."""


class UserRepository(Protocol):
    def create(self, user: UserRecord) -> UserRecord:
        ...

    def get(self, user_id: str) -> UserRecord | None:
        ...

    def get_by_email(self, email: str) -> UserRecord | None:
        ...


class OrganizationRepository(Protocol):
    def create(self, organization: OrganizationRecord) -> OrganizationRecord:
        ...

    def get(self, organization_id: str) -> OrganizationRecord | None:
        ...

    def get_by_slug(self, slug: str) -> OrganizationRecord | None:
        ...


class MembershipRepository(Protocol):
    def create(self, membership: MembershipRecord) -> MembershipRecord:
        ...

    def get(self, organization_id: str, user_id: str) -> MembershipRecord | None:
        ...

    def list_for_organization(self, organization_id: str) -> list[MembershipRecord]:
        ...

    def list_for_user(self, user_id: str) -> list[MembershipRecord]:
        ...

    def update_role(self, organization_id: str, user_id: str, role: str) -> MembershipRecord | None:
        ...

    def update_membership(
        self,
        organization_id: str,
        user_id: str,
        *,
        role: str | None = None,
        status: str | None = None,
        updated_at: str,
    ) -> MembershipRecord | None:
        ...

    def delete(self, organization_id: str, user_id: str) -> bool:
        ...


class InvitationRepository(Protocol):
    def create(self, invitation: InvitationRecord) -> InvitationRecord:
        ...

    def get(self, organization_id: str, invitation_id: str) -> InvitationRecord | None:
        ...

    def get_by_token(self, token: str) -> InvitationRecord | None:
        ...

    def mark_accepted(self, token: str, accepted_at: str) -> InvitationRecord | None:
        ...
