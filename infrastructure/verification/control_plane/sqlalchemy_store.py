from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import BIGINT, JSON, Boolean, DateTime, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, select
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from verification.auth.oauth import StoredOAuthClientRecord
from verification.auth.service import StoredApiKeyRecord

from .models import (
    Account,
    ManagedApiKey,
    ManagedBillingCustomer,
    ManagedBillingEvent,
    ManagedOAuthClient,
    ManagedSubscription,
    ManagedTrialHistory,
)


BIGINT_PRIMARY_KEY = BIGINT().with_variant(Integer(), "sqlite")
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class ControlPlaneBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@contextmanager
def control_plane_session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class ControlPlaneAccountModel(ControlPlaneBase):
    __tablename__ = "control_plane_accounts"

    account_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ein: Mapped[str | None] = mapped_column(String(32), nullable=True)

    subscription: Mapped["ControlPlaneSubscriptionModel | None"] = relationship(back_populates="account", uselist=False)
    billing_customer: Mapped["ControlPlaneBillingCustomerModel | None"] = relationship(back_populates="account", uselist=False)


class ControlPlaneSubscriptionModel(ControlPlaneBase):
    __tablename__ = "control_plane_subscriptions"

    account_id: Mapped[str] = mapped_column(String(128), ForeignKey("control_plane_accounts.account_id"), primary_key=True)
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    billing_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_trigger_event: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trial_consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trial_termination_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pending_plan_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_plan_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stripe_subscription_schedule_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pending_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pending_checkout_session_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_checkout_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    account: Mapped[ControlPlaneAccountModel] = relationship(back_populates="subscription")


class ControlPlaneBillingCustomerModel(ControlPlaneBase):
    __tablename__ = "control_plane_billing_customers"

    account_id: Mapped[str] = mapped_column(String(128), ForeignKey("control_plane_accounts.account_id"), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    account: Mapped[ControlPlaneAccountModel] = relationship(back_populates="billing_customer")


class ControlPlaneBillingEventModel(ControlPlaneBase):
    __tablename__ = "control_plane_billing_events"
    __table_args__ = (
        Index("ix_control_plane_billing_events_account_id", "account_id"),
        Index("ix_control_plane_billing_events_stripe_customer_id", "stripe_customer_id"),
        Index("ix_control_plane_billing_events_stripe_subscription_id", "stripe_subscription_id"),
    )

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processing_outcome: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gross_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tax_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invoice_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    webhook_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ControlPlaneTrialHistoryModel(ControlPlaneBase):
    __tablename__ = "control_plane_trial_histories"

    ein: Mapped[str] = mapped_column(String(32), primary_key=True)
    trial_consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_termination_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ControlPlaneApiKeyModel(ControlPlaneBase):
    __tablename__ = "control_plane_api_keys"
    __table_args__ = (
        Index("ix_control_plane_api_keys_account_id", "account_id"),
    )

    key_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(128), ForeignKey("control_plane_accounts.account_id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rate_limit_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ControlPlaneOAuthClientModel(ControlPlaneBase):
    __tablename__ = "control_plane_oauth_clients"
    __table_args__ = (
        Index("ix_control_plane_oauth_clients_account_id", "account_id"),
    )

    client_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(128), ForeignKey("control_plane_accounts.account_id"), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    client_secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rate_limit_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ControlPlaneUsageMonthlyModel(ControlPlaneBase):
    __tablename__ = "control_plane_usage_monthly"
    __table_args__ = (
        UniqueConstraint("account_id", "month_key", name="uq_control_plane_usage_account_month"),
    )

    usage_id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, Identity(start=1), primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String(128), ForeignKey("control_plane_accounts.account_id"), nullable=False)
    month_key: Mapped[str] = mapped_column(String(16), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SqlAlchemyControlPlaneStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_accounts(self) -> list[Account]:
        with control_plane_session_scope(self._session_factory) as session:
            models = session.scalars(select(ControlPlaneAccountModel).order_by(ControlPlaneAccountModel.created_at, ControlPlaneAccountModel.account_id)).all()
            return [_account_from_model(model) for model in models]

    def get_account(self, account_id: str) -> Account | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneAccountModel, str(account_id))
            return None if model is None else _account_from_model(model)

    def put_account(self, account: Account) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneAccountModel, str(account.id))
            if model is None:
                model = ControlPlaneAccountModel(
                    account_id=str(account.id),
                    name=account.name,
                    status=account.status,
                    created_at=_parse_timestamp(account.created_at),
                    ein=account.ein,
                )
                session.add(model)
            else:
                model.name = account.name
                model.status = account.status
                model.created_at = _parse_timestamp(account.created_at)
                model.ein = account.ein
            session.flush()

    def get_subscription(self, account_id: str) -> ManagedSubscription | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneSubscriptionModel, str(account_id))
            return None if model is None else _subscription_from_model(model)

    def put_subscription(self, subscription: ManagedSubscription) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneSubscriptionModel, str(subscription.account_id))
            if model is None:
                model = ControlPlaneSubscriptionModel(account_id=str(subscription.account_id), **_subscription_kwargs(subscription))
                session.add(model)
            else:
                for key, value in _subscription_kwargs(subscription).items():
                    setattr(model, key, value)
            session.flush()

    def get_billing_customer(self, account_id: str) -> ManagedBillingCustomer | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneBillingCustomerModel, str(account_id))
            return None if model is None else _billing_customer_from_model(model)

    def put_billing_customer(self, customer: ManagedBillingCustomer) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneBillingCustomerModel, str(customer.account_id))
            if model is None:
                model = ControlPlaneBillingCustomerModel(
                    account_id=str(customer.account_id),
                    organization_id=str(customer.organization_id),
                    stripe_customer_id=str(customer.stripe_customer_id),
                    created_at=_parse_timestamp(customer.created_at),
                    updated_at=_parse_timestamp(customer.updated_at),
                )
                session.add(model)
            else:
                model.organization_id = str(customer.organization_id)
                model.stripe_customer_id = str(customer.stripe_customer_id)
                model.created_at = _parse_timestamp(customer.created_at)
                model.updated_at = _parse_timestamp(customer.updated_at)
            session.flush()

    def get_billing_customer_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedBillingCustomer | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(ControlPlaneBillingCustomerModel)
                .where(ControlPlaneBillingCustomerModel.stripe_customer_id == str(stripe_customer_id))
                .limit(1)
            )
            return None if model is None else _billing_customer_from_model(model)

    def get_subscription_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedSubscription | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(ControlPlaneSubscriptionModel)
                .where(ControlPlaneSubscriptionModel.stripe_customer_id == str(stripe_customer_id))
                .limit(1)
            )
            return None if model is None else _subscription_from_model(model)

    def get_subscription_by_stripe_subscription_id(self, stripe_subscription_id: str) -> ManagedSubscription | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(ControlPlaneSubscriptionModel)
                .where(ControlPlaneSubscriptionModel.stripe_subscription_id == str(stripe_subscription_id))
                .limit(1)
            )
            return None if model is None else _subscription_from_model(model)

    def get_billing_event(self, event_id: str) -> ManagedBillingEvent | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneBillingEventModel, str(event_id))
            return None if model is None else _billing_event_from_model(model)

    def put_billing_event(self, event: ManagedBillingEvent) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneBillingEventModel, str(event.event_id))
            if model is None:
                model = ControlPlaneBillingEventModel(event_id=str(event.event_id), **_billing_event_kwargs(event))
                session.add(model)
            else:
                for key, value in _billing_event_kwargs(event).items():
                    setattr(model, key, value)
            session.flush()

    def get_trial_history(self, ein: str) -> ManagedTrialHistory | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneTrialHistoryModel, str(ein))
            return None if model is None else _trial_history_from_model(model)

    def put_trial_history(self, history: ManagedTrialHistory) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneTrialHistoryModel, str(history.ein))
            if model is None:
                model = ControlPlaneTrialHistoryModel(ein=str(history.ein), **_trial_history_kwargs(history))
                session.add(model)
            else:
                for key, value in _trial_history_kwargs(history).items():
                    setattr(model, key, value)
            session.flush()

    def list_api_keys(self, account_id: str) -> list[ManagedApiKey]:
        with control_plane_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(ControlPlaneApiKeyModel)
                .where(ControlPlaneApiKeyModel.account_id == str(account_id))
                .order_by(ControlPlaneApiKeyModel.created_at, ControlPlaneApiKeyModel.key_id)
            ).all()
            return [_api_key_model_from_model(model) for model in models]

    def get_api_key(self, account_id: str, key_id: str) -> tuple[ManagedApiKey, StoredApiKeyRecord] | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneApiKeyModel, str(key_id))
            if model is None or model.account_id != str(account_id):
                return None
            return _api_key_model_from_model(model), _api_key_record_from_model(model)

    def get_api_key_record(self, key_id: str) -> StoredApiKeyRecord | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneApiKeyModel, str(key_id))
            return None if model is None else _api_key_record_from_model(model)

    def put_api_key(self, model: ManagedApiKey, record: StoredApiKeyRecord) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            persisted = session.get(ControlPlaneApiKeyModel, str(model.key_id))
            if persisted is None:
                persisted = ControlPlaneApiKeyModel(key_id=str(model.key_id), **_api_key_kwargs(model, record))
                session.add(persisted)
            else:
                for key, value in _api_key_kwargs(model, record).items():
                    setattr(persisted, key, value)
            session.flush()

    def list_oauth_clients(self, account_id: str) -> list[ManagedOAuthClient]:
        with control_plane_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(ControlPlaneOAuthClientModel)
                .where(ControlPlaneOAuthClientModel.account_id == str(account_id))
                .order_by(ControlPlaneOAuthClientModel.created_at, ControlPlaneOAuthClientModel.client_id)
            ).all()
            return [_oauth_client_model_from_model(model) for model in models]

    def get_oauth_client(self, account_id: str, client_id: str) -> tuple[ManagedOAuthClient, StoredOAuthClientRecord] | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneOAuthClientModel, str(client_id))
            if model is None or model.account_id != str(account_id):
                return None
            return _oauth_client_model_from_model(model), _oauth_client_record_from_model(model)

    def get_oauth_client_record(self, client_id: str) -> StoredOAuthClientRecord | None:
        with control_plane_session_scope(self._session_factory) as session:
            model = session.get(ControlPlaneOAuthClientModel, str(client_id))
            return None if model is None else _oauth_client_record_from_model(model)

    def put_oauth_client(self, model: ManagedOAuthClient, record: StoredOAuthClientRecord) -> None:
        with control_plane_session_scope(self._session_factory) as session:
            persisted = session.get(ControlPlaneOAuthClientModel, str(model.client_id))
            if persisted is None:
                persisted = ControlPlaneOAuthClientModel(client_id=str(model.client_id), **_oauth_client_kwargs(model, record))
                session.add(persisted)
            else:
                for key, value in _oauth_client_kwargs(model, record).items():
                    setattr(persisted, key, value)
            session.flush()

    def get_usage(self, account_id: str, month_key: str) -> int:
        with control_plane_session_scope(self._session_factory) as session:
            model = _usage_lookup(session, account_id=str(account_id), month_key=str(month_key))
            return 0 if model is None else int(model.request_count)

    def increment_usage(self, account_id: str, month_key: str, units: int = 1) -> int:
        delta = max(0, int(units))
        with control_plane_session_scope(self._session_factory) as session:
            model = _usage_lookup(session, account_id=str(account_id), month_key=str(month_key))
            if model is None:
                model = ControlPlaneUsageMonthlyModel(
                    account_id=str(account_id),
                    month_key=str(month_key),
                    request_count=delta,
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(model)
            else:
                model.request_count = int(model.request_count or 0) + delta
                model.updated_at = datetime.now(timezone.utc)
            session.flush()
            return int(model.request_count)

    def increment(self, account_id: str, month_key: str) -> None:
        self.increment_usage(account_id, month_key, units=1)


def _usage_lookup(session: Session, *, account_id: str, month_key: str) -> ControlPlaneUsageMonthlyModel | None:
    return session.scalar(
        select(ControlPlaneUsageMonthlyModel)
        .where(
            ControlPlaneUsageMonthlyModel.account_id == str(account_id),
            ControlPlaneUsageMonthlyModel.month_key == str(month_key),
        )
        .limit(1)
    )


def _account_from_model(model: ControlPlaneAccountModel) -> Account:
    return Account(
        id=model.account_id,
        name=model.name,
        status=model.status,
        created_at=_format_timestamp(model.created_at) or "",
        ein=model.ein,
    )


def _subscription_kwargs(subscription: ManagedSubscription) -> dict[str, Any]:
    return {
        "plan_code": subscription.plan_code,
        "status": subscription.status,
        "created_at": _parse_optional_timestamp(subscription.created_at),
        "effective_from": _parse_optional_timestamp(subscription.effective_from),
        "effective_to": _parse_optional_timestamp(subscription.effective_to),
        "stripe_customer_id": subscription.stripe_customer_id,
        "stripe_subscription_id": subscription.stripe_subscription_id,
        "billing_status": subscription.billing_status,
        "billing_period_start": _parse_optional_timestamp(subscription.billing_period_start),
        "billing_period_end": _parse_optional_timestamp(subscription.billing_period_end),
        "grace_period_ends_at": _parse_optional_timestamp(subscription.grace_period_ends_at),
        "trial_status": subscription.trial_status,
        "trial_started_at": _parse_optional_timestamp(subscription.trial_started_at),
        "trial_ends_at": _parse_optional_timestamp(subscription.trial_ends_at),
        "trial_trigger_event": subscription.trial_trigger_event,
        "trial_consumed": bool(subscription.trial_consumed),
        "trial_termination_reason": subscription.trial_termination_reason,
        "pending_plan_code": subscription.pending_plan_code,
        "pending_plan_effective_at": _parse_optional_timestamp(subscription.pending_plan_effective_at),
        "cancel_at_period_end": bool(subscription.cancel_at_period_end),
        "stripe_subscription_schedule_id": subscription.stripe_subscription_schedule_id,
        "pending_checkout_session_id": subscription.pending_checkout_session_id,
        "pending_checkout_session_url": subscription.pending_checkout_session_url,
        "pending_checkout_expires_at": _parse_optional_timestamp(subscription.pending_checkout_expires_at),
        "updated_at": _parse_optional_timestamp(subscription.updated_at),
    }


def _subscription_from_model(model: ControlPlaneSubscriptionModel) -> ManagedSubscription:
    return ManagedSubscription(
        account_id=model.account_id,
        plan_code=model.plan_code,
        status=model.status,
        created_at=_format_timestamp(model.created_at),
        effective_from=_format_timestamp(model.effective_from),
        effective_to=_format_timestamp(model.effective_to),
        stripe_customer_id=model.stripe_customer_id,
        stripe_subscription_id=model.stripe_subscription_id,
        billing_status=model.billing_status,
        billing_period_start=_format_timestamp(model.billing_period_start),
        billing_period_end=_format_timestamp(model.billing_period_end),
        grace_period_ends_at=_format_timestamp(model.grace_period_ends_at),
        trial_status=model.trial_status,
        trial_started_at=_format_timestamp(model.trial_started_at),
        trial_ends_at=_format_timestamp(model.trial_ends_at),
        trial_trigger_event=model.trial_trigger_event,
        trial_consumed=bool(model.trial_consumed),
        trial_termination_reason=model.trial_termination_reason,
        pending_plan_code=model.pending_plan_code,
        pending_plan_effective_at=_format_timestamp(model.pending_plan_effective_at),
        cancel_at_period_end=bool(model.cancel_at_period_end),
        stripe_subscription_schedule_id=model.stripe_subscription_schedule_id,
        pending_checkout_session_id=model.pending_checkout_session_id,
        pending_checkout_session_url=model.pending_checkout_session_url,
        pending_checkout_expires_at=_format_timestamp(model.pending_checkout_expires_at),
        updated_at=_format_timestamp(model.updated_at),
    )


def _billing_customer_from_model(model: ControlPlaneBillingCustomerModel) -> ManagedBillingCustomer:
    return ManagedBillingCustomer(
        account_id=model.account_id,
        organization_id=model.organization_id,
        stripe_customer_id=model.stripe_customer_id,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _billing_event_kwargs(event: ManagedBillingEvent) -> dict[str, Any]:
    return {
        "event_type": event.event_type,
        "processed_at": _parse_timestamp(event.processed_at),
        "account_id": event.account_id,
        "processing_outcome": event.processing_outcome,
        "stripe_customer_id": event.stripe_customer_id,
        "stripe_subscription_id": event.stripe_subscription_id,
        "stripe_invoice_id": event.stripe_invoice_id,
        "gross_amount": event.gross_amount,
        "tax_amount": event.tax_amount,
        "invoice_total": event.invoice_total,
        "currency": event.currency,
        "webhook_created_at": _parse_optional_timestamp(event.webhook_created_at),
        "payload_fingerprint": event.payload_fingerprint,
    }


def _billing_event_from_model(model: ControlPlaneBillingEventModel) -> ManagedBillingEvent:
    return ManagedBillingEvent(
        event_id=model.event_id,
        event_type=model.event_type,
        processed_at=_format_timestamp(model.processed_at) or "",
        account_id=model.account_id,
        processing_outcome=model.processing_outcome,
        stripe_customer_id=model.stripe_customer_id,
        stripe_subscription_id=model.stripe_subscription_id,
        stripe_invoice_id=model.stripe_invoice_id,
        gross_amount=model.gross_amount,
        tax_amount=model.tax_amount,
        invoice_total=model.invoice_total,
        currency=model.currency,
        webhook_created_at=_format_timestamp(model.webhook_created_at),
        payload_fingerprint=model.payload_fingerprint,
    )


def _trial_history_kwargs(history: ManagedTrialHistory) -> dict[str, Any]:
    return {
        "trial_consumed": bool(history.trial_consumed),
        "first_account_id": history.first_account_id,
        "last_account_id": history.last_account_id,
        "trial_started_at": _parse_optional_timestamp(history.trial_started_at),
        "trial_ended_at": _parse_optional_timestamp(history.trial_ended_at),
        "last_status": history.last_status,
        "last_termination_reason": history.last_termination_reason,
        "updated_at": _parse_optional_timestamp(history.updated_at),
    }


def _trial_history_from_model(model: ControlPlaneTrialHistoryModel) -> ManagedTrialHistory:
    return ManagedTrialHistory(
        ein=model.ein,
        trial_consumed=bool(model.trial_consumed),
        first_account_id=model.first_account_id,
        last_account_id=model.last_account_id,
        trial_started_at=_format_timestamp(model.trial_started_at),
        trial_ended_at=_format_timestamp(model.trial_ended_at),
        last_status=model.last_status,
        last_termination_reason=model.last_termination_reason,
        updated_at=_format_timestamp(model.updated_at),
    )


def _api_key_kwargs(model: ManagedApiKey, record: StoredApiKeyRecord) -> dict[str, Any]:
    return {
        "account_id": model.account_id,
        "workspace_id": record.workspace_id,
        "scopes": list(record.scopes),
        "status": model.status,
        "created_at": _parse_timestamp(model.created_at),
        "secret_hash": record.secret_hash,
        "plan_id": record.plan_id,
        "rate_limit_profile": record.rate_limit_profile,
        "revoked": bool(record.revoked),
    }


def _api_key_model_from_model(model: ControlPlaneApiKeyModel) -> ManagedApiKey:
    return ManagedApiKey(
        key_id=model.key_id,
        account_id=model.account_id,
        status=model.status,
        created_at=_format_timestamp(model.created_at) or "",
        plan=model.plan_id,
        scopes=tuple(model.scopes or []),
        rate_limit_profile=model.rate_limit_profile,
    )


def _api_key_record_from_model(model: ControlPlaneApiKeyModel) -> StoredApiKeyRecord:
    return StoredApiKeyRecord(
        key_id=model.key_id,
        secret_hash=model.secret_hash,
        account_id=model.account_id,
        workspace_id=model.workspace_id,
        scopes=tuple(model.scopes or []),
        revoked=bool(model.revoked),
        plan_id=model.plan_id,
        rate_limit_profile=model.rate_limit_profile,
    )


def _oauth_client_kwargs(model: ManagedOAuthClient, record: StoredOAuthClientRecord) -> dict[str, Any]:
    return {
        "account_id": model.account_id,
        "workspace_id": record.workspace_id,
        "scopes": list(record.scopes),
        "status": model.status,
        "created_at": _parse_timestamp(model.created_at),
        "client_secret_hash": record.client_secret_hash,
        "plan_id": record.plan_id,
        "rate_limit_profile": record.rate_limit_profile,
        "revoked": bool(record.revoked),
    }


def _oauth_client_model_from_model(model: ControlPlaneOAuthClientModel) -> ManagedOAuthClient:
    return ManagedOAuthClient(
        client_id=model.client_id,
        account_id=model.account_id,
        status=model.status,
        created_at=_format_timestamp(model.created_at) or "",
        plan=model.plan_id,
        scopes=tuple(model.scopes or []),
        rate_limit_profile=model.rate_limit_profile,
    )


def _oauth_client_record_from_model(model: ControlPlaneOAuthClientModel) -> StoredOAuthClientRecord:
    return StoredOAuthClientRecord(
        client_id=model.client_id,
        client_secret_hash=model.client_secret_hash,
        account_id=model.account_id,
        workspace_id=model.workspace_id,
        scopes=tuple(model.scopes or []),
        revoked=bool(model.revoked),
        plan_id=model.plan_id,
        rate_limit_profile=model.rate_limit_profile,
    )


def _parse_timestamp(value: str) -> datetime:
    normalized = str(value or "").strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_optional_timestamp(value: str | None) -> datetime | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    return _parse_timestamp(candidate)


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def build_control_plane_session_factory(bind: Engine | str) -> sessionmaker[Session]:
    engine = bind if isinstance(bind, Engine) else create_engine(bind, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)

