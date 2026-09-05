from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    ChatExecutionContext,
    ChatInputPolicy,
    ChatModelMessage,
    ChatModelRole,
    ChatOutputPolicy,
    ChatProviderRequest,
    ChatToolExecutionResult,
    ChatToolExecutor,
)
from .providers import ChatProviderError, ChatProviderRegistry
from .routing import ChatModelResolver, ChatModelRoute, ChatModelRouter, ResolvedChatModel


class ChatOrchestrationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ChatInvocationDiagnostic:
    iteration: int
    tier: str
    route_reason: str
    provider: str
    model: str
    finish_reason: str
    tool_request_names: tuple[str, ...]
    usage: dict[str, int | float]


@dataclass(frozen=True)
class ChatOrchestrationResult:
    content: str
    route: ChatModelRoute
    resolved_model: ResolvedChatModel
    diagnostics: tuple[ChatInvocationDiagnostic, ...]
    tool_results: tuple[ChatToolExecutionResult, ...]


class DefaultChatInputPolicy:
    def __init__(self, *, max_characters: int = 16_000) -> None:
        self._max_characters = max(1, int(max_characters))

    def validate(self, content: str, context: ChatExecutionContext) -> str:
        del context
        normalized = str(content or "").strip()
        if not normalized:
            raise ChatOrchestrationError("invalid_input", "Chat message is required")
        if len(normalized) > self._max_characters:
            raise ChatOrchestrationError("input_too_large", "Chat message exceeds the local input limit")
        return normalized


class PassThroughChatOutputPolicy:
    def apply(self, content: str, context: ChatExecutionContext) -> str:
        del context
        return str(content or "").strip()


class ChatConversationOrchestrator:
    def __init__(
        self,
        *,
        providers: ChatProviderRegistry,
        router: ChatModelRouter,
        resolver: ChatModelResolver,
        tool_executor: ChatToolExecutor | None = None,
        input_policy: ChatInputPolicy | None = None,
        output_policy: ChatOutputPolicy | None = None,
        max_tool_iterations: int = 4,
    ) -> None:
        self._providers = providers
        self._router = router
        self._resolver = resolver
        self._tool_executor = tool_executor
        self._input_policy = input_policy or DefaultChatInputPolicy()
        self._output_policy = output_policy or PassThroughChatOutputPolicy()
        self._max_tool_iterations = max(0, int(max_tool_iterations))

    def run(
        self,
        *,
        context: ChatExecutionContext,
        user_message: str,
        history: tuple[ChatModelMessage, ...] = (),
    ) -> ChatOrchestrationResult:
        normalized_user_message = self._input_policy.validate(user_message, context)
        route = self._router.route(
            normalized_user_message,
            conversation_message_count=len(history),
        )
        resolved = self._resolver.resolve(route)
        provider = self._providers.get(resolved.provider)
        tools = self._tool_executor.definitions(context) if self._tool_executor is not None else ()
        messages = [*history, ChatModelMessage(role=ChatModelRole.USER, content=normalized_user_message)]
        diagnostics: list[ChatInvocationDiagnostic] = []
        tool_results: list[ChatToolExecutionResult] = []

        for iteration in range(self._max_tool_iterations + 1):
            try:
                response = provider.generate(
                    ChatProviderRequest(
                        messages=tuple(messages),
                        tools=tuple(tools),
                        model=resolved.model,
                        max_tokens=resolved.max_tokens,
                        temperature=resolved.temperature,
                    )
                )
            except ChatProviderError as exc:
                raise ChatOrchestrationError(exc.code, str(exc)) from exc

            diagnostics.append(
                ChatInvocationDiagnostic(
                    iteration=iteration,
                    tier=resolved.tier.value,
                    route_reason=resolved.reason_code,
                    provider=response.provider or resolved.provider,
                    model=response.model or resolved.model,
                    finish_reason=response.finish_reason,
                    tool_request_names=tuple(request.name for request in response.tool_requests),
                    usage=dict(response.usage),
                )
            )

            if response.tool_requests:
                if self._tool_executor is None:
                    raise ChatOrchestrationError(
                        "tool_request_unavailable",
                        "The model requested a tool but no tool executor is configured",
                    )
                if iteration >= self._max_tool_iterations:
                    raise ChatOrchestrationError(
                        "tool_iteration_limit",
                        "The model exceeded the bounded tool iteration limit",
                    )
                messages.append(
                    ChatModelMessage(
                        role=ChatModelRole.ASSISTANT,
                        content=response.content,
                        tool_requests=response.tool_requests,
                    )
                )
                for request in response.tool_requests:
                    result = self._tool_executor.execute(request, context)
                    tool_results.append(result)
                    messages.append(
                        ChatModelMessage(
                            role=ChatModelRole.TOOL,
                            content=result.content,
                            name=result.name,
                            tool_call_id=result.request_id,
                        )
                    )
                continue

            if response.finish_reason.lower() in {"refusal", "refused"}:
                raise ChatOrchestrationError("provider_refusal", "The model refused the request")
            final_content = self._output_policy.apply(response.content, context)
            if not final_content:
                raise ChatOrchestrationError("empty_model_response", "The model returned an empty response")
            return ChatOrchestrationResult(
                content=final_content,
                route=route,
                resolved_model=resolved,
                diagnostics=tuple(diagnostics),
                tool_results=tuple(tool_results),
            )

        raise ChatOrchestrationError("tool_iteration_limit", "The bounded tool loop did not terminate")
