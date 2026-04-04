"""Phase 27J widen nonprofit filing financial columns to BIGINT

Revision ID: 20260404_000007
Revises: 20260403_000006
Create Date: 2026-04-04 14:00:07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260404_000007"
down_revision = "20260403_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("nonprofit_filings") as batch_op:
        batch_op.alter_column("total_assets", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=True)
        batch_op.alter_column("total_income", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=True)
        batch_op.alter_column("total_revenue", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("nonprofit_filings") as batch_op:
        batch_op.alter_column("total_revenue", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=True)
        batch_op.alter_column("total_income", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=True)
        batch_op.alter_column("total_assets", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=True)
