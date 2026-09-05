from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class ChatModelRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ChatToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ChatToolRequest:
    request_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatModelMessage:
    role: ChatModelRole
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    tool_requests: tuple[ChatToolRequest, ...] = ()


@dataclass(frozen=True)
class ChatProviderRequest:
    messages: tuple[ChatModelMessage, ...]
    tools: tuple[ChatToolDefinition, ...]
    model: str
    max_tokens: int = 512
    temperature: float = 0.0


@dataclass(frozen=True)
class ChatProviderResponse:
    content: str
    tool_requests: tuple[ChatToolRequest, ...] = ()
    finish_reason: str = "stop"
    provider: str = ""
    model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, int | float] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatExecutionContext:
    user_id: int
    organization_id: int
    request_id: str | None = None


@dataclass(frozen=True)
class ChatToolExecutionResult:
    request_id: str
    name: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ChatToolExecutor(Protocol):
    def definitions(self, context: ChatExecutionContext) -> tuple[ChatToolDefinition, ...]: ...

    def execute(
        self,
        request: ChatToolRequest,
        context: ChatExecutionContext,
    ) -> ChatToolExecutionResult: ...


class ChatInputPolicy(Protocol):
    def validate(self, content: str, context: ChatExecutionContext) -> str: ...


class ChatOutputPolicy(Protocol):
    def apply(self, content: str, context: ChatExecutionContext) -> str: ...
