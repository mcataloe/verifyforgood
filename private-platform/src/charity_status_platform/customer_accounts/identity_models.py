from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MembershipRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class ApiKeyStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    email: str
    normalized_email: str
    full_name: str | None
    created_at: str
    updated_at: str
    password_hash: str | None = None


@dataclass(frozen=True)
class OrganizationRecord:
    organization_id: str
    name: str
    slug: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class MembershipRecord:
    organization_id: str
    user_id: str
    role: MembershipRole
    status: MembershipStatus
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class InvitationRecord:
    invitation_id: str
    organization_id: str
    email: str
    normalized_email: str
    token: str
    role: MembershipRole
    status: InvitationStatus
    invited_by_user_id: str | None
    created_at: str
    expires_at: str
    accepted_at: str | None = None


@dataclass(frozen=True)
class ApiKeyRecord:
    key_id: str
    organization_id: str
    hashed_key_value: str
    display_name: str
    created_at: str
    created_by_user_id: str
    status: ApiKeyStatus
    last_used_at: str | None = None


@dataclass(frozen=True)
class PlanRecord:
    plan_id: str
    plan_name: str
    monthly_price: int
    feature_flags: tuple[str, ...]
    request_limit: int
    description: str


@dataclass(frozen=True)
class SubscriptionRecord:
    subscription_id: str
    organization_id: str
    plan_id: str
    status: SubscriptionStatus
    billing_cycle_start: str
    billing_cycle_end: str
    created_at: str
