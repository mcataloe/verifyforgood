"""Phase 24G nonprofit query optimization indexes

Revision ID: 20260331_000004
Revises: 20260331_000003
Create Date: 2026-03-31 00:00:04
"""

from __future__ import annotations

from alembic import op


revision = "20260331_000004"
down_revision = "20260331_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.create_index(
        "ix_nonprofits_normalized_name_ein",
        "nonprofits",
        ["normalized_name", "ein"],
        unique=False,
    )
    op.create_index(
        "ix_nonprofit_filings_nonprofit_latest",
        "nonprofit_filings",
        ["nonprofit_id", "tax_year", "filing_date", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_compliance_checks_nonprofit_type_evaluated",
        "compliance_checks",
        ["nonprofit_id", "check_type", "evaluated_at"],
        unique=False,
    )
    if dialect_name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_nonprofits_normalized_name_trgm "
            "ON nonprofits USING gin (normalized_name gin_trgm_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_nonprofits_normalized_name_trgm")
    op.drop_index("ix_compliance_checks_nonprofit_type_evaluated", table_name="compliance_checks")
    op.drop_index("ix_nonprofit_filings_nonprofit_latest", table_name="nonprofit_filings")
    op.drop_index("ix_nonprofits_normalized_name_ein", table_name="nonprofits")
