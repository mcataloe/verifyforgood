from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatConversationRecord:
    conversation_id: int | None
    user_id: int
    organization_id: int
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChatMessageRecord:
    message_id: int | None
    conversation_id: int
    role: ChatMessageRole
    content: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ChatConversationRepository(Protocol):
    def create_conversation(self, conversation: ChatConversationRecord) -> ChatConversationRecord: ...

    def get_conversation(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> ChatConversationRecord | None: ...

    def list_conversations(
        self,
        *,
        user_id: int | str,
        organization_id: int | str,
        limit: int = 50,
    ) -> list[ChatConversationRecord]: ...

    def append_message(
        self,
        message: ChatMessageRecord,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> ChatMessageRecord | None: ...

    def list_messages(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> list[ChatMessageRecord] | None: ...


class ConversationNotFoundError(LookupError):
    """Raised when a conversation is missing or outside the caller's user/org scope."""


class InvalidChatMessageError(ValueError):
    """Raised when a message cannot be persisted safely."""


class ChatConversationService:
    def __init__(self, repository: ChatConversationRepository) -> None:
        self._repository = repository

    def create_conversation(
        self,
        *,
        user_id: int | str,
        organization_id: int | str,
        title: str | None = None,
        created_at: str | None = None,
    ) -> ChatConversationRecord:
        timestamp = created_at or _utc_now_iso()
        return self._repository.create_conversation(
            ChatConversationRecord(
                conversation_id=None,
                user_id=_require_positive_int(user_id, "user_id"),
                organization_id=_require_positive_int(organization_id, "organization_id"),
                title=_normalize_title(title),
                created_at=timestamp,
                updated_at=timestamp,
            )
        )

    def get_conversation(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> ChatConversationRecord:
        conversation = self._repository.get_conversation(
            conversation_id,
            user_id=user_id,
            organization_id=organization_id,
        )
        if conversation is None:
            raise ConversationNotFoundError("Conversation not found")
        return conversation

    def list_conversations(
        self,
        *,
        user_id: int | str,
        organization_id: int | str,
        limit: int = 50,
    ) -> list[ChatConversationRecord]:
        return self._repository.list_conversations(
            user_id=user_id,
            organization_id=organization_id,
            limit=max(1, min(int(limit), 100)),
        )

    def append_message(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
        role: ChatMessageRole | str,
        content: str,
        metadata: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> ChatMessageRecord:
        normalized_content = str(content or "").strip()
        if not normalized_content:
            raise InvalidChatMessageError("Chat message content is required")
        try:
            normalized_role = role if isinstance(role, ChatMessageRole) else ChatMessageRole(str(role))
        except ValueError as exc:
            raise InvalidChatMessageError(f"Unsupported persisted chat role: {role}") from exc

        persisted = self._repository.append_message(
            ChatMessageRecord(
                message_id=None,
                conversation_id=_require_positive_int(conversation_id, "conversation_id"),
                role=normalized_role,
                content=normalized_content,
                created_at=created_at or _utc_now_iso(),
                metadata=dict(metadata or {}),
            ),
            user_id=user_id,
            organization_id=organization_id,
        )
        if persisted is None:
            raise ConversationNotFoundError("Conversation not found")
        return persisted

    def list_messages(
        self,
        conversation_id: int | str,
        *,
        user_id: int | str,
        organization_id: int | str,
    ) -> list[ChatMessageRecord]:
        messages = self._repository.list_messages(
            conversation_id,
            user_id=user_id,
            organization_id=organization_id,
        )
        if messages is None:
            raise ConversationNotFoundError("Conversation not found")
        return messages


def _normalize_title(value: str | None) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        return "New conversation"
    return normalized[:255]


def _require_positive_int(value: int | str, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer") from exc
    if normalized <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return normalized


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
