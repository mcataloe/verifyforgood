"""Phase 27L generated BIGINT PKs for Form 990 nonprofit tables

Revision ID: 20260404_000009
Revises: 20260404_000008
Create Date: 2026-04-04 20:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260404_000009"
down_revision = "20260404_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_nonprofits_normalized_name_trgm")

    op.drop_table("form990_extracted_files")
    op.drop_table("form990_archives")
    op.drop_table("compliance_checks")
    op.drop_table("nonprofit_sources")
    op.drop_table("nonprofit_filings")
    op.drop_table("nonprofits")

    _create_nonprofit_domain_tables(
        dialect_name=dialect_name,
        generated_child_ids=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_nonprofits_normalized_name_trgm")

    op.drop_table("form990_extracted_files")
    op.drop_table("form990_archives")
    op.drop_table("compliance_checks")
    op.drop_table("nonprofit_sources")
    op.drop_table("nonprofit_filings")
    op.drop_table("nonprofits")

    _create_nonprofit_domain_tables(
        dialect_name=dialect_name,
        generated_child_ids=False,
    )


def _create_nonprofit_domain_tables(*, dialect_name: str, generated_child_ids: bool) -> None:
    nonprofit_pk = _pk_column("nonprofit_id", dialect_name=dialect_name, generated=True)
    filing_pk = _pk_column("filing_id", dialect_name=dialect_name, generated=generated_child_ids, fallback_length=64)
    source_pk = _pk_column(
        "nonprofit_source_id",
        dialect_name=dialect_name,
        generated=generated_child_ids,
        fallback_length=64,
    )
    compliance_pk = _pk_column(
        "compliance_check_id",
        dialect_name=dialect_name,
        generated=generated_child_ids,
        fallback_length=64,
    )
    archive_pk = _pk_column("archive_id", dialect_name=dialect_name, generated=generated_child_ids, fallback_length=64)
    extracted_file_pk = _pk_column("file_id", dialect_name=dialect_name, generated=generated_child_ids, fallback_length=64)

    nonprofit_fk_type = _fk_type_for_dialect(dialect_name)
    archive_fk_type = _fk_type_for_dialect(dialect_name) if generated_child_ids else sa.String(length=64)

    op.create_table(
        "nonprofits",
        nonprofit_pk,
        sa.Column("ein", sa.String(length=9), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("subsection_code", sa.String(length=16), nullable=True),
        sa.Column("deductibility_code", sa.String(length=32), nullable=True),
        sa.Column("tax_deductible", sa.Boolean(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("irs_status", sa.String(length=64), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("country", sa.String(length=32), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=True),
        sa.Column("ntee_category", sa.String(length=32), nullable=True),
        sa.Column("canonical_source", sa.String(length=128), nullable=True),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("ein", name="uq_nonprofits_ein"),
    )
    op.create_index("ix_nonprofits_normalized_name", "nonprofits", ["normalized_name"], unique=False)
    op.create_index("ix_nonprofits_normalized_name_ein", "nonprofits", ["normalized_name", "ein"], unique=False)

    op.create_table(
        "nonprofit_filings",
        filing_pk,
        sa.Column("nonprofit_id", nonprofit_fk_type, nullable=False),
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
        sa.Column("raw_s3_key", sa.Text(), nullable=True),
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
        "nonprofit_sources",
        source_pk,
        sa.Column("nonprofit_id", nonprofit_fk_type, nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("record_id", sa.String(length=255), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("driver", sa.String(length=64), nullable=True),
        sa.Column("integration_id", sa.String(length=128), nullable=True),
        sa.Column("tenant_enabled", sa.Boolean(), nullable=True),
        sa.Column("required_for_eligibility", sa.Boolean(), nullable=True),
        sa.Column("evaluation_effect", sa.String(length=32), nullable=True),
        sa.Column("explanation_code", sa.String(length=128), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("licensed", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_signature", sa.String(length=128), nullable=True),
        sa.Column("normalized_data", sa.JSON(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["nonprofit_id"], ["nonprofits.nonprofit_id"], name="fk_nonprofit_sources_nonprofit_id_nonprofits"),
        sa.UniqueConstraint("nonprofit_id", "source_id", "record_id", "retrieved_at", name="uq_nonprofit_sources_lineage"),
    )
    op.create_index("ix_nonprofit_sources_nonprofit_retrieved", "nonprofit_sources", ["nonprofit_id", "retrieved_at"], unique=False)
    op.create_index("ix_nonprofit_sources_nonprofit_source_id", "nonprofit_sources", ["nonprofit_id", "source_id"], unique=False)

    op.create_table(
        "compliance_checks",
        compliance_pk,
        sa.Column("nonprofit_id", nonprofit_fk_type, nullable=False),
        sa.Column("check_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.Column("environment", sa.String(length=32), nullable=True),
        sa.Column("registration_status", sa.String(length=64), nullable=True),
        sa.Column("registration_jurisdiction", sa.String(length=64), nullable=True),
        sa.Column("registration_expiration_date", sa.Date(), nullable=True),
        sa.Column("solicitation_permitted", sa.Boolean(), nullable=True),
        sa.Column("state_business_status", sa.String(length=64), nullable=True),
        sa.Column("state_business_good_standing", sa.Boolean(), nullable=True),
        sa.Column("final_recommendation", sa.String(length=64), nullable=True),
        sa.Column("flags_json", sa.JSON(), nullable=True),
        sa.Column("reasons_json", sa.JSON(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["nonprofit_id"], ["nonprofits.nonprofit_id"], name="fk_compliance_checks_nonprofit_id_nonprofits"),
    )
    op.create_index("ix_compliance_checks_nonprofit_evaluated", "compliance_checks", ["nonprofit_id", "evaluated_at"], unique=False)
    op.create_index("ix_compliance_checks_nonprofit_type", "compliance_checks", ["nonprofit_id", "check_type"], unique=False)
    op.create_index("ix_compliance_checks_nonprofit_type_evaluated", "compliance_checks", ["nonprofit_id", "check_type", "evaluated_at"], unique=False)

    op.create_table(
        "form990_archives",
        archive_pk,
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
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_url", name="uq_form990_archives_source_url"),
    )
    op.create_index("ix_form990_archives_last_checked_at", "form990_archives", ["last_checked_at"], unique=False)

    op.create_table(
        "form990_extracted_files",
        extracted_file_pk,
        sa.Column("archive_id", archive_fk_type, nullable=False),
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

    if dialect_name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_nonprofits_normalized_name_trgm "
            "ON nonprofits USING gin (normalized_name gin_trgm_ops)"
        )


def _pk_column(name: str, *, dialect_name: str, generated: bool, fallback_length: int | None = None) -> sa.Column:
    if generated:
        column_type = sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()
        return sa.Column(name, column_type, sa.Identity(start=1), primary_key=True, nullable=False)
    assert fallback_length is not None
    return sa.Column(name, sa.String(length=fallback_length), primary_key=True, nullable=False)


def _fk_type_for_dialect(dialect_name: str) -> sa.types.TypeEngine:
    return sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()
