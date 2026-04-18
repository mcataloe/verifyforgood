from __future__ import annotations

from copy import deepcopy
import secrets
from typing import Any

import boto3

from .identity_models import (
    ApiKeyRecord,
    ApiKeyStatus,
    FeatureFlagKey,
    FeatureFlagRecord,
    IdentityProviderType,
    InvitationRecord,
    InvitationStatus,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationRecord,
    PlanRecord,
    SubscriptionRecord,
    SubscriptionStatus,
    UsageMetricType,
    UsageRecord,
    UserRecord,
)
from .identity_repositories import (
    DuplicateApiKeyError,
    DuplicateMembershipError,
    DuplicateOrganizationSlugError,
    DuplicateUserEmailError,
)

IDENTITY_TABLE_NAME = "identity"
EMAIL_LOOKUP_INDEX = "email_lookup"
USER_MEMBERSHIPS_INDEX = "user_memberships"
INVITATION_TOKEN_INDEX = "invitation_token_lookup"
ORGANIZATION_SLUG_LOOKUP_INDEX = "organization_slug_lookup"
API_KEY_LOOKUP_INDEX = "api_key_lookup"
PLAN_LOOKUP_INDEX = "plan_lookup"


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
        organization = _organization_from_item(item)
        if organization.deleted_at:
            return None
        return organization

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
        organization = _organization_from_item(items[0])
        if organization.deleted_at:
            return None
        return organization

    def update_profile(
        self,
        organization_id: str,
        *,
        name: str,
        slug: str,
        contact_email: str | None,
        updated_at: str,
    ) -> OrganizationRecord | None:
        existing = self.get(organization_id)
        if existing is None:
            return None
        normalized_slug = _normalize_slug(slug)
        existing_with_slug = self.get_by_slug(normalized_slug)
        if (
            existing_with_slug is not None
            and existing_with_slug.organization_id != existing.organization_id
        ):
            raise DuplicateOrganizationSlugError(
                f"Organization slug already exists: {normalized_slug}"
            )
        updated = OrganizationRecord(
            organization_id=existing.organization_id,
            name=name,
            slug=normalized_slug,
            created_at=existing.created_at,
            updated_at=updated_at,
            contact_email=contact_email,
            deleted_at=existing.deleted_at,
            deleted_by_user_id=existing.deleted_by_user_id,
        )
        self._table.put_item(Item=_organization_item(updated))
        return updated

    def soft_delete(
        self,
        organization_id: str,
        *,
        deleted_at: str,
        deleted_by_user_id: str,
    ) -> OrganizationRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": "ORG"})
        item = response.get("Item")
        if item is None:
            return None
        existing = _organization_from_item(item)
        updated = OrganizationRecord(
            organization_id=existing.organization_id,
            name=existing.name,
            slug=existing.slug,
            created_at=existing.created_at,
            updated_at=deleted_at,
            contact_email=existing.contact_email,
            deleted_at=deleted_at,
            deleted_by_user_id=deleted_by_user_id,
        )
        self._table.put_item(Item=_organization_item(updated))
        return updated


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

    def list_for_organization(self, organization_id: str) -> list[InvitationRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _organization_pk(organization_id), ":prefix": "INVITATION#"},
        )
        items = response.get("Items") or []
        return [_invitation_from_item(item) for item in items if item.get("type") == "INVITATION"]

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


class DynamoApiKeyRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord:
        persisted = api_key if api_key.key_id is not None else ApiKeyRecord(
            key_id=f"key_{secrets.token_hex(16)}",
            organization_id=api_key.organization_id,
            hashed_key_value=api_key.hashed_key_value,
            display_name=api_key.display_name,
            created_at=api_key.created_at,
            created_by_user_id=api_key.created_by_user_id,
            status=api_key.status,
            last_used_at=api_key.last_used_at,
        )
        try:
            self._table.put_item(
                Item=_api_key_item(persisted),
                ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ConditionalCheckFailedException":
                raise DuplicateApiKeyError(f"API key already exists: {persisted.key_id}") from exc
            raise
        return persisted

    def list_for_organization(self, organization_id: str) -> list[ApiKeyRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _organization_pk(organization_id), ":prefix": "APIKEY#"},
        )
        items = response.get("Items") or []
        return [_api_key_from_item(item) for item in items if item.get("type") == "API_KEY"]

    def get_by_key_id(self, key_id: str) -> ApiKeyRecord | None:
        response = self._table.query(
            IndexName=API_KEY_LOOKUP_INDEX,
            KeyConditionExpression="gsi5pk = :gsi5pk",
            ExpressionAttributeValues={":gsi5pk": f"APIKEY#{key_id}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _api_key_from_item(items[0])

    def revoke(self, organization_id: str, key_id: str, *, revoked_at: str | None = None) -> ApiKeyRecord | None:
        existing = self.get_by_key_id(key_id)
        if existing is None or existing.organization_id != organization_id:
            return None
        updated = ApiKeyRecord(
            key_id=existing.key_id,
            organization_id=existing.organization_id,
            hashed_key_value=existing.hashed_key_value,
            display_name=existing.display_name,
            created_at=existing.created_at,
            created_by_user_id=existing.created_by_user_id,
            status=ApiKeyStatus.REVOKED,
            last_used_at=existing.last_used_at,
        )
        self._table.put_item(Item=_api_key_item(updated))
        return updated

    def touch_last_used(self, key_id: str, *, used_at: str) -> ApiKeyRecord | None:
        existing = self.get_by_key_id(key_id)
        if existing is None:
            return None
        updated = ApiKeyRecord(
            key_id=existing.key_id,
            organization_id=existing.organization_id,
            hashed_key_value=existing.hashed_key_value,
            display_name=existing.display_name,
            created_at=existing.created_at,
            created_by_user_id=existing.created_by_user_id,
            status=existing.status,
            last_used_at=used_at,
        )
        self._table.put_item(Item=_api_key_item(updated))
        return updated


class DynamoPlanRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def get(self, plan_id: int | str) -> PlanRecord | None:
        plan_key = _normalize_plan_key(plan_id)
        response = self._table.get_item(Key={"pk": _plan_pk(plan_key), "sk": "PLAN"})
        item = response.get("Item")
        if item is None:
            return None
        return _plan_from_item(item)

    def list_all(self) -> list[PlanRecord]:
        response = self._table.query(
            IndexName=PLAN_LOOKUP_INDEX,
            KeyConditionExpression="gsi6pk = :gsi6pk",
            ExpressionAttributeValues={":gsi6pk": "PLANCATALOG"},
        )
        items = response.get("Items") or []
        return [_plan_from_item(item) for item in items if item.get("type") == "PLAN"]

    def seed_defaults(self, plans: list[PlanRecord]) -> None:
        for plan in plans:
            if self.get(plan.plan_code) is not None:
                continue
            self._table.put_item(Item=_plan_item(plan))


class DynamoSubscriptionRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def put(self, subscription: SubscriptionRecord) -> SubscriptionRecord:
        persisted = subscription if subscription.subscription_id is not None else SubscriptionRecord(
            subscription_id=f"sub_{secrets.token_hex(16)}",
            organization_id=subscription.organization_id,
            plan_id=subscription.plan_id,
            status=subscription.status,
            billing_cycle_start=subscription.billing_cycle_start,
            billing_cycle_end=subscription.billing_cycle_end,
            created_at=subscription.created_at,
            pending_plan_id=subscription.pending_plan_id,
            pending_plan_effective_at=subscription.pending_plan_effective_at,
            cancel_at_period_end=subscription.cancel_at_period_end,
            updated_at=subscription.updated_at,
            grace_period_ends_at=subscription.grace_period_ends_at,
            billing_status=subscription.billing_status,
        )
        self._table.put_item(Item=_subscription_item(persisted))
        return persisted

    def get_by_organization(self, organization_id: str) -> SubscriptionRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": "SUBSCRIPTION"})
        item = response.get("Item")
        if item is None:
            return None
        return _subscription_from_item(item)


class DynamoUsageRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def increment(
        self,
        organization_id: str,
        metric_type: str,
        period_month: str,
        *,
        units: int,
        last_updated: str,
    ) -> UsageRecord:
        normalized_units = max(0, int(units))
        if normalized_units <= 0:
            existing = self.get(organization_id, metric_type, period_month)
            if existing is not None:
                return existing
            record = UsageRecord(
                organization_id=organization_id,
                metric_type=UsageMetricType(metric_type),
                period_month=period_month,
                request_count=0,
                last_updated=last_updated,
            )
            self._table.put_item(Item=_usage_item(record))
            return record
        response = self._table.update_item(
            Key={"pk": _organization_pk(organization_id), "sk": _usage_sk(period_month, metric_type)},
            UpdateExpression=(
                "SET #type = if_not_exists(#type, :type), "
                "#organization_id = if_not_exists(#organization_id, :organization_id), "
                "#metric_type = if_not_exists(#metric_type, :metric_type), "
                "#period_month = if_not_exists(#period_month, :period_month), "
                "#request_count = if_not_exists(#request_count, :zero) + :units, "
                "#last_updated = :last_updated"
            ),
            ExpressionAttributeNames={
                "#type": "type",
                "#organization_id": "organization_id",
                "#metric_type": "metric_type",
                "#period_month": "period_month",
                "#request_count": "request_count",
                "#last_updated": "last_updated",
            },
            ExpressionAttributeValues={
                ":type": "USAGE_RECORD",
                ":organization_id": organization_id,
                ":metric_type": UsageMetricType(metric_type).value,
                ":period_month": period_month,
                ":zero": 0,
                ":units": normalized_units,
                ":last_updated": last_updated,
            },
            ReturnValues="ALL_NEW",
        )
        return _usage_from_item(response["Attributes"])

    def get(self, organization_id: str, metric_type: str, period_month: str) -> UsageRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": _usage_sk(period_month, metric_type)})
        item = response.get("Item")
        if item is None:
            return None
        return _usage_from_item(item)

    def list_for_period(self, organization_id: str, period_month: str) -> list[UsageRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _organization_pk(organization_id), ":prefix": f"USAGE#{period_month}#"},
        )
        items = response.get("Items") or []
        return [_usage_from_item(item) for item in items if item.get("type") == "USAGE_RECORD"]

    def put(self, record: UsageRecord) -> UsageRecord:
        self._table.put_item(Item=_usage_item(record))
        return record


class DynamoFeatureFlagRepository:
    def __init__(self, table_name: str = IDENTITY_TABLE_NAME, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def get(self, organization_id: str, flag_key: str) -> FeatureFlagRecord | None:
        response = self._table.get_item(Key={"pk": _organization_pk(organization_id), "sk": _feature_flag_sk(flag_key)})
        item = response.get("Item")
        if item is None:
            return None
        return _feature_flag_from_item(item)

    def list_for_organization(self, organization_id: str) -> list[FeatureFlagRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _organization_pk(organization_id), ":prefix": "FEATUREFLAG#"},
        )
        items = response.get("Items") or []
        return [_feature_flag_from_item(item) for item in items if item.get("type") == "FEATURE_FLAG"]

    def put(self, record: FeatureFlagRecord) -> FeatureFlagRecord:
        self._table.put_item(Item=_feature_flag_item(record))
        return record


def _user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def _organization_pk(organization_id: str) -> str:
    return f"ORG#{organization_id}"


def _plan_pk(plan_id: str) -> str:
    return f"PLAN#{plan_id}"


def _usage_sk(period_month: str, metric_type: str) -> str:
    return f"USAGE#{period_month}#{metric_type}"


def _feature_flag_sk(flag_key: str) -> str:
    return f"FEATUREFLAG#{str(flag_key or '').strip().lower()}"


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
        "identity_provider_type": user.identity_provider_type.value,
        "external_subject_id": user.external_subject_id,
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
        "contact_email": organization.contact_email,
        "deleted_at": organization.deleted_at,
        "deleted_by_user_id": organization.deleted_by_user_id,
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


def _api_key_item(api_key: ApiKeyRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(api_key.organization_id),
        "sk": f"APIKEY#{api_key.key_id}",
        "type": "API_KEY",
        "organization_id": api_key.organization_id,
        "key_id": api_key.key_id,
        "hashed_key_value": api_key.hashed_key_value,
        "display_name": api_key.display_name,
        "created_at": api_key.created_at,
        "created_by_user_id": api_key.created_by_user_id,
        "status": api_key.status.value,
        "last_used_at": api_key.last_used_at,
        "gsi5pk": f"APIKEY#{api_key.key_id}",
        "gsi5sk": f"ORG#{api_key.organization_id}",
    }


def _plan_item(plan: PlanRecord) -> dict[str, Any]:
    plan_key = _normalize_plan_key(plan.plan_code or plan.plan_id)
    return {
        "pk": _plan_pk(plan_key),
        "sk": "PLAN",
        "type": "PLAN",
        "plan_id": plan_key,
        "plan_code": plan_key,
        "plan_name": plan.plan_name,
        "monthly_price": plan.monthly_price,
        "feature_flags": list(plan.feature_flags),
        "request_limit": plan.request_limit,
        "description": plan.description,
        "gsi6pk": "PLANCATALOG",
        "gsi6sk": plan_key,
    }


def _subscription_item(subscription: SubscriptionRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(subscription.organization_id),
        "sk": "SUBSCRIPTION",
        "type": "SUBSCRIPTION",
        "subscription_id": subscription.subscription_id,
        "organization_id": subscription.organization_id,
        "plan_id": subscription.plan_id,
        "status": subscription.status.value,
        "billing_cycle_start": subscription.billing_cycle_start,
        "billing_cycle_end": subscription.billing_cycle_end,
        "created_at": subscription.created_at,
        "pending_plan_id": subscription.pending_plan_id,
        "pending_plan_effective_at": subscription.pending_plan_effective_at,
        "cancel_at_period_end": bool(subscription.cancel_at_period_end),
        "updated_at": subscription.updated_at,
        "grace_period_ends_at": subscription.grace_period_ends_at,
        "billing_status": subscription.billing_status,
    }


def _usage_item(record: UsageRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(record.organization_id),
        "sk": _usage_sk(record.period_month, record.metric_type.value),
        "type": "USAGE_RECORD",
        "organization_id": record.organization_id,
        "metric_type": record.metric_type.value,
        "period_month": record.period_month,
        "request_count": record.request_count,
        "last_updated": record.last_updated,
    }


def _feature_flag_item(record: FeatureFlagRecord) -> dict[str, Any]:
    return {
        "pk": _organization_pk(record.organization_id),
        "sk": _feature_flag_sk(record.flag_key.value),
        "type": "FEATURE_FLAG",
        "organization_id": record.organization_id,
        "flag_key": record.flag_key.value,
        "enabled": bool(record.enabled),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
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
        identity_provider_type=IdentityProviderType(
            str(item.get("identity_provider_type") or IdentityProviderType.LOCAL_PASSWORD.value)
        ),
        external_subject_id=_optional_string(item.get("external_subject_id")),
    )


def _organization_from_item(item: dict[str, Any]) -> OrganizationRecord:
    return OrganizationRecord(
        organization_id=str(item.get("organization_id") or ""),
        name=str(item.get("name") or ""),
        slug=str(item.get("slug") or ""),
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
        contact_email=_optional_string(item.get("contact_email")),
        deleted_at=_optional_string(item.get("deleted_at")),
        deleted_by_user_id=_optional_string(item.get("deleted_by_user_id")),
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


def _api_key_from_item(item: dict[str, Any]) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=str(item.get("key_id") or ""),
        organization_id=str(item.get("organization_id") or ""),
        hashed_key_value=str(item.get("hashed_key_value") or ""),
        display_name=str(item.get("display_name") or ""),
        created_at=str(item.get("created_at") or ""),
        created_by_user_id=str(item.get("created_by_user_id") or ""),
        status=ApiKeyStatus(str(item.get("status") or ApiKeyStatus.ACTIVE.value)),
        last_used_at=_optional_string(item.get("last_used_at")),
    )


def _plan_from_item(item: dict[str, Any]) -> PlanRecord:
    feature_flags = item.get("feature_flags") or []
    return PlanRecord(
        plan_id=str(item.get("plan_id") or ""),
        plan_code=str(item.get("plan_code") or item.get("plan_id") or ""),
        plan_name=str(item.get("plan_name") or ""),
        monthly_price=int(item.get("monthly_price") or 0),
        feature_flags=tuple(str(flag) for flag in feature_flags),
        request_limit=int(item.get("request_limit") or 0),
        description=str(item.get("description") or ""),
    )


def _normalize_plan_key(value: int | str | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized


def _subscription_from_item(item: dict[str, Any]) -> SubscriptionRecord:
    return SubscriptionRecord(
        subscription_id=str(item.get("subscription_id") or ""),
        organization_id=str(item.get("organization_id") or ""),
        plan_id=str(item.get("plan_id") or ""),
        status=SubscriptionStatus(str(item.get("status") or SubscriptionStatus.ACTIVE.value)),
        billing_cycle_start=str(item.get("billing_cycle_start") or ""),
        billing_cycle_end=str(item.get("billing_cycle_end") or ""),
        created_at=str(item.get("created_at") or ""),
        pending_plan_id=_optional_string(item.get("pending_plan_id")),
        pending_plan_effective_at=_optional_string(item.get("pending_plan_effective_at")),
        cancel_at_period_end=bool(item.get("cancel_at_period_end", False)),
        updated_at=_optional_string(item.get("updated_at")),
        grace_period_ends_at=_optional_string(item.get("grace_period_ends_at")),
        billing_status=_optional_string(item.get("billing_status")),
    )


def _usage_from_item(item: dict[str, Any]) -> UsageRecord:
    return UsageRecord(
        organization_id=str(item.get("organization_id") or ""),
        metric_type=UsageMetricType(str(item.get("metric_type") or UsageMetricType.API_REQUESTS.value)),
        period_month=str(item.get("period_month") or ""),
        request_count=int(item.get("request_count") or 0),
        last_updated=str(item.get("last_updated") or ""),
    )


def _feature_flag_from_item(item: dict[str, Any]) -> FeatureFlagRecord:
    return FeatureFlagRecord(
        organization_id=str(item.get("organization_id") or ""),
        flag_key=FeatureFlagKey(str(item.get("flag_key") or FeatureFlagKey.ENABLE_CANDID.value)),
        enabled=bool(item.get("enabled", False)),
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
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

    def update_item(  # noqa: N803
        self,
        Key,
        UpdateExpression=None,
        ExpressionAttributeNames=None,
        ExpressionAttributeValues=None,
        ReturnValues=None,
    ):
        key = (Key["pk"], Key["sk"])
        item = deepcopy(self._items.get(key) or {"pk": Key["pk"], "sk": Key["sk"]})
        if UpdateExpression and "#request_count = if_not_exists(#request_count, :zero) + :units" in UpdateExpression:
            values = ExpressionAttributeValues or {}
            item["type"] = values[":type"]
            item["organization_id"] = values[":organization_id"]
            item["metric_type"] = values[":metric_type"]
            item["period_month"] = values[":period_month"]
            item["request_count"] = int(item.get("request_count") or values[":zero"]) + int(values[":units"])
            item["last_updated"] = values[":last_updated"]
            self._items[key] = deepcopy(item)
            if ReturnValues == "ALL_NEW":
                return {"Attributes": deepcopy(item)}
            return {}
        raise NotImplementedError("FakeIdentityDynamoTable.update_item only supports usage counter updates")

    def delete_item(self, Key):  # noqa: N803
        self._items.pop((Key["pk"], Key["sk"]), None)
        return {}

    def query(  # noqa: N803
        self,
        IndexName=None,
        KeyConditionExpression=None,
        ExpressionAttributeValues=None,
        Limit=None,
        ExclusiveStartKey=None,
        ScanIndexForward=True,
    ):
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
        elif IndexName == API_KEY_LOOKUP_INDEX:
            matches = [item for item in items if item.get("gsi5pk") == values.get(":gsi5pk")]
            matches.sort(key=lambda item: str(item.get("gsi5sk") or ""))
        elif IndexName == PLAN_LOOKUP_INDEX:
            matches = [item for item in items if item.get("gsi6pk") == values.get(":gsi6pk")]
            matches.sort(key=lambda item: str(item.get("gsi6sk") or ""))
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
        if not ScanIndexForward:
            matches.reverse()
        if ExclusiveStartKey is not None:
            start_pk = ExclusiveStartKey.get("pk")
            start_sk = ExclusiveStartKey.get("sk")
            for index, item in enumerate(matches):
                if item.get("pk") == start_pk and item.get("sk") == start_sk:
                    matches = matches[index + 1 :]
                    break
        if Limit is not None:
            page = matches[:Limit]
            last_evaluated_key = None
            if len(matches) > Limit and page:
                last = page[-1]
                last_evaluated_key = {"pk": last["pk"], "sk": last["sk"]}
            return {
                "Items": [deepcopy(item) for item in page],
                **({"LastEvaluatedKey": last_evaluated_key} if last_evaluated_key is not None else {}),
            }
        return {"Items": [deepcopy(item) for item in matches]}


class FakeIdentityDynamoResource:
    def __init__(self, table: FakeIdentityDynamoTable) -> None:
        self._table = table

    def Table(self, name: str):  # noqa: N802
        return self._table
