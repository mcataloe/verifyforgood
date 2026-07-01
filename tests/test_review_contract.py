from __future__ import annotations

from verification.backend.shared.review import build_review, ensure_review


def _payload(**overrides):
    payload = {
        "organization": {"ein": "123456789", "name": "Evidence Org"},
        "verification": {
            "irs_status": "active",
            "recent_990_on_file": True,
            "state": "IL",
            "tax_deductible": True,
        },
        "filing_summary": {
            "tax_year": "2024",
            "form_type": "990",
            "filing_date": "2025-05-01",
            "parse_status": "parsed",
        },
        "name_verification": {"name_match": True, "score": 0.98},
        "scores": {"overall": 1, "trust": 1, "compliance": 1},
        "score_explanation": {"eligibility": "INELIGIBLE"},
        "decision": {"status": "deny"},
        "policy_evaluation": {"final_recommendation": "deny"},
        "final_recommendation": "deny",
        "state_compliance": {},
        "external_signals": {},
        "integration_evaluation": {
            "integrations": [],
            "attempted_integrations": [],
            "used_integrations": [],
            "required_unmet_integrations": [],
            "failure_integrations": [],
        },
    }
    payload.update(overrides)
    return payload


def _check(review, check_id):
    return next(item for item in review["evidence_review"]["checks"] if item["check_id"] == check_id)


def test_review_complete_does_not_depend_on_legacy_scores_or_recommendation():
    review = build_review(_payload())

    assert review["contract_version"] == "1.0"
    assert review["evidence_review"]["status"] == "complete"
    assert review["requirements_evaluation"] is None
    assert review["customer_decision"] is None
    assert "deny" not in str(review)
    assert _check(review, "irs_status")["observed_value"] == "active"


def test_review_marks_stale_filing_without_claiming_legal_noncompliance():
    review = build_review(
        _payload(
            verification={
                "irs_status": "active",
                "recent_990_on_file": False,
                "state": "IL",
                "tax_deductible": True,
            }
        )
    )

    assert review["evidence_review"]["status"] == "stale"
    assert _check(review, "filing_recency")["status"] == "stale"
    assert "legal filing-obligation determination" in _check(review, "filing_recency")["limitations"][0]


def test_review_keeps_unavailable_required_source_distinct_from_no_match():
    review = build_review(
        _payload(
            integration_evaluation={
                "integrations": [
                    {
                        "integration_id": "candid",
                        "attempted": False,
                        "availability_status": "missing_credentials",
                        "required_for_eligibility": True,
                    }
                ],
                "required_unmet_integrations": ["candid"],
                "failure_integrations": [],
            }
        )
    )

    assert review["evidence_review"]["status"] == "source_unavailable"
    assert _check(review, "integration:candid")["status"] == "source_unavailable"


def test_review_marks_conflicting_checked_sources():
    review = build_review(
        _payload(
            state_compliance={
                "registration_status": "revoked",
                "registration_jurisdiction": "IL",
                "compliance_flags": [],
            }
        )
    )

    assert review["evidence_review"]["status"] == "conflicting"
    assert _check(review, "state_registration_status")["status"] == "conflicting"


def test_review_marks_potential_external_match_as_review_required_not_confirmed():
    review = build_review(
        _payload(
            external_signals={
                "sanctions": {
                    "sanctions_match": True,
                    "source": "ofac_mock",
                }
            }
        )
    )

    assert review["evidence_review"]["status"] == "review_required"
    assert _check(review, "sanctions_screening")["status"] == "potential_match"
    assert "not a confirmed adverse finding" in review["evidence_review"]["issues"][0]["message"]


def test_customer_requirements_are_named_versioned_and_neutral():
    review = build_review(_payload(), customer_policy_id="customer_policy_v1")
    evaluation = review["requirements_evaluation"]

    assert evaluation["policy_id"] == "customer_policy_v1"
    assert evaluation["policy_version"] == "1.0"
    assert evaluation["policy_owner"] == "customer"
    assert evaluation["result"] == "requirements_met"
    assert {item["result"] for item in evaluation["requirements"]} == {"met"}
    assert "final_recommendation" not in evaluation
    assert "approve" not in str(evaluation)


def test_customer_requirements_report_not_met_without_grant_denial():
    review = build_review(
        _payload(verification={"irs_status": "inactive", "recent_990_on_file": True, "tax_deductible": True}),
        customer_policy_id="customer_policy_v1",
    )

    assert review["requirements_evaluation"]["result"] == "requirements_not_met"
    assert any(item["result"] == "not_met" for item in review["requirements_evaluation"]["requirements"])
    assert review["customer_decision"] is None


def test_customer_requirements_report_unresolved_for_stale_evidence():
    review = build_review(
        _payload(
            verification={
                "irs_status": "active",
                "recent_990_on_file": False,
                "state": "IL",
                "tax_deductible": True,
            }
        ),
        customer_policy_id="customer_policy_v1",
    )

    assert review["requirements_evaluation"]["result"] == "unresolved"
    assert any(
        item["requirement_id"] == "recent_filing_indicator_available" and item["result"] == "unresolved"
        for item in review["requirements_evaluation"]["requirements"]
    )


def test_ensure_review_preserves_existing_compatible_review():
    payload = _payload()
    ensure_review(payload)
    first = payload["review"]

    ensure_review(payload, customer_policy_id="customer_policy_v1")

    assert payload["review"] is first
