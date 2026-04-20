"""Phase 28B support ticket email delivery

Revision ID: 20260420_000017
Revises: 20260418_000016
Create Date: 2026-04-20 10:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260420_000017"
down_revision = "20260418_000016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_support_tickets",
        sa.Column("ticket_id", sa.BigInteger(), sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("support_request_id", sa.String(length=128), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("account_id", sa.String(length=128), nullable=True),
        sa.Column("workspace_id", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reply_email", sa.String(length=320), nullable=True),
        sa.Column("watchers", sa.JSON(), nullable=False),
        sa.Column("route_hash", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("current_plan", sa.String(length=64), nullable=True),
        sa.Column("membership_role", sa.String(length=32), nullable=True),
        sa.Column("delivery_mode", sa.String(length=64), nullable=False),
        sa.Column("delivery_provider", sa.String(length=64), nullable=False),
        sa.Column("delivery_status", sa.String(length=32), nullable=False),
        sa.Column("delivery_recipient", sa.String(length=320), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("delivery_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name=op.f("fk_organization_support_tickets_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("ticket_id", name=op.f("pk_organization_support_tickets")),
        sa.UniqueConstraint(
            "support_request_id",
            name="uq_organization_support_tickets_support_request_id",
        ),
    )
    op.create_index(
        "ix_organization_support_tickets_organization_created",
        "organization_support_tickets",
        ["organization_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_organization_support_tickets_delivery_status",
        "organization_support_tickets",
        ["delivery_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_organization_support_tickets_delivery_status", table_name="organization_support_tickets")
    op.drop_index("ix_organization_support_tickets_organization_created", table_name="organization_support_tickets")
    op.drop_table("organization_support_tickets")
