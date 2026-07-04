"""Phase 28D drop legacy platform nonprofit tables

Revision ID: 20260703_000019
Revises: 20260703_000018
Create Date: 2026-07-03 12:00:00

These seven tables were created by early, now-superseded migrations in this
chain (Phase 24E/24F/24G/27F/27J/27K/27L/27N/27O/27P/27Q) before nonprofit
data was split onto its own dedicated database, managed by the
``alembic_nonprofit`` migration chain. That dedicated database now holds a
confirmed superset of this data (more rows in every table, and no EIN present
here that is missing there), so these copies are stale spillover rather than
a unique source of data.
"""

from __future__ import annotations

from alembic import op


revision = "20260703_000019"
down_revision = "20260703_000018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dropped in FK-safe order (dependents before the tables they reference).
    op.drop_table("nonprofit_raw_filings")
    op.drop_table("nonprofit_filings")
    op.drop_table("nonprofit_sources")
    op.drop_table("compliance_checks")
    op.drop_table("form990_extracted_files")
    op.drop_table("nonprofits")
    op.drop_table("form990_archives")


def downgrade() -> None:
    raise NotImplementedError("Phase 28D is destructive and not intended to be downgraded.")
