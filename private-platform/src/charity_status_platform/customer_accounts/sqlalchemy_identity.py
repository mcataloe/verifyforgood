from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .identity_models import (
    ApiKeyRecord,
    ApiKeyStatus,
    IdentityProviderType,
    MembershipRecord,
    MembershipRole,
    MembershipStatus,
    OrganizationRecord,
    PlanRecord,
    SubscriptionRecord,
    SubscriptionStatus,
    UserRecord,
)
from .identity_repositories import (
    ApiKeyRepository,
    DuplicateApiKeyError,
    DuplicateMembershipError,
    DuplicateOrganizationSlugError,
    DuplicateUserEmailError,
    MembershipRepository,
    OrganizationRepository,
    PlanRepository,
    SubscriptionRepository,
    UserRepository,
)
from .sqlalchemy_db import customer_accounts_session_scope
from .sqlalchemy_models import (
    OrganizationApiKeyModel,
    OrganizationMembershipModel,
    OrganizationModel,
    OrganizationSubscriptionModel,
    PlanModel,
    UserModel,
)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, user: UserRecord) -> UserRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            session.add(_user_model(user))
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateUserEmailError(f"User email already exists: {user.email}") from exc
        return user

    def get(self, user_id: str) -> UserRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(UserModel, user_id)
            return None if model is None else _user_record(model)

    def get_by_email(self, email: str) -> UserRecord | None:
        normalized_email = str(email or "").strip().lower()
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(select(UserModel).where(UserModel.normalized_email == normalized_email).limit(1))
            return None if model is None else _user_record(model)


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, organization: OrganizationRecord) -> OrganizationRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            session.add(_organization_model(organization))
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateOrganizationSlugError(f"Organization slug already exists: {organization.slug}") from exc
        return organization

    def get(self, organization_id: str) -> OrganizationRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationModel, organization_id)
            if model is None:
                return None
            record = _organization_record(model)
            return None if record.deleted_at else record

    def get_by_slug(self, slug: str) -> OrganizationRecord | None:
        normalized_slug = str(slug or "").strip().lower()
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(select(OrganizationModel).where(OrganizationModel.slug == normalized_slug).limit(1))
            if model is None:
                return None
            record = _organization_record(model)
            return None if record.deleted_at else record

    def update_profile(
        self,
        organization_id: str,
        *,
        name: str,
        contact_email: str | None,
        updated_at: str,
    ) -> OrganizationRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationModel, organization_id)
            if model is None or model.deleted_at is not None:
                return None
            model.name = name
            model.contact_email = contact_email
            model.updated_at = _parse_timestamp(updated_at)
            session.flush()
            return _organization_record(model)

    def soft_delete(
        self,
        organization_id: str,
        *,
        deleted_at: str,
        deleted_by_user_id: str,
    ) -> OrganizationRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationModel, organization_id)
            if model is None:
                return None
            model.deleted_at = _parse_timestamp(deleted_at)
            model.deleted_by_user_id = deleted_by_user_id
            model.updated_at = _parse_timestamp(deleted_at)
            session.flush()
            return _organization_record(model)


class SqlAlchemyMembershipRepository(MembershipRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, membership: MembershipRecord) -> MembershipRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            session.add(_membership_model(membership))
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateMembershipError(
                    f"Membership already exists for user {membership.user_id} in organization {membership.organization_id}"
                ) from exc
        return membership

    def get(self, organization_id: str, user_id: str) -> MembershipRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationMembershipModel, {"organization_id": organization_id, "user_id": user_id})
            return None if model is None else _membership_record(model)

    def list_for_organization(self, organization_id: str) -> list[MembershipRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationMembershipModel)
                .where(OrganizationMembershipModel.organization_id == organization_id)
                .order_by(OrganizationMembershipModel.created_at, OrganizationMembershipModel.user_id)
            ).all()
            return [_membership_record(model) for model in models]

    def list_for_user(self, user_id: str) -> list[MembershipRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationMembershipModel)
                .where(OrganizationMembershipModel.user_id == user_id)
                .order_by(OrganizationMembershipModel.created_at, OrganizationMembershipModel.organization_id)
            ).all()
            return [_membership_record(model) for model in models]

    def update_role(self, organization_id: str, user_id: str, role: str) -> MembershipRecord | None:
        existing = self.get(organization_id, user_id)
        if existing is None:
            return None
        return self.update_membership(
            organization_id,
            user_id,
            role=role,
            updated_at=existing.updated_at,
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
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationMembershipModel, {"organization_id": organization_id, "user_id": user_id})
            if model is None:
                return None
            if role is not None:
                model.role = role
            if status is not None:
                model.status = status
            model.updated_at = _parse_timestamp(updated_at)
            session.flush()
            return _membership_record(model)

    def delete(self, organization_id: str, user_id: str) -> bool:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationMembershipModel, {"organization_id": organization_id, "user_id": user_id})
            if model is None:
                return False
            session.delete(model)
            return True


class SqlAlchemyPlanRepository(PlanRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, plan_id: str) -> PlanRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(PlanModel, plan_id)
            return None if model is None else _plan_record(model)

    def list_all(self) -> list[PlanRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(select(PlanModel).order_by(PlanModel.plan_id)).all()
            return [_plan_record(model) for model in models]

    def seed_defaults(self, plans: list[PlanRecord]) -> None:
        with customer_accounts_session_scope(self._session_factory) as session:
            for record in plans:
                model = session.get(PlanModel, record.plan_id)
                if model is None:
                    session.add(_plan_model(record))
                    continue
                model.plan_name = record.plan_name
                model.monthly_price = record.monthly_price
                model.feature_flags = list(record.feature_flags)
                model.request_limit = record.request_limit
                model.description = record.description
            session.flush()


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def put(self, subscription: SubscriptionRecord) -> SubscriptionRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationSubscriptionModel).where(
                    or_(
                        OrganizationSubscriptionModel.subscription_id == subscription.subscription_id,
                        OrganizationSubscriptionModel.organization_id == subscription.organization_id,
                    )
                ).limit(1)
            )
            if model is None:
                session.add(_subscription_model(subscription))
            else:
                model.subscription_id = subscription.subscription_id
                model.organization_id = subscription.organization_id
                model.plan_id = subscription.plan_id
                model.status = subscription.status.value
                model.billing_cycle_start = _parse_timestamp(subscription.billing_cycle_start)
                model.billing_cycle_end = _parse_timestamp(subscription.billing_cycle_end)
                model.created_at = _parse_timestamp(subscription.created_at)
                model.pending_plan_id = subscription.pending_plan_id
                model.pending_plan_effective_at = _parse_timestamp(subscription.pending_plan_effective_at) if subscription.pending_plan_effective_at else None
                model.cancel_at_period_end = bool(subscription.cancel_at_period_end)
                model.updated_at = _parse_timestamp(subscription.updated_at) if subscription.updated_at else None
                model.grace_period_ends_at = _parse_timestamp(subscription.grace_period_ends_at) if subscription.grace_period_ends_at else None
                model.billing_status = subscription.billing_status
            session.flush()
        return subscription

    def get_by_organization(self, organization_id: str) -> SubscriptionRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationSubscriptionModel)
                .where(OrganizationSubscriptionModel.organization_id == organization_id)
                .limit(1)
            )
            return None if model is None else _subscription_record(model)


class SqlAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            session.add(_api_key_model(api_key))
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateApiKeyError(f"API key already exists: {api_key.key_id}") from exc
        return api_key

    def list_for_organization(self, organization_id: str) -> list[ApiKeyRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationApiKeyModel)
                .where(OrganizationApiKeyModel.organization_id == organization_id)
                .order_by(OrganizationApiKeyModel.created_at, OrganizationApiKeyModel.key_id)
            ).all()
            return [_api_key_record(model) for model in models]

    def get_by_key_id(self, key_id: str) -> ApiKeyRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, key_id)
            return None if model is None else _api_key_record(model)

    def revoke(self, organization_id: str, key_id: str, *, revoked_at: str | None = None) -> ApiKeyRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, key_id)
            if model is None or model.organization_id != organization_id:
                return None
            model.status = ApiKeyStatus.REVOKED.value
            session.flush()
            return _api_key_record(model)

    def touch_last_used(self, key_id: str, *, used_at: str) -> ApiKeyRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, key_id)
            if model is None:
                return None
            model.last_used_at = _parse_timestamp(used_at)
            session.flush()
            return _api_key_record(model)


def _parse_timestamp(value: str) -> datetime:
    normalized = str(value or "").strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _user_model(record: UserRecord) -> UserModel:
    return UserModel(
        user_id=record.user_id,
        email=record.email,
        normalized_email=record.normalized_email,
        full_name=record.full_name,
        created_at=_parse_timestamp(record.created_at),
        updated_at=_parse_timestamp(record.updated_at),
        password_hash=record.password_hash,
        identity_provider_type=record.identity_provider_type.value,
        external_subject_id=record.external_subject_id,
    )


def _user_record(model: UserModel) -> UserRecord:
    return UserRecord(
        user_id=model.user_id,
        email=model.email,
        normalized_email=model.normalized_email,
        full_name=model.full_name,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
        password_hash=model.password_hash,
        identity_provider_type=IdentityProviderType(model.identity_provider_type),
        external_subject_id=model.external_subject_id,
    )


def _organization_model(record: OrganizationRecord) -> OrganizationModel:
    return OrganizationModel(
        organization_id=record.organization_id,
        name=record.name,
        slug=record.slug,
        created_at=_parse_timestamp(record.created_at),
        updated_at=_parse_timestamp(record.updated_at),
        contact_email=record.contact_email,
        deleted_at=_parse_timestamp(record.deleted_at) if record.deleted_at else None,
        deleted_by_user_id=record.deleted_by_user_id,
    )


def _organization_record(model: OrganizationModel) -> OrganizationRecord:
    return OrganizationRecord(
        organization_id=model.organization_id,
        name=model.name,
        slug=model.slug,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
        contact_email=model.contact_email,
        deleted_at=_format_timestamp(model.deleted_at),
        deleted_by_user_id=model.deleted_by_user_id,
    )


def _membership_model(record: MembershipRecord) -> OrganizationMembershipModel:
    return OrganizationMembershipModel(
        organization_id=record.organization_id,
        user_id=record.user_id,
        role=record.role.value,
        status=record.status.value,
        created_at=_parse_timestamp(record.created_at),
        updated_at=_parse_timestamp(record.updated_at),
    )


def _membership_record(model: OrganizationMembershipModel) -> MembershipRecord:
    return MembershipRecord(
        organization_id=model.organization_id,
        user_id=model.user_id,
        role=MembershipRole(model.role),
        status=MembershipStatus(model.status),
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _plan_model(record: PlanRecord) -> PlanModel:
    return PlanModel(
        plan_id=record.plan_id,
        plan_name=record.plan_name,
        monthly_price=record.monthly_price,
        feature_flags=list(record.feature_flags),
        request_limit=record.request_limit,
        description=record.description,
    )


def _plan_record(model: PlanModel) -> PlanRecord:
    return PlanRecord(
        plan_id=model.plan_id,
        plan_name=model.plan_name,
        monthly_price=model.monthly_price,
        feature_flags=tuple(model.feature_flags or []),
        request_limit=model.request_limit,
        description=model.description,
    )


def _subscription_model(record: SubscriptionRecord) -> OrganizationSubscriptionModel:
    return OrganizationSubscriptionModel(
        subscription_id=record.subscription_id,
        organization_id=record.organization_id,
        plan_id=record.plan_id,
        status=record.status.value,
        billing_cycle_start=_parse_timestamp(record.billing_cycle_start),
        billing_cycle_end=_parse_timestamp(record.billing_cycle_end),
        created_at=_parse_timestamp(record.created_at),
        pending_plan_id=record.pending_plan_id,
        pending_plan_effective_at=_parse_timestamp(record.pending_plan_effective_at) if record.pending_plan_effective_at else None,
        cancel_at_period_end=bool(record.cancel_at_period_end),
        updated_at=_parse_timestamp(record.updated_at) if record.updated_at else None,
        grace_period_ends_at=_parse_timestamp(record.grace_period_ends_at) if record.grace_period_ends_at else None,
        billing_status=record.billing_status,
    )


def _subscription_record(model: OrganizationSubscriptionModel) -> SubscriptionRecord:
    return SubscriptionRecord(
        subscription_id=model.subscription_id,
        organization_id=model.organization_id,
        plan_id=model.plan_id,
        status=SubscriptionStatus(model.status),
        billing_cycle_start=_format_timestamp(model.billing_cycle_start) or "",
        billing_cycle_end=_format_timestamp(model.billing_cycle_end) or "",
        created_at=_format_timestamp(model.created_at) or "",
        pending_plan_id=model.pending_plan_id,
        pending_plan_effective_at=_format_timestamp(model.pending_plan_effective_at),
        cancel_at_period_end=bool(model.cancel_at_period_end),
        updated_at=_format_timestamp(model.updated_at),
        grace_period_ends_at=_format_timestamp(model.grace_period_ends_at),
        billing_status=model.billing_status,
    )


def _api_key_model(record: ApiKeyRecord) -> OrganizationApiKeyModel:
    return OrganizationApiKeyModel(
        key_id=record.key_id,
        organization_id=record.organization_id,
        hashed_key_value=record.hashed_key_value,
        display_name=record.display_name,
        created_at=_parse_timestamp(record.created_at),
        created_by_user_id=record.created_by_user_id,
        status=record.status.value,
        last_used_at=_parse_timestamp(record.last_used_at) if record.last_used_at else None,
    )


def _api_key_record(model: OrganizationApiKeyModel) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=model.key_id,
        organization_id=model.organization_id,
        hashed_key_value=model.hashed_key_value,
        display_name=model.display_name,
        created_at=_format_timestamp(model.created_at) or "",
        created_by_user_id=model.created_by_user_id,
        status=ApiKeyStatus(model.status),
        last_used_at=_format_timestamp(model.last_used_at),
    )
