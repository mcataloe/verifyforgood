from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from verification.backend.customer.api.chat_api import ChatApiServices, create_chat_router
from verification.backend.shared.chat import (
    ChatConversationRecord,
    ChatConversationService,
    ChatMessageRecord,
    ChatMessageRole,
    ChatModelResolver,
    ChatModelRouter,
    ChatModelSettings,
    ChatProviderResponse,
    ChatProviderRegistry,
    ChatProviderUnavailableError,
    ChatConversationOrchestrator,
    FakeChatLLMProvider,
)


class _ConversationRepository:
    def __init__(self) -> None:
        self.conversations = {}
        self.messages = {}
        self.next_conversation_id = 1
        self.next_message_id = 1

    def create_conversation(self, conversation: ChatConversationRecord):
        persisted = replace(conversation, conversation_id=self.next_conversation_id)
        self.next_conversation_id += 1
        self.conversations[persisted.conversation_id] = persisted
        self.messages[persisted.conversation_id] = []
        return persisted

    def get_conversation(self, conversation_id, *, user_id, organization_id):
        conversation = self.conversations.get(int(conversation_id))
        if conversation is None:
            return None
        if conversation.user_id != int(user_id) or conversation.organization_id != int(organization_id):
            return None
        return conversation

    def list_conversations(self, *, user_id, organization_id, limit=50):
        return [
            item
            for item in self.conversations.values()
            if item.user_id == int(user_id) and item.organization_id == int(organization_id)
        ][:limit]

    def append_message(self, message: ChatMessageRecord, *, user_id, organization_id):
        if self.get_conversation(
            message.conversation_id,
            user_id=user_id,
            organization_id=organization_id,
        ) is None:
            return None
        persisted = replace(message, message_id=self.next_message_id)
        self.next_message_id += 1
        self.messages[message.conversation_id].append(persisted)
        return persisted

    def list_messages(self, conversation_id, *, user_id, organization_id):
        if self.get_conversation(
            conversation_id,
            user_id=user_id,
            organization_id=organization_id,
        ) is None:
            return None
        return list(self.messages[int(conversation_id)])


class _AuthService:
    def get_current_user(self, authorization_header):
        if authorization_header != "Bearer test-token":
            from verification.backend.shared.auth import AuthenticationError

            raise AuthenticationError("invalid")
        return SimpleNamespace(user_id="1")


class _OrganizationContextService:
    def __init__(self, organization_id: int) -> None:
        self.organization_id = organization_id

    def resolve_for_user(self, *, user_id):
        assert user_id == "1"
        return SimpleNamespace(organization_id=str(self.organization_id))


def _services(repository, *, organization_id=7, provider=None):
    provider = provider or FakeChatLLMProvider(
        [ChatProviderResponse(content="Local pipeline response.")]
    )
    orchestrator = ChatConversationOrchestrator(
        providers=ChatProviderRegistry([provider]),
        router=ChatModelRouter(),
        resolver=ChatModelResolver(ChatModelSettings(provider="fake")),
    )
    return ChatApiServices(
        conversations=ChatConversationService(repository),
        orchestrator=orchestrator,
        auth_service=_AuthService(),
        organization_context_service=_OrganizationContextService(organization_id),
    )


def _client(services):
    app = FastAPI()
    app.include_router(create_chat_router(lambda: services))
    return TestClient(app)


def _headers(**extra):
    return {"Authorization": "Bearer test-token", **extra}


def test_chat_api_creates_sends_and_reads_conversation_with_server_owned_scope():
    repository = _ConversationRepository()
    client = _client(_services(repository, organization_id=7))

    created = client.post(
        "/v1/chat/conversations",
        headers=_headers(**{"X-Organization-Id": "999"}),
        json={"title": "Local pipeline", "organization_id": 999},
    )
    assert created.status_code == 201
    conversation = created.json()["data"]["conversation"]
    assert conversation["user_id"] == 1
    assert conversation["organization_id"] == 7

    sent = client.post(
        f'/v1/chat/conversations/{conversation["conversation_id"]}/messages',
        headers=_headers(),
        json={"content": "Show me the latest filing.", "organization_id": 999},
    )
    assert sent.status_code == 200
    data = sent.json()["data"]
    assert data["assistant_message"]["content"] == "Local pipeline response."
    assert data["orchestration"]["route_tier"] == "low"
    assert data["orchestration"]["provider"] == "fake"

    history = client.get(
        f'/v1/chat/conversations/{conversation["conversation_id"]}',
        headers=_headers(),
    )
    assert history.status_code == 200
    assert [item["role"] for item in history.json()["data"]["messages"]] == ["user", "assistant"]


def test_chat_api_does_not_expose_conversation_after_server_org_context_switch():
    repository = _ConversationRepository()
    org7_client = _client(_services(repository, organization_id=7))
    created = org7_client.post(
        "/v1/chat/conversations",
        headers=_headers(),
        json={"title": "Org 7"},
    ).json()["data"]["conversation"]

    org8_client = _client(_services(repository, organization_id=8))
    response = org8_client.get(
        f'/v1/chat/conversations/{created["conversation_id"]}',
        headers=_headers(),
    )

    assert response.status_code == 404
    assert response.json()["errors"][0]["code"] == "not_found"


def test_chat_api_requires_authentication():
    client = _client(_services(_ConversationRepository()))

    response = client.get("/v1/chat/conversations")

    assert response.status_code == 401
    assert response.json()["errors"][0]["code"] == "unauthorized"


def test_chat_api_maps_provider_failure_without_exposing_internal_tool_data():
    repository = _ConversationRepository()
    provider = FakeChatLLMProvider([ChatProviderUnavailableError("local model offline")])
    client = _client(_services(repository, provider=provider))
    conversation = client.post(
        "/v1/chat/conversations",
        headers=_headers(),
        json={},
    ).json()["data"]["conversation"]

    response = client.post(
        f'/v1/chat/conversations/{conversation["conversation_id"]}/messages',
        headers=_headers(),
        json={"content": "Hello"},
    )

    assert response.status_code == 503
    assert response.json()["errors"][0]["code"] == "provider_unavailable"
    assert "tool" not in response.text.lower()
