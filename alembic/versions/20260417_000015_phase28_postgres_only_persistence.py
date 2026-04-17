"""Phase 28 PostgreSQL-only persistence tables

Revision ID: 20260417_000015
Revises: 20260407_000014
Create Date: 2026-04-17 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_000015"
down_revision = "20260407_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    bigint_type = _bigint_for_dialect(dialect_name)

    op.create_table(
        "organization_invitations",
        sa.Column("invitation_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("invited_by_user_id", bigint_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_invitations_organization_id_organizations"),
        sa.UniqueConstraint("token", name="uq_organization_invitations_token"),
    )
    op.create_index("ix_organization_invitations_organization_id", "organization_invitations", ["organization_id"], unique=False)
    op.create_index("ix_organization_invitations_normalized_email", "organization_invitations", ["normalized_email"], unique=False)

    op.create_table(
        "organization_usage_monthly",
        sa.Column("usage_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("metric_type", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.String(length=16), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_usage_monthly_organization_id_organizations"),
        sa.UniqueConstraint("organization_id", "metric_type", "period_month", name="uq_organization_usage_monthly_org_metric_period"),
    )
    op.create_index(
        "ix_organization_usage_monthly_organization_period",
        "organization_usage_monthly",
        ["organization_id", "period_month"],
        unique=False,
    )

    op.create_table(
        "organization_feature_flags",
        sa.Column("feature_flag_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("flag_key", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_feature_flags_organization_id_organizations"),
        sa.UniqueConstraint("organization_id", "flag_key", name="uq_organization_feature_flags_org_flag"),
    )
    op.create_index("ix_organization_feature_flags_organization_id", "organization_feature_flags", ["organization_id"], unique=False)

    op.create_table(
        "organization_settings",
        sa.Column("settings_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=True),
        sa.Column("account_id", sa.String(length=128), nullable=True),
        sa.Column("integrations", sa.JSON(), nullable=False),
        sa.Column("billing_allow_overage", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("billing_monthly_request_cap", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], name="fk_organization_settings_organization_id_organizations"),
        sa.UniqueConstraint("organization_id", name="uq_organization_settings_organization_id"),
        sa.UniqueConstraint("workspace_id", name="uq_organization_settings_workspace_id"),
        sa.UniqueConstraint("account_id", name="uq_organization_settings_account_id"),
    )

    op.create_table(
        "control_plane_accounts",
        sa.Column("account_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ein", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "control_plane_subscriptions",
        sa.Column("account_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("plan_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("billing_status", sa.String(length=64), nullable=True),
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_status", sa.String(length=64), nullable=True),
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_trigger_event", sa.String(length=128), nullable=True),
        sa.Column("trial_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trial_termination_reason", sa.String(length=128), nullable=True),
        sa.Column("pending_plan_code", sa.String(length=64), nullable=True),
        sa.Column("pending_plan_effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stripe_subscription_schedule_id", sa.String(length=255), nullable=True),
        sa.Column("pending_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("pending_checkout_session_url", sa.Text(), nullable=True),
        sa.Column("pending_checkout_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["control_plane_accounts.account_id"], name="fk_control_plane_subscriptions_account_id_control_plane_accounts"),
        sa.UniqueConstraint("stripe_customer_id", name="uq_control_plane_subscriptions_stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id", name="uq_control_plane_subscriptions_stripe_subscription_id"),
    )

    op.create_table(
        "control_plane_billing_customers",
        sa.Column("account_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["control_plane_accounts.account_id"], name="fk_control_plane_billing_customers_account_id_control_plane_accounts"),
        sa.UniqueConstraint("stripe_customer_id", name="uq_control_plane_billing_customers_stripe_customer_id"),
    )

    op.create_table(
        "control_plane_billing_events",
        sa.Column("event_id", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=True),
        sa.Column("processing_outcome", sa.String(length=128), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("gross_amount", sa.Integer(), nullable=True),
        sa.Column("tax_amount", sa.Integer(), nullable=True),
        sa.Column("invoice_total", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("webhook_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_fingerprint", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_control_plane_billing_events_account_id", "control_plane_billing_events", ["account_id"], unique=False)
    op.create_index("ix_control_plane_billing_events_stripe_customer_id", "control_plane_billing_events", ["stripe_customer_id"], unique=False)
    op.create_index("ix_control_plane_billing_events_stripe_subscription_id", "control_plane_billing_events", ["stripe_subscription_id"], unique=False)

    op.create_table(
        "control_plane_trial_histories",
        sa.Column("ein", sa.String(length=32), primary_key=True, nullable=False),
        sa.Column("trial_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_account_id", sa.String(length=128), nullable=True),
        sa.Column("last_account_id", sa.String(length=128), nullable=True),
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=64), nullable=True),
        sa.Column("last_termination_reason", sa.String(length=128), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "control_plane_api_keys",
        sa.Column("key_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("rate_limit_profile", sa.String(length=64), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["account_id"], ["control_plane_accounts.account_id"], name="fk_control_plane_api_keys_account_id_control_plane_accounts"),
    )
    op.create_index("ix_control_plane_api_keys_account_id", "control_plane_api_keys", ["account_id"], unique=False)

    op.create_table(
        "control_plane_oauth_clients",
        sa.Column("client_id", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_secret_hash", sa.String(length=255), nullable=False),
        sa.Column("plan_id", sa.String(length=64), nullable=False),
        sa.Column("rate_limit_profile", sa.String(length=64), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["account_id"], ["control_plane_accounts.account_id"], name="fk_control_plane_oauth_clients_account_id_control_plane_accounts"),
    )
    op.create_index("ix_control_plane_oauth_clients_account_id", "control_plane_oauth_clients", ["account_id"], unique=False)

    op.create_table(
        "control_plane_usage_monthly",
        sa.Column("usage_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("month_key", sa.String(length=16), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["control_plane_accounts.account_id"], name="fk_control_plane_usage_monthly_account_id_control_plane_accounts"),
        sa.UniqueConstraint("account_id", "month_key", name="uq_control_plane_usage_account_month"),
    )


def downgrade() -> None:
    op.drop_table("control_plane_usage_monthly")
    op.drop_index("ix_control_plane_oauth_clients_account_id", table_name="control_plane_oauth_clients")
    op.drop_table("control_plane_oauth_clients")
    op.drop_index("ix_control_plane_api_keys_account_id", table_name="control_plane_api_keys")
    op.drop_table("control_plane_api_keys")
    op.drop_table("control_plane_trial_histories")
    op.drop_index("ix_control_plane_billing_events_stripe_subscription_id", table_name="control_plane_billing_events")
    op.drop_index("ix_control_plane_billing_events_stripe_customer_id", table_name="control_plane_billing_events")
    op.drop_index("ix_control_plane_billing_events_account_id", table_name="control_plane_billing_events")
    op.drop_table("control_plane_billing_events")
    op.drop_table("control_plane_billing_customers")
    op.drop_table("control_plane_subscriptions")
    op.drop_table("control_plane_accounts")
    op.drop_table("organization_settings")
    op.drop_index("ix_organization_feature_flags_organization_id", table_name="organization_feature_flags")
    op.drop_table("organization_feature_flags")
    op.drop_index("ix_organization_usage_monthly_organization_period", table_name="organization_usage_monthly")
    op.drop_table("organization_usage_monthly")
    op.drop_index("ix_organization_invitations_normalized_email", table_name="organization_invitations")
    op.drop_index("ix_organization_invitations_organization_id", table_name="organization_invitations")
    op.drop_table("organization_invitations")


def _bigint_for_dialect(dialect_name: str) -> sa.types.TypeEngine:
    return sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()
