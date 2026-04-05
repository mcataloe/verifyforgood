"""Phase 27M generated BIGINT PKs for customer-account tables

Revision ID: 20260404_000010
Revises: 20260404_000009
Create Date: 2026-04-04 23:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260404_000010"
down_revision = "20260404_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_table("organization_audit_logs")
    op.drop_table("organization_api_keys")
    op.drop_table("organization_subscriptions")
    op.drop_table("plans")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    op.drop_table("users")

    _create_customer_account_tables(dialect_name=dialect_name)


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_table("organization_audit_logs")
    op.drop_table("organization_api_keys")
    op.drop_table("organization_subscriptions")
    op.drop_table("plans")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
    op.drop_table("users")

    _create_legacy_customer_account_tables(dialect_name=dialect_name)


def _create_customer_account_tables(*, dialect_name: str) -> None:
    bigint_type = _bigint_for_dialect(dialect_name)

    op.create_table(
        "users",
        sa.Column("user_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("identity_provider_type", sa.String(length=64), nullable=False),
        sa.Column("external_subject_id", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
    )
    op.create_index("ix_users_normalized_email", "users", ["normalized_email"], unique=False)

    op.create_table(
        "organizations",
        sa.Column("organization_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", bigint_type, nullable=True),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=False)

    op.create_table(
        "organization_memberships",
        sa.Column("membership_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("user_id", bigint_type, nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_memberships_organization_id_organizations"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_organization_memberships_user_id_users"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_memberships_organization_user"),
    )
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False)

    op.create_table(
        "plans",
        sa.Column("plan_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("plan_name", sa.String(length=255), nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("monthly_price", sa.Integer(), nullable=False),
        sa.Column("feature_flags", sa.JSON(), nullable=False),
        sa.Column("request_limit", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.UniqueConstraint("plan_code", name="uq_plans_plan_code"),
    )
    op.create_index("ix_plans_plan_code", "plans", ["plan_code"], unique=False)

    op.create_table(
        "organization_subscriptions",
        sa.Column("subscription_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("plan_id", bigint_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("billing_cycle_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("billing_cycle_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pending_plan_id", bigint_type, nullable=True),
        sa.Column("pending_plan_effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_status", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_subscriptions_organization_id_organizations"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.plan_id"], name="fk_organization_subscriptions_plan_id_plans"),
        sa.UniqueConstraint("organization_id", name="uq_organization_subscriptions_organization_id"),
    )

    op.create_table(
        "organization_api_keys",
        sa.Column("key_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("hashed_key_value", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", bigint_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_api_keys_organization_id_organizations"),
    )
    op.create_index("ix_organization_api_keys_organization_id", "organization_api_keys", ["organization_id"], unique=False)

    op.create_table(
        "organization_audit_logs",
        sa.Column("audit_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", bigint_type, nullable=True),
        sa.Column("organization_id", bigint_type, nullable=True),
        sa.Column("target_user_id", bigint_type, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_audit_logs_organization_id_organizations"),
    )
    op.create_index(
        "ix_organization_audit_logs_organization_timestamp",
        "organization_audit_logs",
        ["organization_id", "timestamp"],
        unique=False,
    )
    op.create_index("ix_organization_audit_logs_timestamp", "organization_audit_logs", ["timestamp"], unique=False)


def _create_legacy_customer_account_tables(*, dialect_name: str) -> None:
    string_id = sa.String(length=64)

    op.create_table(
        "users",
        sa.Column("user_id", string_id, primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("identity_provider_type", sa.String(length=64), nullable=False),
        sa.Column("external_subject_id", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
    )
    op.create_index("ix_users_normalized_email", "users", ["normalized_email"], unique=False)

    op.create_table(
        "organizations",
        sa.Column("organization_id", string_id, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", string_id, nullable=True),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=False)

    op.create_table(
        "organization_memberships",
        sa.Column("organization_id", string_id, nullable=False),
        sa.Column("user_id", string_id, nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_memberships_organization_id_organizations"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_organization_memberships_user_id_users"),
        sa.PrimaryKeyConstraint("organization_id", "user_id", name="pk_organization_memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_memberships_organization_user"),
    )
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False)

    op.create_table(
        "plans",
        sa.Column("plan_id", string_id, primary_key=True, nullable=False),
        sa.Column("plan_name", sa.String(length=255), nullable=False),
        sa.Column("monthly_price", sa.Integer(), nullable=False),
        sa.Column("feature_flags", sa.JSON(), nullable=False),
        sa.Column("request_limit", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )

    op.create_table(
        "organization_subscriptions",
        sa.Column("subscription_id", string_id, primary_key=True, nullable=False),
        sa.Column("organization_id", string_id, nullable=False),
        sa.Column("plan_id", string_id, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("billing_cycle_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("billing_cycle_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pending_plan_id", string_id, nullable=True),
        sa.Column("pending_plan_effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_status", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_subscriptions_organization_id_organizations"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.plan_id"], name="fk_organization_subscriptions_plan_id_plans"),
        sa.UniqueConstraint("organization_id", name="uq_organization_subscriptions_organization_id"),
    )

    op.create_table(
        "organization_api_keys",
        sa.Column("key_id", string_id, primary_key=True, nullable=False),
        sa.Column("organization_id", string_id, nullable=False),
        sa.Column("hashed_key_value", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", string_id, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_api_keys_organization_id_organizations"),
    )
    op.create_index("ix_organization_api_keys_organization_id", "organization_api_keys", ["organization_id"], unique=False)

    op.create_table(
        "organization_audit_logs",
        sa.Column("audit_id", string_id, primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", string_id, nullable=True),
        sa.Column("organization_id", string_id, nullable=True),
        sa.Column("target_user_id", string_id, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_audit_logs_organization_id_organizations"),
    )
    op.create_index(
        "ix_organization_audit_logs_organization_timestamp",
        "organization_audit_logs",
        ["organization_id", "timestamp"],
        unique=False,
    )
    op.create_index("ix_organization_audit_logs_timestamp", "organization_audit_logs", ["timestamp"], unique=False)


def _bigint_for_dialect(dialect_name: str) -> sa.types.TypeEngine:
    return sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()
