from infrastructure.charity_status.decision.engine import build_decision


def _base_inputs():
    organization = {"ein": "12-3456789", "name": "Example Org"}
    verification = {"irs_status": "active", "tax_deductible": True, "recent_990_on_file": True}
    scores = {"overall": 82}
    score_explanation = {
        "model_version": "2.0.0",
        "score_data_sources": ["irs_eo_bmf_athena", "irs_form_990_xml"],
        "eligibility": "ELIGIBLE",
        "peer_benchmarking_used": True,
        "peer_group": {"ntee": "P", "org_type": "03", "revenue_band": "1m_to_10m"},
        "peer_group_size": 100,
        "factors": {
            "active_status": True,
            "program_expense_ratio": 0.8,
            "liabilities_to_assets_ratio": 0.4,
            "narrative_missing": False,
            "name_match": True,
        },
        "confidence": "high",
    }
    name_verification = {"name_match": True}
    filing_summary = {"tax_year": "2023"}
    enrichment = {"providers": [], "failures": []}
    return organization, verification, scores, score_explanation, name_verification, filing_summary, enrichment


def test_decision_approve():
    decision, extras = build_decision(*_base_inputs())

    assert decision["status"] == "approve"
    assert "irs_active" in decision["reasons"]
    assert extras["audit"]["model_version"] == "2.0.0"
    assert extras["summary"]["decision_status"] == "approve"


def test_decision_approve_with_review_from_name_mismatch():
    args = list(_base_inputs())
    args[4] = {"name_match": False}
    decision, _ = build_decision(*args)

    assert decision["status"] == "approve_with_review"
    assert "ein_name_mismatch" in decision["manual_review"]["reason_codes"]


def test_decision_manual_review_low_score():
    args = list(_base_inputs())
    args[2] = {"overall": 55}
    decision, _ = build_decision(*args)

    assert decision["status"] == "manual_review"


def test_decision_deny_ineligible():
    args = list(_base_inputs())
    args[1] = {"irs_status": "inactive", "tax_deductible": True, "recent_990_on_file": False}
    args[3] = {**args[3], "eligibility": "INELIGIBLE", "factors": {**args[3]["factors"], "active_status": False}}
    decision, _ = build_decision(*args)

    assert decision["status"] == "deny"
    assert "ineligible_status" in decision["risk_flags"]


def test_decision_insufficient_data():
    args = list(_base_inputs())
    args[2] = {"overall": None}
    decision, _ = build_decision(*args)

    assert decision["status"] == "insufficient_data"


def test_decision_enrichment_failure_flag():
    args = list(_base_inputs())
    args[6] = {"providers": [], "failures": [{"provider": "candid", "error": "timeout"}]}
    decision, extras = build_decision(*args)

    assert "enrichment_provider_failures" in decision["risk_flags"]
    assert extras["audit"]["enrichments_used"] is False


def test_decision_manual_review_when_required_integrations_unmet():
    args = list(_base_inputs())
    decision, extras = build_decision(
        *args,
        integration_evaluation={
            "integrations": [
                {
                    "integration_id": "candid",
                    "required_for_eligibility": True,
                    "availability_status": "not_offered",
                }
            ],
            "attempted_integrations": [],
            "used_integrations": [],
            "required_unmet_integrations": ["candid"],
            "failure_integrations": [],
        },
    )

    assert decision["status"] == "manual_review"
    assert "required_integration_unavailable" in decision["risk_flags"]
    assert extras["audit"]["required_unmet_integrations"] == ["candid"]
