from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .identity_models import MembershipStatus
from .identity_repositories import MembershipRepository, OrganizationRepository
from .organization_service import OrganizationContextResponse


@dataclass(frozen=True)
class OrganizationContextService:
    organizations: OrganizationRepository
    memberships: MembershipRepository

    def resolve_for_user(
        self,
        *,
        user_id: str,
    ) -> OrganizationContextResponse | None:
        active_memberships = [
            membership
            for membership in self.memberships.list_for_user(user_id)
            if membership.status is MembershipStatus.ACTIVE
        ]
        if not active_memberships:
            return None

        active_memberships = sorted(
            active_memberships,
            key=lambda membership: membership.organization_id,
        )
        active_memberships.sort(
            key=lambda membership: _timestamp_sort_value(membership.updated_at),
            reverse=True,
        )

        membership = active_memberships[0]
        organization = self.organizations.get(membership.organization_id)
        if organization is None:
            return None

        return OrganizationContextResponse(
            organization_id=organization.organization_id,
            organization_name=organization.name,
            slug=organization.slug,
            account_id=organization.organization_id,
            workspace_id=organization.organization_id,
            membership={
                "user_id": membership.user_id,
                "role": membership.role.value,
                "status": membership.status.value,
            },
        )


def _timestamp_sort_value(value: str) -> float:
    candidate = str(value or "").strip()
    if not candidate:
        return 0.0

    normalized = candidate.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp()
    except ValueError:
        return 0.0
