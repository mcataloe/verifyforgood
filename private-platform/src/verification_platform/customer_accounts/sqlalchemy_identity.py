from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
    ApiKeyRepository,
    DuplicateApiKeyError,
    DuplicateMembershipError,
    DuplicateOrganizationSlugError,
    DuplicateUserEmailError,
    FeatureFlagRepository,
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    PlanRepository,
    SubscriptionRepository,
    UsageRepository,
    UserRepository,
)
from .sqlalchemy_db import customer_accounts_session_scope
from .sqlalchemy_models import (
    OrganizationApiKeyModel,
    OrganizationMembershipModel,
    OrganizationModel,
    OrganizationSubscriptionModel,
    OrganizationFeatureFlagModel,
    OrganizationInvitationModel,
    OrganizationSettingsModel,
    OrganizationUsageMonthlyModel,
    PlanModel,
    UserModel,
)


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, user: UserRecord) -> UserRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _user_model(user)
            session.add(model)
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateUserEmailError(f"User email already exists: {user.email}") from exc
            session.refresh(model)
            return _user_record(model)

    def get(self, user_id: int | str) -> UserRecord | None:
        normalized = _normalize_int_id(user_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(UserModel, normalized)
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
            model = _organization_model(organization)
            session.add(model)
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateOrganizationSlugError(f"Organization slug already exists: {organization.slug}") from exc
            session.refresh(model)
            return _organization_record(model)

    def get(self, organization_id: int | str) -> OrganizationRecord | None:
        normalized = _normalize_int_id(organization_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationModel, normalized)
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
        organization_id: int | str,
        *,
        name: str,
        slug: str,
        contact_email: str | None,
        updated_at: str,
    ) -> OrganizationRecord | None:
        normalized = _normalize_int_id(organization_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationModel, normalized)
            if model is None or model.deleted_at is not None:
                return None
            model.name = name
            model.slug = str(slug).strip().lower()
            model.contact_email = contact_email
            model.updated_at = _parse_timestamp(updated_at)
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateOrganizationSlugError(
                    f"Organization slug already exists: {slug}"
                ) from exc
            return _organization_record(model)

    def soft_delete(
        self,
        organization_id: int | str,
        *,
        deleted_at: str,
        deleted_by_user_id: int | str,
    ) -> OrganizationRecord | None:
        normalized = _normalize_int_id(organization_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationModel, normalized)
            if model is None:
                return None
            model.deleted_at = _parse_timestamp(deleted_at)
            model.deleted_by_user_id = _normalize_int_id(deleted_by_user_id)
            model.updated_at = _parse_timestamp(deleted_at)
            session.flush()
            return _organization_record(model)


class SqlAlchemyMembershipRepository(MembershipRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, membership: MembershipRecord) -> MembershipRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _membership_model(membership)
            session.add(model)
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateMembershipError(
                    f"Membership already exists for user {membership.user_id} in organization {membership.organization_id}"
                ) from exc
            session.refresh(model)
            return _membership_record(model)

    def get(self, organization_id: int | str, user_id: int | str) -> MembershipRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _membership_lookup(session, organization_id=organization_id, user_id=user_id)
            return None if model is None else _membership_record(model)

    def list_for_organization(self, organization_id: int | str) -> list[MembershipRecord]:
        normalized = _normalize_int_id(organization_id)
        if normalized is None:
            return []
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationMembershipModel)
                .where(OrganizationMembershipModel.organization_id == normalized)
                .order_by(OrganizationMembershipModel.created_at, OrganizationMembershipModel.user_id)
            ).all()
            return [_membership_record(model) for model in models]

    def list_for_user(self, user_id: int | str) -> list[MembershipRecord]:
        normalized = _normalize_int_id(user_id)
        if normalized is None:
            return []
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationMembershipModel)
                .where(OrganizationMembershipModel.user_id == normalized)
                .order_by(OrganizationMembershipModel.created_at, OrganizationMembershipModel.organization_id)
            ).all()
            return [_membership_record(model) for model in models]

    def update_role(self, organization_id: int | str, user_id: int | str, role: str) -> MembershipRecord | None:
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
        organization_id: int | str,
        user_id: int | str,
        *,
        role: str | None = None,
        status: str | None = None,
        updated_at: str,
    ) -> MembershipRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _membership_lookup(session, organization_id=organization_id, user_id=user_id)
            if model is None:
                return None
            if role is not None:
                model.role = role
            if status is not None:
                model.status = status
            model.updated_at = _parse_timestamp(updated_at)
            session.flush()
            return _membership_record(model)

    def delete(self, organization_id: int | str, user_id: int | str) -> bool:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _membership_lookup(session, organization_id=organization_id, user_id=user_id)
            if model is None:
                return False
            session.delete(model)
            return True


class SqlAlchemyInvitationRepository(InvitationRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, invitation: InvitationRecord) -> InvitationRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _invitation_model(invitation)
            session.add(model)
            session.flush()
            session.refresh(model)
            return _invitation_record(model)

    def get(self, organization_id: str, invitation_id: str) -> InvitationRecord | None:
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_org_id is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationInvitationModel, str(invitation_id))
            if model is None or model.organization_id != normalized_org_id:
                return None
            return _invitation_record(model)

    def list_for_organization(self, organization_id: str) -> list[InvitationRecord]:
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_org_id is None:
            return []
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationInvitationModel)
                .where(OrganizationInvitationModel.organization_id == normalized_org_id)
                .order_by(OrganizationInvitationModel.created_at, OrganizationInvitationModel.invitation_id)
            ).all()
            return [_invitation_record(model) for model in models]

    def get_by_token(self, token: str) -> InvitationRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationInvitationModel)
                .where(OrganizationInvitationModel.token == str(token))
                .limit(1)
            )
            return None if model is None else _invitation_record(model)

    def mark_accepted(self, token: str, accepted_at: str) -> InvitationRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationInvitationModel)
                .where(OrganizationInvitationModel.token == str(token))
                .limit(1)
            )
            if model is None:
                return None
            model.status = InvitationStatus.ACCEPTED.value
            model.accepted_at = _parse_timestamp(accepted_at)
            session.flush()
            return _invitation_record(model)


class SqlAlchemyUsageRepository(UsageRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def increment(
        self,
        organization_id: str,
        metric_type: str,
        period_month: str,
        *,
        units: int,
        last_updated: str,
    ) -> UsageRecord:
        normalized_org_id = _require_int_id(organization_id, field_name="organization_id")
        resolved_units = max(0, int(units))
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _usage_lookup(session, organization_id=normalized_org_id, metric_type=metric_type, period_month=period_month)
            if model is None:
                model = OrganizationUsageMonthlyModel(
                    organization_id=normalized_org_id,
                    metric_type=metric_type,
                    period_month=period_month,
                    request_count=resolved_units,
                    last_updated=_parse_timestamp(last_updated),
                )
                session.add(model)
            else:
                model.request_count = int(model.request_count or 0) + resolved_units
                model.last_updated = _parse_timestamp(last_updated)
            session.flush()
            return _usage_record(model)

    def get(self, organization_id: str, metric_type: str, period_month: str) -> UsageRecord | None:
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_org_id is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _usage_lookup(session, organization_id=normalized_org_id, metric_type=metric_type, period_month=period_month)
            return None if model is None else _usage_record(model)

    def list_for_period(self, organization_id: str, period_month: str) -> list[UsageRecord]:
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_org_id is None:
            return []
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationUsageMonthlyModel)
                .where(
                    OrganizationUsageMonthlyModel.organization_id == normalized_org_id,
                    OrganizationUsageMonthlyModel.period_month == str(period_month),
                )
                .order_by(OrganizationUsageMonthlyModel.metric_type)
            ).all()
            return [_usage_record(model) for model in models]

    def put(self, record: UsageRecord) -> UsageRecord:
        normalized_org_id = _require_int_id(record.organization_id, field_name="organization_id")
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _usage_lookup(
                session,
                organization_id=normalized_org_id,
                metric_type=record.metric_type.value,
                period_month=record.period_month,
            )
            if model is None:
                model = OrganizationUsageMonthlyModel(
                    organization_id=normalized_org_id,
                    metric_type=record.metric_type.value,
                    period_month=record.period_month,
                    request_count=int(record.request_count),
                    last_updated=_parse_timestamp(record.last_updated),
                )
                session.add(model)
            else:
                model.request_count = int(record.request_count)
                model.last_updated = _parse_timestamp(record.last_updated)
            session.flush()
            return _usage_record(model)


class SqlAlchemyFeatureFlagRepository(FeatureFlagRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, organization_id: str, flag_key: str) -> FeatureFlagRecord | None:
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_org_id is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _feature_flag_lookup(session, organization_id=normalized_org_id, flag_key=flag_key)
            return None if model is None else _feature_flag_record(model)

    def list_for_organization(self, organization_id: str) -> list[FeatureFlagRecord]:
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_org_id is None:
            return []
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationFeatureFlagModel)
                .where(OrganizationFeatureFlagModel.organization_id == normalized_org_id)
                .order_by(OrganizationFeatureFlagModel.flag_key)
            ).all()
            return [_feature_flag_record(model) for model in models]

    def put(self, record: FeatureFlagRecord) -> FeatureFlagRecord:
        normalized_org_id = _require_int_id(record.organization_id, field_name="organization_id")
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _feature_flag_lookup(session, organization_id=normalized_org_id, flag_key=record.flag_key.value)
            if model is None:
                model = OrganizationFeatureFlagModel(
                    organization_id=normalized_org_id,
                    flag_key=record.flag_key.value,
                    enabled=bool(record.enabled),
                    created_at=_parse_timestamp(record.created_at),
                    updated_at=_parse_timestamp(record.updated_at),
                )
                session.add(model)
            else:
                model.enabled = bool(record.enabled)
                model.created_at = _parse_timestamp(record.created_at)
                model.updated_at = _parse_timestamp(record.updated_at)
            session.flush()
            return _feature_flag_record(model)


class SqlAlchemyPlanRepository(PlanRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get(self, plan_id: int | str) -> PlanRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _lookup_plan(session, plan_id)
            return None if model is None else _plan_record(model)

    def list_all(self) -> list[PlanRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(select(PlanModel).order_by(PlanModel.plan_id)).all()
            return [_plan_record(model) for model in models]

    def seed_defaults(self, plans: list[PlanRecord]) -> None:
        with customer_accounts_session_scope(self._session_factory) as session:
            for record in plans:
                model = session.scalar(select(PlanModel).where(PlanModel.plan_code == record.plan_code).limit(1))
                if model is None:
                    session.add(_plan_model(record))
                    continue
                model.plan_name = record.plan_name
                model.plan_code = record.plan_code
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
            model = _lookup_subscription(
                session,
                subscription_id=subscription.subscription_id,
                organization_id=subscription.organization_id,
            )
            if model is None:
                model = _subscription_model(subscription)
                session.add(model)
            else:
                model.organization_id = _require_int_id(subscription.organization_id, field_name="organization_id")
                model.plan_id = _require_int_id(subscription.plan_id, field_name="plan_id")
                model.status = subscription.status.value
                model.billing_cycle_start = _parse_timestamp(subscription.billing_cycle_start)
                model.billing_cycle_end = _parse_timestamp(subscription.billing_cycle_end)
                model.created_at = _parse_timestamp(subscription.created_at)
                model.pending_plan_id = _normalize_int_id(subscription.pending_plan_id)
                model.pending_plan_effective_at = (
                    _parse_timestamp(subscription.pending_plan_effective_at) if subscription.pending_plan_effective_at else None
                )
                model.cancel_at_period_end = bool(subscription.cancel_at_period_end)
                model.updated_at = _parse_timestamp(subscription.updated_at) if subscription.updated_at else None
                model.grace_period_ends_at = _parse_timestamp(subscription.grace_period_ends_at) if subscription.grace_period_ends_at else None
                model.billing_status = subscription.billing_status
            session.flush()
            session.refresh(model)
            return _subscription_record(model)

    def get_by_organization(self, organization_id: int | str) -> SubscriptionRecord | None:
        normalized = _normalize_int_id(organization_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationSubscriptionModel)
                .where(OrganizationSubscriptionModel.organization_id == normalized)
                .limit(1)
            )
            return None if model is None else _subscription_record(model)


class SqlAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, api_key: ApiKeyRecord) -> ApiKeyRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _api_key_model(api_key)
            session.add(model)
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateApiKeyError("API key already exists") from exc
            session.refresh(model)
            return _api_key_record(model)

    def list_for_organization(self, organization_id: int | str) -> list[ApiKeyRecord]:
        normalized = _normalize_int_id(organization_id)
        if normalized is None:
            return []
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationApiKeyModel)
                .where(OrganizationApiKeyModel.organization_id == normalized)
                .order_by(OrganizationApiKeyModel.created_at, OrganizationApiKeyModel.key_id)
            ).all()
            return [_api_key_record(model) for model in models]

    def get_by_key_id(self, key_id: int | str) -> ApiKeyRecord | None:
        normalized = _normalize_int_id(key_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, normalized)
            return None if model is None else _api_key_record(model)

    def update_metadata(
        self,
        organization_id: int | str,
        key_id: int | str,
        *,
        display_name: str,
        description: str,
    ) -> ApiKeyRecord | None:
        normalized_key_id = _normalize_int_id(key_id)
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_key_id is None or normalized_org_id is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, normalized_key_id)
            if model is None or model.organization_id != normalized_org_id:
                return None
            model.display_name = display_name
            model.description = description
            session.flush()
            return _api_key_record(model)

    def revoke(self, organization_id: int | str, key_id: int | str, *, revoked_at: str | None = None) -> ApiKeyRecord | None:
        normalized_key_id = _normalize_int_id(key_id)
        normalized_org_id = _normalize_int_id(organization_id)
        if normalized_key_id is None or normalized_org_id is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, normalized_key_id)
            if model is None or model.organization_id != normalized_org_id:
                return None
            model.status = ApiKeyStatus.REVOKED.value
            if revoked_at:
                model.last_used_at = _parse_timestamp(revoked_at)
            session.flush()
            return _api_key_record(model)

    def touch_last_used(self, key_id: int | str, *, used_at: str) -> ApiKeyRecord | None:
        normalized = _normalize_int_id(key_id)
        if normalized is None:
            return None
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.get(OrganizationApiKeyModel, normalized)
            if model is None:
                return None
            model.last_used_at = _parse_timestamp(used_at)
            session.flush()
            return _api_key_record(model)


def _lookup_plan(session: Session, plan_id: int | str) -> PlanModel | None:
    normalized_id = _normalize_int_id(plan_id)
    if normalized_id is not None:
        model = session.get(PlanModel, normalized_id)
        if model is not None:
            return model
    normalized_code = _normalize_code(plan_id)
    if not normalized_code:
        return None
    return session.scalar(select(PlanModel).where(PlanModel.plan_code == normalized_code).limit(1))


def _lookup_subscription(
    session: Session,
    *,
    subscription_id: int | str | None,
    organization_id: int | str,
) -> OrganizationSubscriptionModel | None:
    normalized_subscription_id = _normalize_int_id(subscription_id)
    normalized_organization_id = _normalize_int_id(organization_id)
    if normalized_subscription_id is not None:
        model = session.get(OrganizationSubscriptionModel, normalized_subscription_id)
        if model is not None:
            return model
    if normalized_organization_id is None:
        return None
    return session.scalar(
        select(OrganizationSubscriptionModel)
        .where(OrganizationSubscriptionModel.organization_id == normalized_organization_id)
        .limit(1)
    )


def _membership_lookup(session: Session, *, organization_id: int | str, user_id: int | str) -> OrganizationMembershipModel | None:
    normalized_org_id = _normalize_int_id(organization_id)
    normalized_user_id = _normalize_int_id(user_id)
    if normalized_org_id is None or normalized_user_id is None:
        return None
    return session.scalar(
        select(OrganizationMembershipModel)
        .where(
            OrganizationMembershipModel.organization_id == normalized_org_id,
            OrganizationMembershipModel.user_id == normalized_user_id,
        )
        .limit(1)
    )


def _usage_lookup(
    session: Session,
    *,
    organization_id: int | str,
    metric_type: str,
    period_month: str,
) -> OrganizationUsageMonthlyModel | None:
    normalized_org_id = _normalize_int_id(organization_id)
    if normalized_org_id is None:
        return None
    return session.scalar(
        select(OrganizationUsageMonthlyModel)
        .where(
            OrganizationUsageMonthlyModel.organization_id == normalized_org_id,
            OrganizationUsageMonthlyModel.metric_type == str(metric_type),
            OrganizationUsageMonthlyModel.period_month == str(period_month),
        )
        .limit(1)
    )


def _feature_flag_lookup(
    session: Session,
    *,
    organization_id: int | str,
    flag_key: str,
) -> OrganizationFeatureFlagModel | None:
    normalized_org_id = _normalize_int_id(organization_id)
    if normalized_org_id is None:
        return None
    return session.scalar(
        select(OrganizationFeatureFlagModel)
        .where(
            OrganizationFeatureFlagModel.organization_id == normalized_org_id,
            OrganizationFeatureFlagModel.flag_key == str(flag_key),
        )
        .limit(1)
    )


def _normalize_int_id(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.isdigit():
        return int(normalized)
    return None


def _require_int_id(value: int | str | None, *, field_name: str) -> int:
    normalized = _normalize_int_id(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be a numeric identifier")
    return normalized


def _normalize_code(value: int | str | None) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


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
    kwargs = {
        "email": record.email,
        "normalized_email": record.normalized_email,
        "full_name": record.full_name,
        "created_at": _parse_timestamp(record.created_at),
        "updated_at": _parse_timestamp(record.updated_at),
        "password_hash": record.password_hash,
        "identity_provider_type": record.identity_provider_type.value,
        "external_subject_id": record.external_subject_id,
    }
    user_id = _normalize_int_id(record.user_id)
    if user_id is not None:
        kwargs["user_id"] = user_id
    return UserModel(**kwargs)


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
    kwargs = {
        "name": record.name,
        "slug": record.slug,
        "created_at": _parse_timestamp(record.created_at),
        "updated_at": _parse_timestamp(record.updated_at),
        "contact_email": record.contact_email,
        "deleted_at": _parse_timestamp(record.deleted_at) if record.deleted_at else None,
        "deleted_by_user_id": _normalize_int_id(record.deleted_by_user_id),
    }
    organization_id = _normalize_int_id(record.organization_id)
    if organization_id is not None:
        kwargs["organization_id"] = organization_id
    return OrganizationModel(**kwargs)


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
    kwargs = {
        "organization_id": _require_int_id(record.organization_id, field_name="organization_id"),
        "user_id": _require_int_id(record.user_id, field_name="user_id"),
        "role": record.role.value,
        "status": record.status.value,
        "created_at": _parse_timestamp(record.created_at),
        "updated_at": _parse_timestamp(record.updated_at),
    }
    if record.membership_id is not None:
        kwargs["membership_id"] = record.membership_id
    return OrganizationMembershipModel(**kwargs)


def _membership_record(model: OrganizationMembershipModel) -> MembershipRecord:
    return MembershipRecord(
        membership_id=model.membership_id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        role=MembershipRole(model.role),
        status=MembershipStatus(model.status),
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _invitation_model(record: InvitationRecord) -> OrganizationInvitationModel:
    return OrganizationInvitationModel(
        invitation_id=str(record.invitation_id),
        organization_id=_require_int_id(record.organization_id, field_name="organization_id"),
        email=record.email,
        normalized_email=record.normalized_email,
        token=record.token,
        role=record.role.value,
        status=record.status.value,
        invited_by_user_id=_normalize_int_id(record.invited_by_user_id),
        created_at=_parse_timestamp(record.created_at),
        expires_at=_parse_timestamp(record.expires_at),
        accepted_at=_parse_timestamp(record.accepted_at) if record.accepted_at else None,
    )


def _invitation_record(model: OrganizationInvitationModel) -> InvitationRecord:
    return InvitationRecord(
        invitation_id=model.invitation_id,
        organization_id=str(model.organization_id),
        email=model.email,
        normalized_email=model.normalized_email,
        token=model.token,
        role=MembershipRole(model.role),
        status=InvitationStatus(model.status),
        invited_by_user_id=(str(model.invited_by_user_id) if model.invited_by_user_id is not None else None),
        created_at=_format_timestamp(model.created_at) or "",
        expires_at=_format_timestamp(model.expires_at) or "",
        accepted_at=_format_timestamp(model.accepted_at),
    )


def _plan_model(record: PlanRecord) -> PlanModel:
    kwargs = {
        "plan_code": record.plan_code,
        "plan_name": record.plan_name,
        "monthly_price": record.monthly_price,
        "feature_flags": list(record.feature_flags),
        "request_limit": record.request_limit,
        "description": record.description,
    }
    plan_id = _normalize_int_id(record.plan_id)
    if plan_id is not None:
        kwargs["plan_id"] = plan_id
    return PlanModel(**kwargs)


def _plan_record(model: PlanModel) -> PlanRecord:
    return PlanRecord(
        plan_id=model.plan_id,
        plan_code=model.plan_code,
        plan_name=model.plan_name,
        monthly_price=model.monthly_price,
        feature_flags=tuple(model.feature_flags or []),
        request_limit=model.request_limit,
        description=model.description,
    )


def _subscription_model(record: SubscriptionRecord) -> OrganizationSubscriptionModel:
    kwargs = {
        "organization_id": _require_int_id(record.organization_id, field_name="organization_id"),
        "plan_id": _require_int_id(record.plan_id, field_name="plan_id"),
        "status": record.status.value,
        "billing_cycle_start": _parse_timestamp(record.billing_cycle_start),
        "billing_cycle_end": _parse_timestamp(record.billing_cycle_end),
        "created_at": _parse_timestamp(record.created_at),
        "pending_plan_id": _normalize_int_id(record.pending_plan_id),
        "pending_plan_effective_at": _parse_timestamp(record.pending_plan_effective_at) if record.pending_plan_effective_at else None,
        "cancel_at_period_end": bool(record.cancel_at_period_end),
        "updated_at": _parse_timestamp(record.updated_at) if record.updated_at else None,
        "grace_period_ends_at": _parse_timestamp(record.grace_period_ends_at) if record.grace_period_ends_at else None,
        "billing_status": record.billing_status,
    }
    subscription_id = _normalize_int_id(record.subscription_id)
    if subscription_id is not None:
        kwargs["subscription_id"] = subscription_id
    return OrganizationSubscriptionModel(**kwargs)


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
    kwargs = {
        "organization_id": _require_int_id(record.organization_id, field_name="organization_id"),
        "hashed_key_value": record.hashed_key_value,
        "display_name": record.display_name,
        "description": record.description,
        "created_at": _parse_timestamp(record.created_at),
        "created_by_user_id": _require_int_id(record.created_by_user_id, field_name="created_by_user_id"),
        "status": record.status.value,
        "last_used_at": _parse_timestamp(record.last_used_at) if record.last_used_at else None,
    }
    key_id = _normalize_int_id(record.key_id)
    if key_id is not None:
        kwargs["key_id"] = key_id
    return OrganizationApiKeyModel(**kwargs)


def _api_key_record(model: OrganizationApiKeyModel) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=model.key_id,
        organization_id=model.organization_id,
        hashed_key_value=model.hashed_key_value,
        display_name=model.display_name,
        description=model.description,
        created_at=_format_timestamp(model.created_at) or "",
        created_by_user_id=model.created_by_user_id,
        status=ApiKeyStatus(model.status),
        last_used_at=_format_timestamp(model.last_used_at),
    )


def _usage_record(model: OrganizationUsageMonthlyModel) -> UsageRecord:
    return UsageRecord(
        organization_id=str(model.organization_id),
        metric_type=UsageMetricType(model.metric_type),
        period_month=model.period_month,
        request_count=int(model.request_count),
        last_updated=_format_timestamp(model.last_updated) or "",
    )


def _feature_flag_record(model: OrganizationFeatureFlagModel) -> FeatureFlagRecord:
    return FeatureFlagRecord(
        organization_id=str(model.organization_id),
        flag_key=FeatureFlagKey(model.flag_key),
        enabled=bool(model.enabled),
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )
