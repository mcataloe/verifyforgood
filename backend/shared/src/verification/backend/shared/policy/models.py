from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PolicyOutcome = Literal["approve", "approve_with_review", "manual_review", "deny", "insufficient_data"]


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    description: str
    when: dict[str, Any]
    outcome: PolicyOutcome
    override_decision: bool = True
    priority: int = 100


@dataclass(frozen=True)
class PolicyDefinition:
    policy_id: str
    rules: list[PolicyRule]


@dataclass(frozen=True)
class PolicyEvaluation:
    policy_id: str
    result: str
    matched_rules: list[dict[str, Any]]
    overrides_decision: bool
    final_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "result": self.result,
            "matched_rules": self.matched_rules,
            "overrides_decision": self.overrides_decision,
            "final_recommendation": self.final_recommendation,
        }
