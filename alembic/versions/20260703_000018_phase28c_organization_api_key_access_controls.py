"""Phase 28C organization API key permission level, expiry, and CIDR allowlist

Revision ID: 20260703_000018
Revises: 20260420_000017
Create Date: 2026-07-03 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260703_000018"
down_revision = "20260420_000017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_api_keys",
        sa.Column("permission_level", sa.String(length=32), nullable=False, server_default="full_access"),
    )
    op.alter_column("organization_api_keys", "permission_level", server_default=None)
    op.add_column(
        "organization_api_keys",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_api_keys",
        sa.Column("allowed_cidr", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organization_api_keys", "allowed_cidr")
    op.drop_column("organization_api_keys", "expires_at")
    op.drop_column("organization_api_keys", "permission_level")
