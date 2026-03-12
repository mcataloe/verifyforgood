from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MaterializedProfile:
    pk: str
    sk: str
    ein: str
    organization: dict[str, Any]
    verification: dict[str, Any]
    scores: dict[str, Any]
    score_explanation: dict[str, Any]
    model_version: str
    source_hash: str
    materialized_at: str
    environment: str
    source_data_versions: dict[str, Any]
    latest_filing: dict[str, Any] | None = None
    enrichment: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    audit: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    policy_evaluation: dict[str, Any] | None = None
    final_recommendation: str | None = None
    state_compliance: dict[str, Any] | None = None
    external_signals: dict[str, Any] | None = None

    def to_item(self) -> dict[str, Any]:
        item = {
            "pk": self.pk,
            "sk": self.sk,
            "ein": self.ein,
            "organization": self.organization,
            "verification": self.verification,
            "scores": self.scores,
            "score_explanation": self.score_explanation,
            "model_version": self.model_version,
            "source_hash": self.source_hash,
            "materialized_at": self.materialized_at,
            "environment": self.environment,
            "source_data_versions": self.source_data_versions,
        }
        if self.latest_filing is not None:
            item["latest_filing"] = self.latest_filing
        if self.enrichment is not None:
            item["enrichment"] = self.enrichment
        if self.decision is not None:
            item["decision"] = self.decision
        if self.summary is not None:
            item["summary"] = self.summary
        if self.audit is not None:
            item["audit"] = self.audit
        if self.evidence is not None:
            item["evidence"] = self.evidence
        if self.policy_evaluation is not None:
            item["policy_evaluation"] = self.policy_evaluation
        if self.final_recommendation is not None:
            item["final_recommendation"] = self.final_recommendation
        if self.state_compliance is not None:
            item["state_compliance"] = self.state_compliance
        if self.external_signals is not None:
            item["external_signals"] = self.external_signals
        return item
