from __future__ import annotations

import pytest

from verification.backend.shared.chat import (
    ChatConversationOrchestrator,
    ChatExecutionContext,
    ChatModelMessage,
    ChatModelResolver,
    ChatModelRole,
    ChatModelRouter,
    ChatModelSettings,
    ChatModelTier,
    ChatProviderRequest,
    ChatProviderResponse,
    ChatProviderRegistry,
    ChatToolDefinition,
    ChatToolExecutionResult,
    ChatToolRequest,
    FakeChatLLMProvider,
    OllamaChatLLMProvider,
)


class _EchoToolExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[ChatToolRequest, ChatExecutionContext]] = []

    def definitions(self, context: ChatExecutionContext):
        del context
        return (
            ChatToolDefinition(
                name="chat_echo",
                description="Echo a value for orchestration tests.",
                input_schema={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
            ),
        )

    def execute(self, request: ChatToolRequest, context: ChatExecutionContext):
        self.calls.append((request, context))
        return ChatToolExecutionResult(
            request_id=request.request_id,
            name=request.name,
            content=f'{{"value":"{request.arguments["value"]}"}}',
            metadata={"source": "test"},
        )


def test_model_router_emits_application_owned_tiers():
    router = ChatModelRouter()

    assert router.route("What is this nonprofit's latest filing?").tier is ChatModelTier.LOW
    assert router.route("Compare the last two filings and summarize the differences.").tier is ChatModelTier.MEDIUM
    assert router.route("Perform a multi-document analysis across all filings.").tier is ChatModelTier.HIGH


def test_local_model_resolver_can_map_every_tier_to_one_small_model():
    resolver = ChatModelResolver(
        ChatModelSettings(provider="ollama", local_model="small-local-model")
    )
    router = ChatModelRouter()

    resolved_models = {
        resolver.resolve(router.route(message)).model
        for message in (
            "Latest filing?",
            "Compare the last two filings.",
            "Perform a multi-document analysis across all filings.",
        )
    }

    assert resolved_models == {"small-local-model"}


def test_orchestrator_returns_direct_fake_response_with_route_diagnostics():
    provider = FakeChatLLMProvider(
        [ChatProviderResponse(content="Structured local answer.", finish_reason="stop")]
    )
    orchestrator = ChatConversationOrchestrator(
        providers=ChatProviderRegistry([provider]),
        router=ChatModelRouter(),
        resolver=ChatModelResolver(ChatModelSettings(provider="fake")),
    )

    result = orchestrator.run(
        context=ChatExecutionContext(user_id=1, organization_id=10),
        user_message="Latest filing?",
    )

    assert result.content == "Structured local answer."
    assert result.resolved_model.tier is ChatModelTier.LOW
    assert result.resolved_model.model == "fake-local"
    assert result.diagnostics[0].provider == "fake"
    assert result.diagnostics[0].route_reason == "simple_or_single_fact"


def test_orchestrator_executes_requested_tool_outside_provider_then_continues():
    provider = FakeChatLLMProvider(
        [
            ChatProviderResponse(
                content="",
                finish_reason="tool_calls",
                tool_requests=(
                    ChatToolRequest(
                        request_id="tool-1",
                        name="chat_echo",
                        arguments={"value": "hello"},
                    ),
                ),
            ),
            ChatProviderResponse(content="The tool returned hello.", finish_reason="stop"),
        ]
    )
    tools = _EchoToolExecutor()
    orchestrator = ChatConversationOrchestrator(
        providers=ChatProviderRegistry([provider]),
        router=ChatModelRouter(),
        resolver=ChatModelResolver(ChatModelSettings(provider="fake")),
        tool_executor=tools,
    )
    context = ChatExecutionContext(user_id=1, organization_id=10)

    result = orchestrator.run(context=context, user_message="Echo hello")

    assert result.content == "The tool returned hello."
    assert len(tools.calls) == 1
    assert tools.calls[0][1] == context
    assert len(provider.requests) == 2
    assert provider.requests[1].messages[-1].role is ChatModelRole.TOOL
    assert provider.requests[1].messages[-1].name == "chat_echo"
    assert result.tool_results[0].metadata == {"source": "test"}


def test_ollama_provider_uses_native_chat_shape_and_normalizes_tool_request():
    captured = {}

    def transport(url, payload, timeout):
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {
            "model": "small-local-model",
            "done": True,
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "chat_echo",
                            "arguments": {"value": "hello"},
                        }
                    }
                ],
            },
            "prompt_eval_count": 12,
            "eval_count": 4,
        }

    provider = OllamaChatLLMProvider(transport=transport, timeout_seconds=2.5)
    response = provider.generate(
        ChatProviderRequest(
            model="small-local-model",
            messages=(ChatModelMessage(role=ChatModelRole.USER, content="Echo hello"),),
            tools=(
                ChatToolDefinition(
                    name="chat_echo",
                    description="Echo a value.",
                    input_schema={"type": "object", "properties": {"value": {"type": "string"}}},
                ),
            ),
        )
    )

    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["model"] == "small-local-model"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["tools"][0]["function"]["name"] == "chat_echo"
    assert response.provider == "ollama"
    assert response.tool_requests[0].name == "chat_echo"
    assert response.tool_requests[0].arguments == {"value": "hello"}
    assert response.usage == {"input_tokens": 12, "output_tokens": 4}


def test_orchestrator_preserves_existing_history_without_leaking_provider_types():
    provider = FakeChatLLMProvider([ChatProviderResponse(content="Next answer.")])
    orchestrator = ChatConversationOrchestrator(
        providers=ChatProviderRegistry([provider]),
        router=ChatModelRouter(),
        resolver=ChatModelResolver(ChatModelSettings(provider="fake")),
    )

    orchestrator.run(
        context=ChatExecutionContext(user_id=1, organization_id=10),
        user_message="Next question",
        history=(
            ChatModelMessage(role=ChatModelRole.USER, content="Earlier question"),
            ChatModelMessage(role=ChatModelRole.ASSISTANT, content="Earlier answer"),
        ),
    )

    assert [message.role for message in provider.requests[0].messages] == [
        ChatModelRole.USER,
        ChatModelRole.ASSISTANT,
        ChatModelRole.USER,
    ]
