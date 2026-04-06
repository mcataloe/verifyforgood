"""Widen nonprofit NTEE category storage for EO/BMF canonical labels.

Revision ID: 20260405_000012
Revises: 20260404_000011
Create Date: 2026-04-05 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260405_000012"
down_revision = "20260404_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "nonprofits",
        "ntee_category",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "nonprofits",
        "ntee_category",
        existing_type=sa.String(length=128),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
