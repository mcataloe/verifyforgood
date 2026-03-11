from __future__ import annotations

from charity_status.policy import evaluate_policy


def _base_payload() -> dict:
    return {
        "verification": {"state": "IL", "ntee_category": "Human Services"},
        "source_record": {"subsection": "03"},
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
