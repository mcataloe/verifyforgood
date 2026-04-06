"""Widen nonprofit entity type storage for EO/BMF subsection labels.

Revision ID: 20260405_000013
Revises: 20260405_000012
Create Date: 2026-04-05 12:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260405_000013"
down_revision = "20260405_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "nonprofits",
        "entity_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "nonprofits",
        "entity_type",
        existing_type=sa.String(length=128),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
