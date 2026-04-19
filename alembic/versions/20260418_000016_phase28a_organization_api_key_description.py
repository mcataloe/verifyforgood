"""Phase 28A organization API key description metadata

Revision ID: 20260418_000016
Revises: 20260417_000015
Create Date: 2026-04-18 14:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260418_000016"
down_revision = "20260417_000015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_api_keys",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("organization_api_keys", "description", server_default=None)


def downgrade() -> None:
    op.drop_column("organization_api_keys", "description")
