from __future__ import annotations

from dataclasses import dataclass

from verification.state_registry.models import MatchConfidence
from verification.state_registry.normalization import normalize_entity_name


@dataclass(frozen=True)
class NameMatchResult:
    matched_on: str
    confidence: MatchConfidence

    def to_dict(self) -> dict[str, str]:
        return {
            "matched_on": self.matched_on,
            "confidence": self.confidence.value,
        }


def classify_name_match(
    query_name: str | None,
    entity_name: str | None,
    normalized_entity_name: str | None = None,
) -> NameMatchResult | None:
    normalized_query = normalize_entity_name(query_name)
    normalized_candidate = normalized_entity_name or normalize_entity_name(entity_name)
    if not normalized_query or not normalized_candidate:
        return None
    if normalized_query == normalized_candidate:
        return NameMatchResult(matched_on="normalized_entity_name", confidence=MatchConfidence.HIGH)
    if normalized_candidate.startswith(normalized_query) or normalized_query.startswith(normalized_candidate):
        return NameMatchResult(matched_on="name_prefix", confidence=MatchConfidence.MEDIUM)

    query_tokens = set(normalized_query.split())
    candidate_tokens = set(normalized_candidate.split())
    if not query_tokens or not candidate_tokens:
        return None
    overlap = len(query_tokens & candidate_tokens) / max(len(query_tokens), len(candidate_tokens))
    if overlap >= 0.75:
        return NameMatchResult(matched_on="token_overlap", confidence=MatchConfidence.MEDIUM)
    if overlap >= 0.5:
        return NameMatchResult(matched_on="token_overlap", confidence=MatchConfidence.LOW)
    return None

