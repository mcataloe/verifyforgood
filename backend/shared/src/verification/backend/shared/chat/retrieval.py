from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from .contracts import ChatExecutionContext


class ChatRetrievalMode(str, Enum):
    STRUCTURED = "structured"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    MODEL_ONLY = "model_only"


@dataclass(frozen=True)
class ChatRetrievalRoute:
    mode: ChatRetrievalMode
    reason_code: str


@dataclass(frozen=True)
class ChatSemanticRetrievalResult:
    content: str
    metadata: dict[str, object] = field(default_factory=dict)


class ChatSemanticRetriever(Protocol):
    def is_available(self) -> bool: ...

    def retrieve(
        self,
        query: str,
        context: ChatExecutionContext,
    ) -> ChatSemanticRetrievalResult | None: ...


class DisabledChatSemanticRetriever:
    def is_available(self) -> bool:
        return False

    def retrieve(
        self,
        query: str,
        context: ChatExecutionContext,
    ) -> ChatSemanticRetrievalResult | None:
        del query, context
        return None


class ChatRetrievalRouter:
    _SEMANTIC_MARKERS = (
        "narrative",
        "mission description",
        "program accomplishments",
        "program description",
        "themes",
        "what does the filing say",
        "what do the filings say",
        "language in the filing",
        "summarize the filing text",
    )

    def route(
        self,
        user_message: str,
        *,
        structured_available: bool,
        semantic_available: bool,
    ) -> ChatRetrievalRoute:
        normalized = " ".join(str(user_message or "").strip().lower().split())
        wants_semantic = any(marker in normalized for marker in self._SEMANTIC_MARKERS)
        if wants_semantic and structured_available and semantic_available:
            return ChatRetrievalRoute(
                mode=ChatRetrievalMode.HYBRID,
                reason_code="structured_plus_unstructured_evidence",
            )
        if wants_semantic and semantic_available:
            return ChatRetrievalRoute(
                mode=ChatRetrievalMode.SEMANTIC,
                reason_code="unstructured_evidence_requested",
            )
        if structured_available:
            return ChatRetrievalRoute(
                mode=ChatRetrievalMode.STRUCTURED,
                reason_code=(
                    "semantic_unavailable_use_structured"
                    if wants_semantic
                    else "deterministic_application_data_available"
                ),
            )
        if semantic_available:
            return ChatRetrievalRoute(
                mode=ChatRetrievalMode.SEMANTIC,
                reason_code="semantic_retriever_only",
            )
        return ChatRetrievalRoute(
            mode=ChatRetrievalMode.MODEL_ONLY,
            reason_code="no_retrieval_capability_available",
        )
