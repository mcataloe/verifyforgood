from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .sqlalchemy_db import CustomerAccountsBase


class UserModel(CustomerAccountsBase):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_provider_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_subject_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    memberships: Mapped[list["OrganizationMembershipModel"]] = relationship(back_populates="user")


class OrganizationModel(CustomerAccountsBase):
    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    memberships: Mapped[list["OrganizationMembershipModel"]] = relationship(back_populates="organization")
    subscriptions: Mapped[list["OrganizationSubscriptionModel"]] = relationship(back_populates="organization")
    api_keys: Mapped[list["OrganizationApiKeyModel"]] = relationship(back_populates="organization")
    audit_logs: Mapped[list["OrganizationAuditLogModel"]] = relationship(back_populates="organization")


class OrganizationMembershipModel(CustomerAccountsBase):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_memberships_organization_user"),
        Index("ix_organization_memberships_user_id", "user_id"),
    )

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    organization: Mapped[OrganizationModel] = relationship(back_populates="memberships")
    user: Mapped[UserModel] = relationship(back_populates="memberships")


class PlanModel(CustomerAccountsBase):
    __tablename__ = "plans"

    plan_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_name: Mapped[str] = mapped_column(String(255), nullable=False)
    monthly_price: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    request_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class OrganizationSubscriptionModel(CustomerAccountsBase):
    __tablename__ = "organization_subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_organization_subscriptions_organization_id"),
    )

    subscription_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.plan_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    billing_cycle_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    billing_cycle_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pending_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_plan_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    organization: Mapped[OrganizationModel] = relationship(back_populates="subscriptions")


class OrganizationApiKeyModel(CustomerAccountsBase):
    __tablename__ = "organization_api_keys"
    __table_args__ = (
        Index("ix_organization_api_keys_organization_id", "organization_id"),
    )

    key_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False)
    hashed_key_value: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[OrganizationModel] = relationship(back_populates="api_keys")


class OrganizationAuditLogModel(CustomerAccountsBase):
    __tablename__ = "organization_audit_logs"
    __table_args__ = (
        Index("ix_organization_audit_logs_organization_timestamp", "organization_id", "timestamp"),
        Index("ix_organization_audit_logs_timestamp", "timestamp"),
    )

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.organization_id"), nullable=True)
    target_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)

    organization: Mapped[OrganizationModel | None] = relationship(back_populates="audit_logs")
