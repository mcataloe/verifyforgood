from __future__ import annotations

from charity_status.policy.models import PolicyDefinition, PolicyRule


DEFAULT_POLICY_ID = "global_default"


POLICIES: dict[str, PolicyDefinition] = {
    "global_default": PolicyDefinition(
        policy_id="global_default",
        rules=[],
    ),
    "strict_manual": PolicyDefinition(
        policy_id="strict_manual",
        rules=[
            PolicyRule(
                rule_id="strict_gov_or_enrichment_review",
                description="Escalate to manual review when governance/enrichment warning signals exist.",
                when={"missing_governance_disclosures": True, "max_overall_score": 100},
                outcome="manual_review",
                override_decision=True,
                priority=90,
            ),
            PolicyRule(
                rule_id="strict_enrichment_failure_review",
                description="Escalate to manual review when enrichment providers fail.",
                when={"enrichment_failures_gt": 0, "max_overall_score": 100},
                outcome="manual_review",
                override_decision=True,
                priority=80,
            ),
        ],
    ),
    "strict_deny": PolicyDefinition(
        policy_id="strict_deny",
        rules=[
            PolicyRule(
                rule_id="deny_low_score",
                description="Deny when overall score is below customer floor.",
                when={"max_overall_score": 64},
                outcome="deny",
                override_decision=True,
                priority=100,
            )
        ],
    ),
    "relaxed_review": PolicyDefinition(
        policy_id="relaxed_review",
        rules=[
            PolicyRule(
                rule_id="relax_to_approve_with_review",
                description="Allow approve_with_review for medium-quality organizations above threshold.",
                when={
                    "decision_in": ["manual_review"],
                    "min_overall_score": 55,
                    "max_overall_score": 69,
                    "eligibility_in": ["ELIGIBLE"],
                },
                outcome="approve_with_review",
                override_decision=True,
                priority=60,
            )
        ],
    ),
}
