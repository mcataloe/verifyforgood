"""Phase 27Q canonical nonprofit raw filing storage

Revision ID: 20260407_000014
Revises: 20260405_000013
Create Date: 2026-04-07 00:00:14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260407_000014"
down_revision = "20260405_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    bigint_type = sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()

    op.create_table(
        "nonprofit_raw_filings",
        sa.Column("raw_filing_id", bigint_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("nonprofit_id", bigint_type, nullable=False),
        sa.Column("filing_id", bigint_type, nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("form_type", sa.String(length=32), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=True),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("source_signature", sa.String(length=128), nullable=True),
        sa.Column("xml_content_hash", sa.String(length=128), nullable=False),
        sa.Column("xml_artifact_reference", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.String(length=32), nullable=True),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("canonicalization_version", sa.String(length=64), nullable=False),
        sa.Column("raw_filing_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["nonprofit_id"],
            ["nonprofits.nonprofit_id"],
            name="fk_nonprofit_raw_filings_nonprofit_id_nonprofits",
        ),
        sa.ForeignKeyConstraint(
            ["filing_id"],
            ["nonprofit_filings.filing_id"],
            name="fk_nonprofit_raw_filings_filing_id_nonprofit_filings",
        ),
        sa.UniqueConstraint(
            "filing_id",
            "xml_content_hash",
            name="uq_nonprofit_raw_filings_filing_hash",
        ),
    )
    op.create_index(
        "ix_nonprofit_raw_filings_nonprofit_form_year",
        "nonprofit_raw_filings",
        ["nonprofit_id", "form_type", "tax_year", "filing_date"],
        unique=False,
    )
    op.create_index(
        "ix_nonprofit_raw_filings_filing_latest",
        "nonprofit_raw_filings",
        ["filing_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_nonprofit_raw_filings_filing_latest", table_name="nonprofit_raw_filings")
    op.drop_index("ix_nonprofit_raw_filings_nonprofit_form_year", table_name="nonprofit_raw_filings")
    op.drop_table("nonprofit_raw_filings")
