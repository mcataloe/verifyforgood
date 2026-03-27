from __future__ import annotations

from copy import deepcopy
from typing import Any

import boto3

from .identity_models import (
    InvitationRecord,
    InvitationStatus,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationRecord,
    UserRecord,
)
from .identity_repositories import (
    DuplicateMembershipError,
    DuplicateOrganizationSlugError,
    DuplicateUserEmailError,
)

IDENTITY_TABLE_NAME = "identity"
EMAIL_LOOKUP_INDEX = "email_lookup"
USER_MEMBERSHIPS_INDEX = "user_memberships"
INVITATION_TOKEN_INDEX = "invitation_token_lookup"
ORGANIZATION_SLUG_LOOKUP_INDEX = "organization_slug_lookup"


class DynamoUserRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def create(self, user: UserRecord) -> UserRecord:
        existing = self.get_by_email(user.email)
        if existing is not None and existing.user_id != user.user_id:
            raise DuplicateUserEmailError(f"User email already exists: {user.email}")
        self._table.put_item(
            Item=_user_item(user),
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
        return user

    def get(self, user_id: str) -> UserRecord | None:
        response = self._table.get_item(Key={"pk": _user_pk(user_id), "sk": "USER"})
        item = response.get("Item")
        if item is None:
            return None
        return _user_from_item(item)

    def get_by_email(self, email: str) -> UserRecord | None:
        normalized_email = _normalize_email(email)
        response = self._table.query(
            IndexName=EMAIL_LOOKUP_INDEX,
            KeyConditionExpression="gsi1pk = :gsi1pk",
            ExpressionAttributeValues={":gsi1pk": f"EMAIL#{normalized_email}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _user_from_item(items[0])


class DynamoOrganizationRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def create(self, organization: OrganizationRecord) -> OrganizationRecord:
        existing = self.get_by_slug(organization.slug)
        if existing is not None and existing.organization_id != organization.organization_id:
            raise DuplicateOrganizationSlugError(f"Organization slug already exists: {organization.slug}")
        self._table.put_item(
            Item=_organization_item(organization),
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
        return organization

    def get(self, organization_id: str) -> OrganizationRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": "ORG"})
        item = response.get("Item")
        if item is None:
            return None
        return _organization_from_item(item)

    def get_by_slug(self, slug: str) -> OrganizationRecord | None:
        normalized_slug = _normalize_slug(slug)
        response = self._table.query(
            IndexName=ORGANIZATION_SLUG_LOOKUP_INDEX,
            KeyConditionExpression="gsi4pk = :gsi4pk",
            ExpressionAttributeValues={":gsi4pk": f"ORGSLUG#{normalized_slug}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _organization_from_item(items[0])


class DynamoMembershipRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def create(self, membership: MembershipRecord) -> MembershipRecord:
        try:
            self._table.put_item(
                Item=_membership_item(membership),
                ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ConditionalCheckFailedException":
                raise DuplicateMembershipError(
                    f"Membership already exists for user {membership.user_id} in organization {membership.organization_id}"
                ) from exc
            raise
        return membership

    def get(self, organization_id: str, user_id: str) -> MembershipRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": f"MEMBERSHIP#{user_id}"})
        item = response.get("Item")
        if item is None:
            return None
        return _membership_from_item(item)

    def list_for_organization(self, organization_id: str) -> list[MembershipRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _organization_pk(organization_id), ":prefix": "MEMBERSHIP#"},
        )
        items = response.get("Items") or []
        return [_membership_from_item(item) for item in items if item.get("type") == "MEMBERSHIP"]

    def list_for_user(self, user_id: str) -> list[MembershipRecord]:
        response = self._table.query(
            IndexName=USER_MEMBERSHIPS_INDEX,
            KeyConditionExpression="gsi2pk = :gsi2pk",
            ExpressionAttributeValues={":gsi2pk": f"USER#{user_id}"},
        )
        items = response.get("Items") or []
        return [_membership_from_item(item) for item in items if item.get("type") == "MEMBERSHIP"]

    def update_role(self, organization_id: str, user_id: str, role: str) -> MembershipRecord | None:
        return self.update_membership(
            organization_id,
            user_id,
            role=role,
            updated_at=self.get(organization_id, user_id).updated_at if self.get(organization_id, user_id) else "",
        )

    def update_membership(
        self,
        organization_id: str,
        user_id: str,
        *,
        role: str | None = None,
        status: str | None = None,
        updated_at: str,
    ) -> MembershipRecord | None:
        existing = self.get(organization_id, user_id)
        if existing is None:
            return None
        updated = MembershipRecord(
            organization_id=existing.organization_id,
            user_id=existing.user_id,
            role=MembershipRole(role or existing.role.value),
            status=MembershipStatus(status or existing.status.value),
            created_at=existing.created_at,
            updated_at=updated_at,
        )
        self._table.put_item(Item=_membership_item(updated))
        return updated

    def delete(self, organization_id: str, user_id: str) -> bool:
        existing = self.get(organization_id, user_id)
        if existing is None:
            return False
        if hasattr(self._table, "delete_item"):
            self._table.delete_item(Key={"pk": _organization_pk(organization_id), "sk": f"MEMBERSHIP#{user_id}"})
        else:
            try:
                del self._table._items[(_organization_pk(organization_id), f"MEMBERSHIP#{user_id}")]
            except Exception:
                return False
        return True


class DynamoInvitationRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def create(self, invitation: InvitationRecord) -> InvitationRecord:
        self._table.put_item(
            Item=_invitation_item(invitation),
            ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
        )
        return invitation

    def get(self, organization_id: str, invitation_id: str) -> InvitationRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": f"INVITATION#{invitation_id}"})
        item = response.get("Item")
        if item is None:
            return None
        return _invitation_from_item(item)

    def get_by_token(self, token: str) -> InvitationRecord | None:
        response = self._table.query(
            IndexName=INVITATION_TOKEN_INDEX,
            KeyConditionExpression="gsi3pk = :gsi3pk",
            ExpressionAttributeValues={":gsi3pk": f"INVITATIONTOKEN#{token}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _invitation_from_item(items[0])

    def mark_accepted(self, token: str, accepted_at: str) -> InvitationRecord | None:
        existing = self.get_by_token(token)
        if existing is None:
            return None
        updated = InvitationRecord(
            invitation_id=existing.invitation_id,
            organization_id=existing.organization_id,
            email=existing.email,
            normalized_email=existing.normalized_email,
            token=existing.token,
            role=existing.role,
            status=InvitationStatus.ACCEPTED,
            invited_by_user_id=existing.invited_by_user_id,
            created_at=existing.created_at,
            expires_at=existing.expires_at,
            accepted_at=accepted_at,
        )
        self._table.put_item(Item=_invitation_item(updated))
        return updated


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _organization_pk(organization_id: str) -> str:
    return f"ORG#{organization_id}"


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _normalize_slug(slug: str) -> str:
    return str(slug or "").strip().lower()


def _user_item(user: UserRecord) -> dict[str, Any]:
    return {
        "pk": _user_pk(user.user_id),
        "sk": "USER",
        "type": "USER",
        "user_id": user.user_id,
        "email": user.email,
        "normalized_email": user.normalized_email,
        "full_name": user.full_name,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "password_hash": user.password_hash,
        "gsi1pk": f"EMAIL#{user.normalized_email}",
        "gsi1sk": _user_pk(user.user_id),
    }


def _organization_item(organization: OrganizationRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(organization.organization_id),
        "sk": "ORG",
        "type": "ORG",
        "organization_id": organization.organization_id,
        "name": organization.name,
        "slug": organization.slug,
        "created_at": organization.created_at,
        "updated_at": organization.updated_at,
        "gsi4pk": f"ORGSLUG#{organization.slug}",
        "gsi4sk": _organization_pk(organization.organization_id),
    }


def _membership_item(membership: MembershipRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(membership.organization_id),
        "sk": f"MEMBERSHIP#{membership.user_id}",
        "type": "MEMBERSHIP",
        "organization_id": membership.organization_id,
        "user_id": membership.user_id,
        "role": membership.role.value,
        "status": membership.status.value,
        "created_at": membership.created_at,
        "updated_at": membership.updated_at,
        "gsi2pk": f"USER#{membership.user_id}",
        "gsi2sk": f"ORG#{membership.organization_id}",
    }


def _invitation_item(invitation: InvitationRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(invitation.organization_id),
        "sk": f"INVITATION#{invitation.invitation_id}",
        "type": "INVITATION",
        "organization_id": invitation.organization_id,
        "invitation_id": invitation.invitation_id,
        "email": invitation.email,
        "normalized_email": invitation.normalized_email,
        "token": invitation.token,
        "role": invitation.role.value,
        "status": invitation.status.value,
        "invited_by_user_id": invitation.invited_by_user_id,
        "created_at": invitation.created_at,
        "expires_at": invitation.expires_at,
        "accepted_at": invitation.accepted_at,
        "gsi3pk": f"INVITATIONTOKEN#{invitation.token}",
        "gsi3sk": f"ORG#{invitation.organization_id}",
    }


def _user_from_item(item: dict[str, Any]) -> UserRecord:
    return UserRecord(
        user_id=str(item.get("user_id") or ""),
        email=str(item.get("email") or ""),
        normalized_email=str(item.get("normalized_email") or ""),
        full_name=_optional_string(item.get("full_name")),
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
        password_hash=_optional_string(item.get("password_hash")),
    )


def _organization_from_item(item: dict[str, Any]) -> OrganizationRecord:
    return OrganizationRecord(
        organization_id=str(item.get("organization_id") or ""),
        name=str(item.get("name") or ""),
        slug=str(item.get("slug") or ""),
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
    )


def _membership_from_item(item: dict[str, Any]) -> MembershipRecord:
    return MembershipRecord(
        organization_id=str(item.get("organization_id") or ""),
        user_id=str(item.get("user_id") or ""),
        role=MembershipRole(str(item.get("role") or MembershipRole.USER.value)),
        status=MembershipStatus(str(item.get("status") or MembershipStatus.ACTIVE.value)),
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
    )


def _invitation_from_item(item: dict[str, Any]) -> InvitationRecord:
    return InvitationRecord(
        invitation_id=str(item.get("invitation_id") or ""),
        organization_id=str(item.get("organization_id") or ""),
        email=str(item.get("email") or ""),
        normalized_email=str(item.get("normalized_email") or ""),
        token=str(item.get("token") or ""),
        role=MembershipRole(str(item.get("role") or MembershipRole.USER.value)),
        status=InvitationStatus(str(item.get("status") or InvitationStatus.PENDING.value)),
        invited_by_user_id=_optional_string(item.get("invited_by_user_id")),
        created_at=str(item.get("created_at") or ""),
        expires_at=str(item.get("expires_at") or ""),
        accepted_at=_optional_string(item.get("accepted_at")),
    )


def _optional_string(value: Any) -> str | None:
    candidate = str(value or "").strip()
    return candidate or None


class ConditionalCheckFailedException(Exception):
    """Local exception used by the in-memory fake when a conditional write fails."""


class FakeIdentityDynamoTable:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict[str, Any]] = {}

    def put_item(self, Item, ConditionExpression=None):  # noqa: N803
        key = (Item["pk"], Item["sk"])
        if ConditionExpression == "attribute_not_exists(pk) AND attribute_not_exists(sk)" and key in self._items:
            raise ConditionalCheckFailedException("Conditional write failed")
        self._items[key] = deepcopy(Item)
        return {}

    def get_item(self, Key):  # noqa: N803
        item = self._items.get((Key["pk"], Key["sk"]))
        return {"Item": deepcopy(item)} if item is not None else {}

    def delete_item(self, Key):  # noqa: N803
        self._items.pop((Key["pk"], Key["sk"]), None)
        return {}

    def query(self, IndexName=None, KeyConditionExpression=None, ExpressionAttributeValues=None, Limit=None):  # noqa: N803
        values = ExpressionAttributeValues or {}
        items = list(self._items.values())
        if IndexName == EMAIL_LOOKUP_INDEX:
            matches = [item for item in items if item.get("gsi1pk") == values.get(":gsi1pk")]
            matches.sort(key=lambda item: str(item.get("gsi1sk") or ""))
        elif IndexName == USER_MEMBERSHIPS_INDEX:
            matches = [item for item in items if item.get("gsi2pk") == values.get(":gsi2pk")]
            matches.sort(key=lambda item: str(item.get("gsi2sk") or ""))
        elif IndexName == INVITATION_TOKEN_INDEX:
            matches = [item for item in items if item.get("gsi3pk") == values.get(":gsi3pk")]
            matches.sort(key=lambda item: str(item.get("gsi3sk") or ""))
        elif IndexName == ORGANIZATION_SLUG_LOOKUP_INDEX:
            matches = [item for item in items if item.get("gsi4pk") == values.get(":gsi4pk")]
            matches.sort(key=lambda item: str(item.get("gsi4sk") or ""))
        elif KeyConditionExpression == "pk = :pk AND begins_with(sk, :prefix)":
            matches = [
                item
                for item in items
                if item.get("pk") == values.get(":pk") and str(item.get("sk") or "").startswith(str(values.get(":prefix") or ""))
            ]
            matches.sort(key=lambda item: str(item.get("sk") or ""))
        else:
            matches = [item for item in items if item.get("pk") == values.get(":pk")]
            matches.sort(key=lambda item: str(item.get("sk") or ""))
        if Limit is not None:
            matches = matches[:Limit]
        return {"Items": [deepcopy(item) for item in matches]}


class FakeIdentityDynamoResource:
    def __init__(self, table: FakeIdentityDynamoTable) -> None:
        self._table = table

    def Table(self, name: str):  # noqa: N802
        return self._table
