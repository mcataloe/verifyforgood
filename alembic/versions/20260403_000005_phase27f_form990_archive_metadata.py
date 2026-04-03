"""Phase 27F Form 990 archive metadata and extracted file hashes

Revision ID: 20260403_000005
Revises: 20260331_000004
Create Date: 2026-04-03 00:00:05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260403_000005"
down_revision = "20260331_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form990_archives",
        sa.Column("archive_id", sa.String(length=64), primary_key=True, nullable=False),
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
        sa.Column("file_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("archive_id", sa.String(length=64), nullable=False),
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
    op.drop_index("ix_form990_extracted_files_archive_status", table_name="form990_extracted_files")
    op.drop_table("form990_extracted_files")
    op.drop_index("ix_form990_archives_last_checked_at", table_name="form990_archives")
    op.drop_table("form990_archives")
