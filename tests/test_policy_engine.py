from __future__ import annotations

from verification.backend.shared.policy import evaluate_policy
from verification.backend.shared.policy.engine import _match_condition


def _base_payload() -> dict:
    return {
        "verification": {"state": "IL", "ntee_category": "Human Services"},
        "source_record": {"subsection": "03"},
        "state_compliance": {"registration_status": "active", "solicitation_permitted": True, "compliance_flags": []},
        "scores": {"overall": 72},
        "score_explanation": {
            "eligibility": "ELIGIBLE",
            "factors": {"narrative_missing": False, "stale_filing_days": 120},
        },
        "decision": {
            "status": "approve",
            "risk_flags": [],
            "manual_review": {"reason_codes": []},
        },
        "enrichment": {"providers": [], "failures": []},
        "integration_evaluation": {
            "integrations": [],
            "attempted_integrations": [],
            "used_integrations": [],
            "required_unmet_integrations": [],
            "failure_integrations": [],
        },
    }


def test_no_policy_provided_uses_default():
    payload = _base_payload()
    result = evaluate_policy(payload, None)
    assert result["policy_id"] == "global_default"
    assert result["overrides_decision"] is False
    assert result["final_recommendation"] == "approve"


def test_default_policy_only():
    payload = _base_payload()
    result = evaluate_policy(payload, "global_default")
    assert result["result"] == "no_match"
    assert result["matched_rules"] == []


def test_named_policy_escalates_to_manual_review():
    payload = _base_payload()
    payload["decision"]["risk_flags"] = ["missing_governance_disclosures"]
    payload["score_explanation"]["factors"]["narrative_missing"] = True
    result = evaluate_policy(payload, "strict_manual")
    assert result["overrides_decision"] is True
    assert result["final_recommendation"] == "manual_review"
    assert result["matched_rules"][0]["rule_id"] == "strict_gov_or_enrichment_review"


def test_named_policy_denies():
    payload = _base_payload()
    payload["scores"]["overall"] = 50
    result = evaluate_policy(payload, "strict_deny")
    assert result["overrides_decision"] is True
    assert result["final_recommendation"] == "deny"


def test_named_policy_relaxes_to_approve_with_review_when_allowed():
    payload = _base_payload()
    payload["decision"]["status"] = "manual_review"
    payload["scores"]["overall"] = 58
    result = evaluate_policy(payload, "relaxed_review")
    assert result["overrides_decision"] is True
    assert result["final_recommendation"] == "approve_with_review"


def test_named_policy_manual_review_when_compliance_flag_present():
    payload = _base_payload()
    payload["state_compliance"]["compliance_flags"] = ["state_registration_expiring_soon"]
    result = evaluate_policy(payload, "strict_manual")
    assert result["final_recommendation"] == "manual_review"


def test_policy_matches_required_integrations_missing_condition():
    payload = _base_payload()
    payload["integration_evaluation"]["required_unmet_integrations"] = ["candid"]
    assert _match_condition("required_integrations_missing_gt", 0, payload) is True
    assert _match_condition("required_integrations_missing_in", ["candid"], payload) is True


def test_policy_condition_helper_supports_integration_failure_and_required_missing():
    payload = _base_payload()
    payload["integration_evaluation"]["required_unmet_integrations"] = ["candid"]
    payload["integration_evaluation"]["failure_integrations"] = ["ofac"]
    assert _match_condition("integration_failures_in", ["ofac"], payload) is True

