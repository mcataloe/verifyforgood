from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from .audit_logging import AuditEventType, AuditLogService
from .identity_models import MembershipRecord, MembershipRole, MembershipStatus, OrganizationRecord
from .identity_repositories import (
    DuplicateMembershipError,
    DuplicateOrganizationSlugError,
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)


class OrganizationBootstrapValidationError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class OrganizationCreateRequest:
    name: str
    slug: str | None = None


@dataclass(frozen=True)
class OrganizationContextResponse:
    organization_id: str
    organization_name: str
    slug: str
    account_id: str
    workspace_id: str
    membership: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "slug": self.slug,
            "account_id": self.account_id,
            "workspace_id": self.workspace_id,
            "membership": dict(self.membership),
        }


class OrganizationService:
    def __init__(
        self,
        *,
        users: UserRepository,
        organizations: OrganizationRepository,
        memberships: MembershipRepository,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self._users = users
        self._organizations = organizations
        self._memberships = memberships
        self._audit_log_service = audit_log_service

    def create_organization(
        self,
        *,
        creator_user_id: str,
        request: OrganizationCreateRequest,
    ) -> OrganizationContextResponse:
        creator = self._users.get(creator_user_id)
        if creator is None:
            raise OrganizationBootstrapValidationError("Authenticated user was not found")

        organization_name = _validate_name(request.name)
        slug = _resolve_slug(request.slug, organization_name)
        if self._organizations.get_by_slug(slug) is not None:
            raise OrganizationBootstrapValidationError("Organization slug is already in use")

        created_at = _utc_now()
        organization_id = f"org_{secrets.token_hex(16)}"
        organization = OrganizationRecord(
            organization_id=organization_id,
            name=organization_name,
            slug=slug,
            created_at=created_at,
            updated_at=created_at,
        )
        try:
            persisted_organization = self._organizations.create(organization)
        except DuplicateOrganizationSlugError:
            raise OrganizationBootstrapValidationError("Organization slug is already in use") from None

        membership = MembershipRecord(
            organization_id=persisted_organization.organization_id,
            user_id=creator.user_id,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at,
        )
        try:
            persisted_membership = self._memberships.create(membership)
        except DuplicateMembershipError:
            raise OrganizationBootstrapValidationError("Bootstrap membership already exists for this user") from None

        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.ORGANIZATION_CREATION,
                actor_user_id=creator.user_id,
                organization_id=persisted_organization.organization_id,
                target_user_id=creator.user_id,
                metadata={
                    "organization_name": persisted_organization.name,
                    "slug": persisted_organization.slug,
                    "bootstrap_role": persisted_membership.role.value,
                    "bootstrap_status": persisted_membership.status.value,
                },
            )

        return OrganizationContextResponse(
            organization_id=persisted_organization.organization_id,
            organization_name=persisted_organization.name,
            slug=persisted_organization.slug,
            account_id=persisted_organization.organization_id,
            workspace_id=persisted_organization.organization_id,
            membership={
                "user_id": persisted_membership.user_id,
                "role": persisted_membership.role.value,
                "status": persisted_membership.status.value,
            },
        )


def _validate_name(name: str) -> str:
    candidate = str(name or "").strip()
    if len(candidate) < 2:
        raise OrganizationBootstrapValidationError("name must be at least 2 characters")
    return candidate


def _resolve_slug(slug: str | None, organization_name: str) -> str:
    candidate = str(slug if slug is not None else organization_name).strip().lower()
    slug_value = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
    if len(slug_value) < 2:
        raise OrganizationBootstrapValidationError("slug must contain at least 2 alphanumeric characters")
    return slug_value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
