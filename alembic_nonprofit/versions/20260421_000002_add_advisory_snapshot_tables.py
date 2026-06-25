"""Add nonprofit advisory snapshot and artifact tables.

Revision ID: 20260421_000002_nonprofit_advisory
Revises: 20260419_000001_nonprofit
Create Date: 2026-04-21 00:00:02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260421_000002_nonprofit_advisory"
down_revision = "20260419_000001_nonprofit"
branch_labels = None
depends_on = None


BIGINT_PRIMARY_KEY = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
BIGINT_FOREIGN_KEY = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.alter_column(
        "alembic_version_nonprofit",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=128),
        existing_nullable=False,
    )

    op.create_table(
        "nonprofit_detail_snapshots",
        sa.Column("snapshot_id", BIGINT_PRIMARY_KEY, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("nonprofit_id", BIGINT_FOREIGN_KEY, nullable=False),
        sa.Column("ein", sa.String(length=9), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("materialized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("build_status", sa.String(length=32), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["nonprofit_id"],
            ["nonprofits.nonprofit_id"],
            name="fk_nonprofit_detail_snapshots_nonprofit_id_nonprofits",
        ),
        sa.UniqueConstraint("ein", name="uq_nonprofit_detail_snapshots_ein"),
    )
    op.create_index(
        "ix_nonprofit_detail_snapshots_nonprofit_id",
        "nonprofit_detail_snapshots",
        ["nonprofit_id"],
        unique=False,
    )
    op.create_index(
        "ix_nonprofit_detail_snapshots_materialized_at",
        "nonprofit_detail_snapshots",
        ["materialized_at"],
        unique=False,
    )

    op.create_table(
        "nonprofit_advisory_artifacts",
        sa.Column("artifact_id", BIGINT_PRIMARY_KEY, sa.Identity(start=1), primary_key=True, nullable=False),
        sa.Column("nonprofit_id", BIGINT_FOREIGN_KEY, nullable=False),
        sa.Column("ein", sa.String(length=9), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("build_status", sa.String(length=32), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["nonprofit_id"],
            ["nonprofits.nonprofit_id"],
            name="fk_nonprofit_advisory_artifacts_nonprofit_id_nonprofits",
        ),
    )
    op.create_index(
        "ix_nonprofit_advisory_artifacts_nonprofit_type_created",
        "nonprofit_advisory_artifacts",
        ["nonprofit_id", "artifact_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_nonprofit_advisory_artifacts_ein_type_created",
        "nonprofit_advisory_artifacts",
        ["ein", "artifact_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_nonprofit_advisory_artifacts_ein_type_created",
        table_name="nonprofit_advisory_artifacts",
    )
    op.drop_index(
        "ix_nonprofit_advisory_artifacts_nonprofit_type_created",
        table_name="nonprofit_advisory_artifacts",
    )
    op.drop_table("nonprofit_advisory_artifacts")

    op.drop_index(
        "ix_nonprofit_detail_snapshots_materialized_at",
        table_name="nonprofit_detail_snapshots",
    )
    op.drop_index(
        "ix_nonprofit_detail_snapshots_nonprofit_id",
        table_name="nonprofit_detail_snapshots",
    )
    op.drop_table("nonprofit_detail_snapshots")
