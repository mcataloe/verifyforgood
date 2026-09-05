from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Identity, Index, Integer, JSON, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from verification.backend.shared.customer_accounts.sqlalchemy_db import (
    CustomerAccountsBase,
    customer_accounts_session_scope,
)
from verification.backend.shared.customer_accounts.sqlalchemy_models import (
    BIGINT_FOREIGN_KEY,
    BIGINT_PRIMARY_KEY,
)

from .conversations import ChatConversationRecord, ChatMessageRecord, ChatMessageRole


class ChatConversationModel(CustomerAccountsBase):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index(
            "ix_chat_conversations_user_org_updated",
            "user_id",
            "organization_id",
            "updated_at",
        ),
    )

    conversation_id: Mapped[int] = mapped_column(
        BIGINT_PRIMARY_KEY,
        Identity(start=1),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT_FOREIGN_KEY,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    organization_id: Mapped[int] = mapped_column(
        BIGINT_FOREIGN_KEY,
        ForeignKey("organizations.organization_id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatMessageModel(CustomerAccountsBase):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index(
            "ix_chat_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )

    message_id: Mapped[int] = mapped_column(
        BIGINT_PRIMARY_KEY,
        Identity(start=1),
        primary_key=True,
        autoincrement=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        BIGINT_FOREIGN_KEY,
        ForeignKey("chat_conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False, default=dict)


class SqlAlchemyChatConversationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_conversation(self, conversation: ChatConversationRecord) -> ChatConversationRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = ChatConversationModel(
                user_id=_require_int(conversation.user_id),
                organization_id=_require_int(conversation.organization_id),
                title=conversation.title,
                created_at=_parse_timestamp(conversation.created_at),
                updated_at=_parse_timestamp(conversation.updated_at),
            )
            session.add(model)
            session.flush()
            session.refresh(model)
            return _conversation_record(model)

    def get_conversation(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> ChatConversationRecord | None:
        normalized = _scope_ids(conversation_id, user_id, organization_id)
        if normalized is None:
            return None
        conversation_id_int, user_id_int, organization_id_int = normalized
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(ChatConversationModel)
                .where(
                    ChatConversationModel.conversation_id == conversation_id_int,
                    ChatConversationModel.user_id == user_id_int,
                    ChatConversationModel.organization_id == organization_id_int,
                )
                .limit(1)
            )
            return None if model is None else _conversation_record(model)

    def list_conversations(
        self,
        *,
        user_id: int | str,
        organization_id: int | str,
        limit: int = 50,
    ) -> list[ChatConversationRecord]:
        normalized = _scope_ids(None, user_id, organization_id)
        if normalized is None:
            return []
        _, user_id_int, organization_id_int = normalized
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(ChatConversationModel)
                .where(
                    ChatConversationModel.user_id == user_id_int,
                    ChatConversationModel.organization_id == organization_id_int,
                )
                .order_by(ChatConversationModel.updated_at.desc(), ChatConversationModel.conversation_id.desc())
                .limit(max(1, min(int(limit), 100)))
            ).all()
            return [_conversation_record(model) for model in models]

    def append_message(
        self,
        message: ChatMessageRecord,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> ChatMessageRecord | None:
        normalized = _scope_ids(message.conversation_id, user_id, organization_id)
        if normalized is None:
            return None
        conversation_id_int, user_id_int, organization_id_int = normalized
        with customer_accounts_session_scope(self._session_factory) as session:
            conversation = session.scalar(
                select(ChatConversationModel)
                .where(
                    ChatConversationModel.conversation_id == conversation_id_int,
                    ChatConversationModel.user_id == user_id_int,
                    ChatConversationModel.organization_id == organization_id_int,
                )
                .limit(1)
            )
            if conversation is None:
                return None
            created_at = _parse_timestamp(message.created_at)
            model = ChatMessageModel(
                conversation_id=conversation_id_int,
                role=message.role.value,
                content=message.content,
                created_at=created_at,
                metadata_json=dict(message.metadata),
            )
            session.add(model)
            conversation.updated_at = max(conversation.updated_at, created_at)
            session.flush()
            session.refresh(model)
            return _message_record(model)

    def list_messages(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> list[ChatMessageRecord] | None:
        normalized = _scope_ids(conversation_id, user_id, organization_id)
        if normalized is None:
            return None
        conversation_id_int, user_id_int, organization_id_int = normalized
        with customer_accounts_session_scope(self._session_factory) as session:
            conversation = session.scalar(
                select(ChatConversationModel.conversation_id)
                .where(
                    ChatConversationModel.conversation_id == conversation_id_int,
                    ChatConversationModel.user_id == user_id_int,
                    ChatConversationModel.organization_id == organization_id_int,
                )
                .limit(1)
            )
            if conversation is None:
                return None
            models = session.scalars(
                select(ChatMessageModel)
                .where(ChatMessageModel.conversation_id == conversation_id_int)
                .order_by(ChatMessageModel.created_at, ChatMessageModel.message_id)
            ).all()
            return [_message_record(model) for model in models]


def _conversation_record(model: ChatConversationModel) -> ChatConversationRecord:
    return ChatConversationRecord(
        conversation_id=int(model.conversation_id),
        user_id=int(model.user_id),
        organization_id=int(model.organization_id),
        title=model.title,
        created_at=model.created_at.isoformat(),
        updated_at=model.updated_at.isoformat(),
    )


def _message_record(model: ChatMessageModel) -> ChatMessageRecord:
    return ChatMessageRecord(
        message_id=int(model.message_id),
        conversation_id=int(model.conversation_id),
        role=ChatMessageRole(model.role),
        content=model.content,
        created_at=model.created_at.isoformat(),
        metadata=dict(model.metadata_json or {}),
    )


def _scope_ids(
    conversation_id: int | str | None,
    user_id: int | str,
    organization_id: int | str,
) -> tuple[int, int, int] | None:
    try:
        conversation = 0 if conversation_id is None else _require_int(conversation_id)
        return conversation, _require_int(user_id), _require_int(organization_id)
    except (TypeError, ValueError):
        return None


def _require_int(value: int | str) -> int:
    normalized = int(value)
    if normalized <= 0:
        raise ValueError("identifier must be a positive integer")
    return normalized


def _parse_timestamp(value: str) -> datetime:
    normalized = str(value).strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized)
