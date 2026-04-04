"""Phase 27I subscription billing projection fields

Revision ID: 20260403_000006
Revises: 20260403_000005
Create Date: 2026-04-03 12:00:06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260403_000006"
down_revision = "20260403_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organization_subscriptions", sa.Column("pending_plan_id", sa.String(length=64), nullable=True))
    op.add_column("organization_subscriptions", sa.Column("pending_plan_effective_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "organization_subscriptions",
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("organization_subscriptions", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organization_subscriptions", sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organization_subscriptions", sa.Column("billing_status", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("organization_subscriptions", "billing_status")
    op.drop_column("organization_subscriptions", "grace_period_ends_at")
    op.drop_column("organization_subscriptions", "updated_at")
    op.drop_column("organization_subscriptions", "cancel_at_period_end")
    op.drop_column("organization_subscriptions", "pending_plan_effective_at")
    op.drop_column("organization_subscriptions", "pending_plan_id")
