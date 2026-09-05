from __future__ import annotations

import json
import socket
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

from .contracts import (
    ChatModelMessage,
    ChatModelRole,
    ChatProviderRequest,
    ChatProviderResponse,
    ChatToolDefinition,
    ChatToolRequest,
)


class ChatProviderError(RuntimeError):
    code = "provider_error"


class ChatProviderTimeoutError(ChatProviderError):
    code = "provider_timeout"


class ChatProviderUnavailableError(ChatProviderError):
    code = "provider_unavailable"


class ChatProviderRateLimitError(ChatProviderError):
    code = "provider_rate_limited"


class ChatProviderContextLimitError(ChatProviderError):
    code = "provider_context_limit"


class ChatProviderMalformedResponseError(ChatProviderError):
    code = "provider_malformed_response"


class ChatProviderRefusalError(ChatProviderError):
    code = "provider_refusal"


class ChatLLMProvider(Protocol):
    name: str

    def generate(self, request: ChatProviderRequest) -> ChatProviderResponse: ...


class ChatProviderRegistry:
    def __init__(self, providers: Sequence[ChatLLMProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def get(self, name: str) -> ChatLLMProvider:
        provider = self._providers.get(str(name).strip().lower())
        if provider is None:
            raise ChatProviderUnavailableError(f"Chat provider is not registered: {name}")
        return provider


class FakeChatLLMProvider:
    name = "fake"

    def __init__(self, steps: Sequence[ChatProviderResponse | Exception] | None = None) -> None:
        self._steps = list(steps or [])
        self.requests: list[ChatProviderRequest] = []

    def generate(self, request: ChatProviderRequest) -> ChatProviderResponse:
        self.requests.append(request)
        if not self._steps:
            return ChatProviderResponse(
                content="Fake local response.",
                finish_reason="stop",
                provider=self.name,
                model=request.model,
                metadata={"fake": True},
            )
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return ChatProviderResponse(
            content=step.content,
            tool_requests=step.tool_requests,
            finish_reason=step.finish_reason,
            provider=step.provider or self.name,
            model=step.model or request.model,
            metadata=dict(step.metadata),
            usage=dict(step.usage),
        )


OllamaTransport = Callable[[str, Mapping[str, Any], float], Mapping[str, Any]]


class OllamaChatLLMProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 30.0,
        transport: OllamaTransport | None = None,
    ) -> None:
        self._base_url = str(base_url).rstrip("/")
        self._timeout_seconds = max(0.1, float(timeout_seconds))
        self._transport = transport or _post_json

    def generate(self, request: ChatProviderRequest) -> ChatProviderResponse:
        if not str(request.model or "").strip():
            raise ChatProviderUnavailableError("Ollama model is not configured")
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [_ollama_message(message) for message in request.messages],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.tools:
            payload["tools"] = [_ollama_tool(tool) for tool in request.tools]

        raw = self._transport(f"{self._base_url}/api/chat", payload, self._timeout_seconds)
        if not isinstance(raw, Mapping):
            raise ChatProviderMalformedResponseError("Ollama returned a non-object response")
        message = raw.get("message")
        if not isinstance(message, Mapping):
            raise ChatProviderMalformedResponseError("Ollama response is missing message")

        tool_requests = _parse_ollama_tool_requests(message.get("tool_calls"))
        content = str(message.get("content") or "")
        finish_reason = str(raw.get("done_reason") or ("tool_calls" if tool_requests else "stop"))
        if finish_reason.lower() in {"refusal", "refused"}:
            raise ChatProviderRefusalError("Ollama refused the request")

        usage: dict[str, int | float] = {}
        for source_key, target_key in (
            ("prompt_eval_count", "input_tokens"),
            ("eval_count", "output_tokens"),
            ("total_duration", "total_duration_ns"),
            ("load_duration", "load_duration_ns"),
        ):
            value = raw.get(source_key)
            if isinstance(value, (int, float)):
                usage[target_key] = value

        metadata = {
            "done": bool(raw.get("done", False)),
            "created_at": raw.get("created_at"),
        }
        return ChatProviderResponse(
            content=content,
            tool_requests=tool_requests,
            finish_reason=finish_reason,
            provider=self.name,
            model=str(raw.get("model") or request.model),
            metadata=metadata,
            usage=usage,
        )


def _ollama_message(message: ChatModelMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": message.role.value,
        "content": message.content,
    }
    if message.name:
        payload["tool_name"] = message.name
    if message.tool_requests:
        payload["tool_calls"] = [
            {
                "function": {
                    "name": request.name,
                    "arguments": request.arguments,
                }
            }
            for request in message.tool_requests
        ]
    return payload


def _ollama_tool(tool: ChatToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _parse_ollama_tool_requests(value: Any) -> tuple[ChatToolRequest, ...]:
    if value in (None, []):
        return ()
    if not isinstance(value, list):
        raise ChatProviderMalformedResponseError("Ollama tool_calls must be a list")
    requests: list[ChatToolRequest] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise ChatProviderMalformedResponseError("Ollama tool call must be an object")
        function = item.get("function")
        if not isinstance(function, Mapping):
            raise ChatProviderMalformedResponseError("Ollama tool call is missing function")
        name = str(function.get("name") or "").strip()
        if not name:
            raise ChatProviderMalformedResponseError("Ollama tool call is missing a function name")
        arguments_value = function.get("arguments") or {}
        if isinstance(arguments_value, str):
            try:
                arguments_value = json.loads(arguments_value)
            except json.JSONDecodeError as exc:
                raise ChatProviderMalformedResponseError("Ollama tool arguments are not valid JSON") from exc
        if not isinstance(arguments_value, Mapping):
            raise ChatProviderMalformedResponseError("Ollama tool arguments must be an object")
        request_id = str(item.get("id") or f"ollama-tool-{index}")
        requests.append(
            ChatToolRequest(
                request_id=request_id,
                name=name,
                arguments=dict(arguments_value),
            )
        )
    return tuple(requests)


def _post_json(url: str, payload: Mapping[str, Any], timeout_seconds: float) -> Mapping[str, Any]:
    body = json.dumps(dict(payload)).encode("utf-8")
    http_request = urllib_request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib_request.urlopen(http_request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except urllib_error.HTTPError as exc:
        if exc.code == 429:
            raise ChatProviderRateLimitError("Ollama rate limited the request") from exc
        if exc.code in {408, 504}:
            raise ChatProviderTimeoutError("Ollama request timed out") from exc
        if exc.code in {400, 413}:
            raise ChatProviderContextLimitError("Ollama rejected the request size/context") from exc
        raise ChatProviderUnavailableError(f"Ollama HTTP error: {exc.code}") from exc
    except (urllib_error.URLError, ConnectionError) as exc:
        raise ChatProviderUnavailableError("Ollama is unavailable") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise ChatProviderTimeoutError("Ollama request timed out") from exc

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ChatProviderMalformedResponseError("Ollama returned invalid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ChatProviderMalformedResponseError("Ollama returned a non-object JSON response")
    return decoded
