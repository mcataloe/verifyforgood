"""Phase 27N local-runtime Form 990 metadata cutover

Revision ID: 20260404_000011
Revises: 20260404_000010
Create Date: 2026-04-04 23:55:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260404_000011"
down_revision = "20260404_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    pk_type = sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()

    op.drop_table("form990_extracted_files")
    op.drop_table("form990_archives")
    op.drop_index("ix_nonprofit_filings_nonprofit_source", table_name="nonprofit_filings")
    op.drop_index("ix_nonprofit_filings_nonprofit_latest", table_name="nonprofit_filings")
    op.drop_index("ix_nonprofit_filings_nonprofit_tax_year", table_name="nonprofit_filings")
    op.drop_table("nonprofit_filings")

    op.create_table(
        "nonprofit_filings",
        sa.Column("filing_id", pk_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("nonprofit_id", pk_type, nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=True),
        sa.Column("tax_period", sa.String(length=16), nullable=True),
        sa.Column("form_type", sa.String(length=32), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("amended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("parse_status", sa.String(length=32), nullable=True),
        sa.Column("total_assets", sa.BigInteger(), nullable=True),
        sa.Column("total_income", sa.BigInteger(), nullable=True),
        sa.Column("total_revenue", sa.BigInteger(), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=True),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("source_signature", sa.String(length=128), nullable=True),
        sa.Column("xml_source_reference", sa.Text(), nullable=True),
        sa.Column("raw_file_reference", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["nonprofit_id"], ["nonprofits.nonprofit_id"], name="fk_nonprofit_filings_nonprofit_id_nonprofits"),
        sa.UniqueConstraint(
            "nonprofit_id",
            "tax_year",
            "form_type",
            "filing_date",
            "source_name",
            name="uq_nonprofit_filings_nonprofit_identity",
        ),
    )
    op.create_index("ix_nonprofit_filings_nonprofit_tax_year", "nonprofit_filings", ["nonprofit_id", "tax_year", "filing_date"], unique=False)
    op.create_index("ix_nonprofit_filings_nonprofit_latest", "nonprofit_filings", ["nonprofit_id", "tax_year", "filing_date", "updated_at"], unique=False)
    op.create_index("ix_nonprofit_filings_nonprofit_source", "nonprofit_filings", ["nonprofit_id", "source_name", "source_record_id"], unique=False)

    op.create_table(
        "form990_archives",
        sa.Column("archive_id", pk_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_duration_ms", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("source_url", name="uq_form990_archives_source_url"),
    )
    op.create_index("ix_form990_archives_last_checked_at", "form990_archives", ["last_checked_at"], unique=False)

    op.create_table(
        "form990_extracted_files",
        sa.Column("file_id", pk_type, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("archive_id", pk_type, nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("parse_status", sa.String(length=32), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["archive_id"], ["form990_archives.archive_id"], name="fk_form990_extracted_files_archive_id_form990_archives"),
        sa.UniqueConstraint("archive_id", "filename", name="uq_form990_extracted_files_archive_filename"),
    )
    op.create_index("ix_form990_extracted_files_archive_status", "form990_extracted_files", ["archive_id", "parse_status"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Phase 27N is destructive and not intended to be downgraded in dev.")
