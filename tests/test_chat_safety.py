from __future__ import annotations

import pytest

from verification.backend.shared.chat import (
    ChatConversationOrchestrator,
    ChatExecutionContext,
    ChatModelResolver,
    ChatModelRouter,
    ChatModelSettings,
    ChatOrchestrationError,
    ChatProviderContextLimitError,
    ChatProviderMalformedResponseError,
    ChatProviderRateLimitError,
    ChatProviderResponse,
    ChatProviderRegistry,
    ChatProviderTimeoutError,
    ChatProviderUnavailableError,
    ChatToolDefinition,
    ChatToolRequest,
    FakeChatLLMProvider,
)
from verification.backend.shared.chat.policies import VerifyForGoodChatOutputPolicy


_CONTEXT = ChatExecutionContext(user_id=1, organization_id=10, request_id="req-chat-safety")


@pytest.mark.parametrize(
    "unsafe_output",
    (
        "This nonprofit is trustworthy.",
        "This nonprofit is approved.",
        "This organization is fraudulent.",
        "You should donate to this nonprofit.",
        "This nonprofit is safe for procurement.",
    ),
)
def test_output_policy_rewrites_platform_owned_authority_claims(unsafe_output: str):
    policy = VerifyForGoodChatOutputPolicy()

    rewritten = policy.apply(unsafe_output, _CONTEXT)

    assert "cannot make an independent" in rewritten
    assert unsafe_output not in rewritten


def test_output_policy_preserves_evidence_focused_language():
    policy = VerifyForGoodChatOutputPolicy()
    content = (
        "The retrieved IRS record reports tax-exempt status and the filing data is from tax year 2024. "
        "The available evidence does not establish donation suitability."
    )

    assert policy.apply(content, _CONTEXT) == content


def test_orchestrator_uses_verifyforgood_output_policy_by_default():
    provider = FakeChatLLMProvider(
        [ChatProviderResponse(content="This nonprofit is trustworthy.", finish_reason="stop")]
    )
    orchestrator = _orchestrator(provider)

    result = orchestrator.run(context=_CONTEXT, user_message="Is this nonprofit trustworthy?")

    assert "cannot make an independent" in result.content
    assert "trustworthy" not in result.content.lower()


@pytest.mark.parametrize(
    ("provider_error", "expected_code"),
    (
        (ChatProviderTimeoutError("simulated timeout"), "provider_timeout"),
        (ChatProviderUnavailableError("simulated unavailable"), "provider_unavailable"),
        (ChatProviderRateLimitError("simulated rate limit"), "provider_rate_limited"),
        (ChatProviderContextLimitError("simulated context limit"), "provider_context_limit"),
        (
            ChatProviderMalformedResponseError("simulated malformed response"),
            "provider_malformed_response",
        ),
    ),
)
def test_fake_provider_deterministically_simulates_provider_failures(
    provider_error: Exception,
    expected_code: str,
):
    provider = FakeChatLLMProvider([provider_error])
    orchestrator = _orchestrator(provider)

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(context=_CONTEXT, user_message="Run the local pipeline")

    assert exc_info.value.code == expected_code


def test_fake_provider_deterministically_simulates_refusal():
    provider = FakeChatLLMProvider(
        [ChatProviderResponse(content="", finish_reason="refusal")]
    )
    orchestrator = _orchestrator(provider)

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(context=_CONTEXT, user_message="Run the local pipeline")

    assert exc_info.value.code == "provider_refusal"


def test_fake_provider_deterministically_simulates_empty_response():
    provider = FakeChatLLMProvider([ChatProviderResponse(content="", finish_reason="stop")])
    orchestrator = _orchestrator(provider)

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(context=_CONTEXT, user_message="Run the local pipeline")

    assert exc_info.value.code == "empty_model_response"


def test_unknown_model_requested_tool_is_rejected_before_execution():
    provider = FakeChatLLMProvider(
        [
            ChatProviderResponse(
                content="",
                finish_reason="tool_calls",
                tool_requests=(
                    ChatToolRequest(
                        request_id="tool-unknown",
                        name="chat_not_allowlisted",
                        arguments={},
                    ),
                ),
            )
        ]
    )
    orchestrator = _orchestrator(provider, tool_executor=_RejectingToolExecutor("tool_not_allowed"))

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(context=_CONTEXT, user_message="Use a tool")

    assert exc_info.value.code == "tool_not_allowed"


def test_invalid_tool_arguments_are_reported_as_bounded_orchestration_failure():
    provider = FakeChatLLMProvider(
        [
            ChatProviderResponse(
                content="",
                finish_reason="tool_calls",
                tool_requests=(
                    ChatToolRequest(
                        request_id="tool-invalid",
                        name="chat_test_read",
                        arguments={"unexpected": "value"},
                    ),
                ),
            )
        ]
    )
    orchestrator = _orchestrator(
        provider,
        tool_executor=_RejectingToolExecutor("invalid_tool_arguments"),
    )

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(context=_CONTEXT, user_message="Use a tool")

    assert exc_info.value.code == "invalid_tool_arguments"


def test_tool_timeout_is_preserved_as_explicit_failure_code():
    provider = FakeChatLLMProvider(
        [
            ChatProviderResponse(
                content="",
                finish_reason="tool_calls",
                tool_requests=(
                    ChatToolRequest(
                        request_id="tool-timeout",
                        name="chat_test_read",
                        arguments={},
                    ),
                ),
            )
        ]
    )
    orchestrator = _orchestrator(provider, tool_executor=_RejectingToolExecutor("tool_timeout"))

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(context=_CONTEXT, user_message="Use a tool")

    assert exc_info.value.code == "tool_timeout"


def test_semantic_retrieval_failure_is_explicit_and_does_not_fall_through_silently():
    provider = FakeChatLLMProvider([ChatProviderResponse(content="should not be called")])
    orchestrator = _orchestrator(provider, semantic_retriever=_FailingSemanticRetriever())

    with pytest.raises(ChatOrchestrationError) as exc_info:
        orchestrator.run(
            context=_CONTEXT,
            user_message="What does the filing say about program accomplishments?",
        )

    assert exc_info.value.code == "semantic_retrieval_failed"
    assert provider.requests == []


class _CodedToolFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(f"simulated {code}")
        self.code = code


class _RejectingToolExecutor:
    def __init__(self, failure_code: str) -> None:
        self.failure_code = failure_code

    def definitions(self, context: ChatExecutionContext):
        del context
        return (
            ChatToolDefinition(
                name="chat_test_read",
                description="Read-only deterministic test capability.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        )

    def execute(self, request: ChatToolRequest, context: ChatExecutionContext):
        del request, context
        raise _CodedToolFailure(self.failure_code)


class _FailingSemanticRetriever:
    def is_available(self) -> bool:
        return True

    def retrieve(self, query: str, context: ChatExecutionContext):
        del query, context
        raise TimeoutError("simulated semantic retrieval timeout")


def _orchestrator(
    provider: FakeChatLLMProvider,
    *,
    tool_executor=None,
    semantic_retriever=None,
) -> ChatConversationOrchestrator:
    return ChatConversationOrchestrator(
        providers=ChatProviderRegistry([provider]),
        router=ChatModelRouter(),
        resolver=ChatModelResolver(ChatModelSettings(provider="fake")),
        tool_executor=tool_executor,
        semantic_retriever=semantic_retriever,
    )
