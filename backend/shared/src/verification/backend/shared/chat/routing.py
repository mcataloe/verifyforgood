from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ChatModelTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ChatModelRoute:
    tier: ChatModelTier
    reason_code: str
    model_profile: str
    max_tokens: int
    temperature: float = 0.0


@dataclass(frozen=True)
class ResolvedChatModel:
    tier: ChatModelTier
    reason_code: str
    provider: str
    model: str
    model_profile: str
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class ChatModelSettings:
    provider: str = "ollama"
    local_model: str = ""
    low_model: str = ""
    medium_model: str = ""
    high_model: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "ChatModelSettings":
        return cls(
            provider=str(env.get("CHAT_PROVIDER", "ollama") or "ollama").strip().lower(),
            local_model=str(env.get("CHAT_LOCAL_MODEL", "") or "").strip(),
            low_model=str(env.get("CHAT_MODEL_LOW", "") or "").strip(),
            medium_model=str(env.get("CHAT_MODEL_MEDIUM", "") or "").strip(),
            high_model=str(env.get("CHAT_MODEL_HIGH", "") or "").strip(),
        )


class ChatModelConfigurationError(ValueError):
    pass


class ChatModelRouter:
    """Application-owned deterministic routing; no provider/model IDs are selected here."""

    _HIGH_MARKERS = (
        "multi-document",
        "multiple documents",
        "across all filings",
        "across the filings",
        "deep analysis",
        "complex analysis",
        "compare all",
        "across multiple",
    )
    _MEDIUM_MARKERS = (
        "compare",
        "difference",
        "differences",
        "trend",
        "summarize",
        "explain why",
        "why did",
        "multiple",
        "across the last",
    )

    def route(
        self,
        user_message: str,
        *,
        conversation_message_count: int = 0,
        expected_tool_count: int = 0,
    ) -> ChatModelRoute:
        normalized = " ".join(str(user_message or "").strip().lower().split())
        if len(normalized) >= 1200 or any(marker in normalized for marker in self._HIGH_MARKERS):
            return ChatModelRoute(
                tier=ChatModelTier.HIGH,
                reason_code="complex_or_long_context",
                model_profile="high_reasoning",
                max_tokens=1200,
            )
        if (
            len(normalized) >= 300
            or conversation_message_count >= 8
            or expected_tool_count >= 2
            or any(marker in normalized for marker in self._MEDIUM_MARKERS)
        ):
            return ChatModelRoute(
                tier=ChatModelTier.MEDIUM,
                reason_code="multi_fact_or_moderate_synthesis",
                model_profile="general_synthesis",
                max_tokens=800,
            )
        return ChatModelRoute(
            tier=ChatModelTier.LOW,
            reason_code="simple_or_single_fact",
            model_profile="low_latency",
            max_tokens=512,
        )


class ChatModelResolver:
    def __init__(self, settings: ChatModelSettings) -> None:
        self._settings = settings

    def resolve(self, route: ChatModelRoute) -> ResolvedChatModel:
        provider = self._settings.provider
        if provider not in {"ollama", "fake"}:
            raise ChatModelConfigurationError(f"Unsupported local chat provider: {provider}")

        override = {
            ChatModelTier.LOW: self._settings.low_model,
            ChatModelTier.MEDIUM: self._settings.medium_model,
            ChatModelTier.HIGH: self._settings.high_model,
        }[route.tier]
        model = override or self._settings.local_model
        if not model and provider == "fake":
            model = "fake-local"
        if not model:
            raise ChatModelConfigurationError(
                "CHAT_LOCAL_MODEL (or a tier-specific CHAT_MODEL_* override) is required for Ollama"
            )
        return ResolvedChatModel(
            tier=route.tier,
            reason_code=route.reason_code,
            provider=provider,
            model=model,
            model_profile=route.model_profile,
            max_tokens=route.max_tokens,
            temperature=route.temperature,
        )
