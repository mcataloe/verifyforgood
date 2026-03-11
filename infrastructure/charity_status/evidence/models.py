from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EvidenceCategory = Literal[
    "eligibility_compliance",
    "financial_resilience",
    "transparency",
    "governance_quality",
    "peer_benchmarking",
    "enrichment",
]
EvidencePolarity = Literal["positive", "negative", "warning", "neutral"]
EvidenceSeverity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class EvidenceFactor:
    key: str
    category: EvidenceCategory
    polarity: EvidencePolarity
    severity: EvidenceSeverity
    value: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "polarity": self.polarity,
            "severity": self.severity,
            "value": self.value,
            "message": self.message,
        }


@dataclass(frozen=True)
class EvidenceSource:
    source: str
    used: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        item = {"source": self.source, "used": self.used}
        if self.detail:
            item["detail"] = self.detail
        return item


@dataclass(frozen=True)
class EvidenceRuleResult:
    rule: str
    passed: bool
    severity: EvidenceSeverity
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class Evidence:
    factors: list[EvidenceFactor]
    sources: list[EvidenceSource]
    rule_results: list[EvidenceRuleResult]
    confidence: str
    generated_at: str
    model_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "factors": [factor.to_dict() for factor in self.factors],
            "sources": [source.to_dict() for source in self.sources],
            "rule_results": [result.to_dict() for result in self.rule_results],
            "confidence": self.confidence,
            "generated_at": self.generated_at,
            "model_version": self.model_version,
        }
