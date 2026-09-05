"""DU-CHAT-001 conversation persistence and ownership

Revision ID: 20260905_000020
Revises: 20260703_000019
Create Date: 2026-09-05 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260905_000020"
down_revision = "20260703_000019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bigint_type = _bigint_for_dialect(bind.dialect.name)

    op.create_table(
        "chat_conversations",
        sa.Column(
            "conversation_id",
            bigint_type,
            sa.Identity(start=1),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("user_id", bigint_type, nullable=False),
        sa.Column("organization_id", bigint_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_chat_conversations_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_chat_conversations_organization_id_organizations",
        ),
    )
    op.create_index(
        "ix_chat_conversations_user_org_updated",
        "chat_conversations",
        ["user_id", "organization_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "chat_messages",
        sa.Column(
            "message_id",
            bigint_type,
            sa.Identity(start=1),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("conversation_id", bigint_type, nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_conversations.conversation_id"],
            name="fk_chat_messages_conversation_id_chat_conversations",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_chat_messages_conversation_created",
        "chat_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_conversation_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_conversations_user_org_updated", table_name="chat_conversations")
    op.drop_table("chat_conversations")


def _bigint_for_dialect(dialect_name: str) -> sa.types.TypeEngine:
    return sa.BigInteger() if dialect_name == "postgresql" else sa.Integer()
