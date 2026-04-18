from __future__ import annotations

from typing import Protocol

from .identity_models import ApiKeyRecord, FeatureFlagRecord, InvitationRecord, MembershipRecord, OrganizationRecord, PlanRecord, SubscriptionRecord, UsageRecord, UserRecord


class IdentityRepositoryError(Exception):
    """Base error for identity repository operations."""


class DuplicateUserEmailError(IdentityRepositoryError):
    """Raised when attempting to create a user with an email already in use."""


class DuplicateMembershipError(IdentityRepositoryError):
    """Raised when attempting to create the same user/org membership twice."""


class DuplicateOrganizationSlugError(IdentityRepositoryError):
    """Raised when attempting to create an organization with an existing slug."""


class DuplicateApiKeyError(IdentityRepositoryError):
    """Raised when attempting to create an API key with an existing key id."""


class UserRepository(Protocol):
    def create(self, user: UserRecord) -> UserRecord:
        ...

    def get(self, user_id: int | str) -> UserRecord | None:
        ...

    def get_by_email(self, email: str) -> UserRecord | None:
        ...


class OrganizationRepository(Protocol):
    def create(self, organization: OrganizationRecord) -> OrganizationRecord:
        ...

    def get(self, organization_id: int | str) -> OrganizationRecord | None:
        ...

    def get_by_slug(self, slug: str) -> OrganizationRecord | None:
        ...

    def update_profile(
        self,
        organization_id: int | str,
        *,
        name: str,
        slug: str,
        contact_email: str | None,
        updated_at: str,
    ) -> OrganizationRecord | None:
        ...

    def soft_delete(
        self,
        organization_id: int | str,
        *,
        deleted_at: str,
        deleted_by_user_id: int | str,
    ) -> OrganizationRecord | None:
        ...


class MembershipRepository(Protocol):
    def create(self, membership: MembershipRecord) -> MembershipRecord:
        ...

    def get(self, organization_id: int | str, user_id: int | str) -> MembershipRecord | None:
        ...

    def list_for_organization(self, organization_id: int | str) -> list[MembershipRecord]:
        ...

    def list_for_user(self, user_id: int | str) -> list[MembershipRecord]:
        ...

    def update_role(self, organization_id: int | str, user_id: int | str, role: str) -> MembershipRecord | None:
        ...

    def update_membership(
        self,
        organization_id: int | str,
        user_id: int | str,
        *,
        role: str | None = None,
        status: str | None = None,
        updated_at: str,
    ) -> MembershipRecord | None:
        ...

    def delete(self, organization_id: int | str, user_id: int | str) -> bool:
        ...


class InvitationRepository(Protocol):
    def create(self, invitation: InvitationRecord) -> InvitationRecord:
        ...

    def get(self, organization_id: str, invitation_id: str) -> InvitationRecord | None:
        ...

    def list_for_organization(self, organization_id: str) -> list[InvitationRecord]:
        ...

    def get_by_token(self, token: str) -> InvitationRecord | None:
        ...

    def mark_accepted(self, token: str, accepted_at: str) -> InvitationRecord | None:
        ...


class ApiKeyRepository(Protocol):
    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord:
        ...

    def list_for_organization(self, organization_id: str) -> list[ApiKeyRecord]:
        ...

    def get_by_key_id(self, key_id: int | str) -> ApiKeyRecord | None:
        ...

    def revoke(self, organization_id: int | str, key_id: int | str, *, revoked_at: str | None = None) -> ApiKeyRecord | None:
        ...

    def touch_last_used(self, key_id: int | str, *, used_at: str) -> ApiKeyRecord | None:
        ...


class PlanRepository(Protocol):
    def get(self, plan_id: int | str) -> PlanRecord | None:
        ...

    def list_all(self) -> list[PlanRecord]:
        ...

    def seed_defaults(self, plans: list[PlanRecord]) -> None:
        ...


class SubscriptionRepository(Protocol):
    def put(self, subscription: SubscriptionRecord) -> SubscriptionRecord:
        ...

    def get_by_organization(self, organization_id: int | str) -> SubscriptionRecord | None:
        ...


class UsageRepository(Protocol):
    def increment(
        self,
        organization_id: str,
        metric_type: str,
        period_month: str,
        *,
        units: int,
        last_updated: str,
    ) -> UsageRecord:
        ...

    def get(self, organization_id: str, metric_type: str, period_month: str) -> UsageRecord | None:
        ...

    def list_for_period(self, organization_id: str, period_month: str) -> list[UsageRecord]:
        ...

    def put(self, record: UsageRecord) -> UsageRecord:
        ...


class FeatureFlagRepository(Protocol):
    def get(self, organization_id: str, flag_key: str) -> FeatureFlagRecord | None:
        ...

    def list_for_organization(self, organization_id: str) -> list[FeatureFlagRecord]:
        ...

    def put(self, record: FeatureFlagRecord) -> FeatureFlagRecord:
        ...
