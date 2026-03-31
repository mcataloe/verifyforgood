"""Phase 24F nonprofit ingest persistence columns

Revision ID: 20260331_000003
Revises: 20260331_000002
Create Date: 2026-03-31 00:00:03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260331_000003"
down_revision = "20260331_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nonprofit_filings", sa.Column("source_signature", sa.String(length=128), nullable=True))
    op.add_column("nonprofit_filings", sa.Column("xml_source_reference", sa.Text(), nullable=True))
    op.add_column("nonprofit_filings", sa.Column("raw_s3_key", sa.Text(), nullable=True))
    op.add_column("nonprofit_sources", sa.Column("source_signature", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("nonprofit_sources", "source_signature")
    op.drop_column("nonprofit_filings", "raw_s3_key")
    op.drop_column("nonprofit_filings", "xml_source_reference")
    op.drop_column("nonprofit_filings", "source_signature")
