from __future__ import annotations

from typing import Any

from verification.policy.config import DEFAULT_POLICY_ID, POLICIES
from verification.policy.models import PolicyDefinition, PolicyEvaluation, PolicyRule


def evaluate_policy(payload: dict[str, Any], policy_id: str | None) -> dict[str, Any]:
    selected_id = (policy_id or DEFAULT_POLICY_ID).strip() or DEFAULT_POLICY_ID
    policy = _get_policy(selected_id)
    decision_status = str((payload.get("decision") or {}).get("status") or "insufficient_data")

    matched = [rule for rule in _ordered_rules(policy.rules) if _matches(rule, payload)]
    matched_rules = [
        {
            "rule_id": rule.rule_id,
            "description": rule.description,
            "outcome": rule.outcome,
            "override_decision": rule.override_decision,
            "priority": rule.priority,
        }
        for rule in matched
    ]

    selected_override = next((rule for rule in matched if rule.override_decision), None)
    overrides = selected_override is not None
    final_recommendation = selected_override.outcome if selected_override else decision_status
    result = "matched" if matched else "no_match"

    return PolicyEvaluation(
        policy_id=policy.policy_id,
        result=result,
        matched_rules=matched_rules,
        overrides_decision=overrides,
        final_recommendation=final_recommendation,
    ).to_dict()


def _get_policy(policy_id: str) -> PolicyDefinition:
    policy = POLICIES.get(policy_id)
    if policy is None:
        raise ValueError(f"Unknown policy_id: {policy_id}")
    return policy


def _ordered_rules(rules: list[PolicyRule]) -> list[PolicyRule]:
    return sorted(rules, key=lambda rule: (-rule.priority, rule.rule_id))


def _matches(rule: PolicyRule, payload: dict[str, Any]) -> bool:
    conditions = rule.when or {}
    for key, expected in conditions.items():
        if not _match_condition(key, expected, payload):
            return False
    return True


def _match_condition(key: str, expected: Any, payload: dict[str, Any]) -> bool:
    verification = payload.get("verification") or {}
    scores = payload.get("scores") or {}
    score_explanation = payload.get("score_explanation") or {}
    decision = payload.get("decision") or {}
    source_record = payload.get("source_record") or {}
    enrichment = payload.get("enrichment") or {}
    integration_evaluation = payload.get("integration_evaluation") or {}
    state_compliance = payload.get("state_compliance") or {}
    external_signals = payload.get("external_signals") or {}
    risk_flags = set((decision.get("risk_flags") or []))
    manual_codes = set(((decision.get("manual_review") or {}).get("reason_codes") or []))

    if key == "eligibility_in":
        return str(score_explanation.get("eligibility")) in set(str(v) for v in expected)
    if key == "decision_in":
        return str(decision.get("status")) in set(str(v) for v in expected)
    if key == "min_overall_score":
        return _to_float(scores.get("overall")) >= float(expected)
    if key == "max_overall_score":
        return _to_float(scores.get("overall")) <= float(expected)
    if key == "stale_filing_days_gt":
        stale_days = _to_float((score_explanation.get("factors") or {}).get("stale_filing_days"))
        return stale_days > float(expected)
    if key == "missing_governance_disclosures":
        actual = (
            "missing_governance_disclosures" in risk_flags
            or "missing_governance_disclosures" in manual_codes
            or (score_explanation.get("factors") or {}).get("narrative_missing") is True
        )
        return bool(actual) is bool(expected)
    if key == "enrichment_failures_gt":
        failures = integration_evaluation.get("failure_integrations") or []
        if not failures:
            failures = [
                str(item.get("integration_id") or item.get("provider") or "")
                for item in (enrichment.get("failures") or [])
                if isinstance(item, dict)
            ]
        return len([item for item in failures if item]) > int(expected)
    if key == "required_integrations_missing_gt":
        missing = integration_evaluation.get("required_unmet_integrations") or []
        return len(missing) > int(expected)
    if key == "required_integrations_missing_in":
        missing = set(str(item) for item in (integration_evaluation.get("required_unmet_integrations") or []))
        return any(str(item) in missing for item in expected)
    if key == "integration_failures_in":
        failures = set(str(item) for item in (integration_evaluation.get("failure_integrations") or []))
        return any(str(item) in failures for item in expected)
    if key == "state_in":
        return str(verification.get("state")) in set(str(v) for v in expected)
    if key == "subsection_in":
        return str(source_record.get("subsection")) in set(str(v) for v in expected)
    if key == "cause_in":
        return str(verification.get("ntee_category")) in set(str(v) for v in expected)
    if key == "compliance_flag_present":
        has_flags = len(state_compliance.get("compliance_flags") or []) > 0
        return has_flags is bool(expected)
    if key == "registration_status_in":
        return str(state_compliance.get("registration_status")) in set(str(v) for v in expected)
    if key == "solicitation_permitted":
        return state_compliance.get("solicitation_permitted") is bool(expected)
    if key == "sanctions_match":
        return bool((external_signals.get("sanctions") or {}).get("sanctions_match")) is bool(expected)
    if key == "federal_awards_min":
        count = _to_float((external_signals.get("federal_awards") or {}).get("award_count"))
        return count >= float(expected)
    if key == "state_business_status_in":
        status = (external_signals.get("state_business") or {}).get("entity_status")
        return str(status) in set(str(v) for v in expected)

    return False


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

