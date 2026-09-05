from __future__ import annotations

from pathlib import Path

import pytest

from verification.backend.shared.chat import (
    ChatConversationService,
    ChatMessageRole,
    ConversationNotFoundError,
    SqlAlchemyChatConversationRepository,
)
from verification.backend.shared.customer_accounts import (
    CustomerAccountsBase,
    OrganizationRecord,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
    UserRecord,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
)


def _session_factory(tmp_path: Path):
    db_path = tmp_path / "chat.sqlite3"
    engine = build_customer_accounts_engine(f"sqlite+pysqlite:///{db_path}")
    CustomerAccountsBase.metadata.create_all(engine)
    return build_customer_accounts_session_factory(engine)


def _seed_scope(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    users = SqlAlchemyUserRepository(session_factory)
    organizations = SqlAlchemyOrganizationRepository(session_factory)

    user_a = users.create(
        UserRecord(
            user_id=None,
            email="chat-a@example.com",
            normalized_email="chat-a@example.com",
            full_name="Chat A",
            created_at="2026-09-05T12:00:00+00:00",
            updated_at="2026-09-05T12:00:00+00:00",
            password_hash="hash",
        )
    )
    user_b = users.create(
        UserRecord(
            user_id=None,
            email="chat-b@example.com",
            normalized_email="chat-b@example.com",
            full_name="Chat B",
            created_at="2026-09-05T12:00:00+00:00",
            updated_at="2026-09-05T12:00:00+00:00",
            password_hash="hash",
        )
    )
    org_a = organizations.create(
        OrganizationRecord(
            organization_id=None,
            name="Chat Org A",
            slug="chat-org-a",
            created_at="2026-09-05T12:00:00+00:00",
            updated_at="2026-09-05T12:00:00+00:00",
        )
    )
    org_b = organizations.create(
        OrganizationRecord(
            organization_id=None,
            name="Chat Org B",
            slug="chat-org-b",
            created_at="2026-09-05T12:00:00+00:00",
            updated_at="2026-09-05T12:00:00+00:00",
        )
    )
    return session_factory, user_a, user_b, org_a, org_b


def test_chat_metadata_contains_conversation_tables(tmp_path: Path):
    session_factory, *_ = _seed_scope(tmp_path)
    del session_factory

    assert "chat_conversations" in CustomerAccountsBase.metadata.tables
    assert "chat_messages" in CustomerAccountsBase.metadata.tables


def test_chat_conversation_history_is_user_and_organization_scoped(tmp_path: Path):
    session_factory, user_a, user_b, org_a, org_b = _seed_scope(tmp_path)
    service = ChatConversationService(SqlAlchemyChatConversationRepository(session_factory))

    conversation = service.create_conversation(
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
        title="Nonprofit review",
        created_at="2026-09-05T12:00:00+00:00",
    )
    user_message = service.append_message(
        conversation.conversation_id,
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
        role=ChatMessageRole.USER,
        content="Show me the latest filing.",
        created_at="2026-09-05T12:01:00+00:00",
    )
    assistant_message = service.append_message(
        conversation.conversation_id,
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
        role=ChatMessageRole.ASSISTANT,
        content="I found the filing metadata.",
        metadata={"route_tier": "low"},
        created_at="2026-09-05T12:02:00+00:00",
    )

    visible = service.list_messages(
        conversation.conversation_id,
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
    )
    assert [item.message_id for item in visible] == [user_message.message_id, assistant_message.message_id]
    assert visible[-1].metadata == {"route_tier": "low"}

    with pytest.raises(ConversationNotFoundError):
        service.get_conversation(
            conversation.conversation_id,
            user_id=user_b.user_id,
            organization_id=org_a.organization_id,
        )
    with pytest.raises(ConversationNotFoundError):
        service.get_conversation(
            conversation.conversation_id,
            user_id=user_a.user_id,
            organization_id=org_b.organization_id,
        )
    with pytest.raises(ConversationNotFoundError):
        service.append_message(
            conversation.conversation_id,
            user_id=user_b.user_id,
            organization_id=org_a.organization_id,
            role=ChatMessageRole.USER,
            content="This must not be written.",
        )

    assert service.list_conversations(user_id=user_b.user_id, organization_id=org_a.organization_id) == []
    assert service.list_conversations(user_id=user_a.user_id, organization_id=org_b.organization_id) == []


def test_chat_conversation_listing_is_scoped_and_recent_first(tmp_path: Path):
    session_factory, user_a, _, org_a, _ = _seed_scope(tmp_path)
    service = ChatConversationService(SqlAlchemyChatConversationRepository(session_factory))

    first = service.create_conversation(
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
        title="First",
        created_at="2026-09-05T12:00:00+00:00",
    )
    second = service.create_conversation(
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
        title="Second",
        created_at="2026-09-05T12:10:00+00:00",
    )

    conversations = service.list_conversations(
        user_id=user_a.user_id,
        organization_id=org_a.organization_id,
    )

    assert [item.conversation_id for item in conversations] == [second.conversation_id, first.conversation_id]
