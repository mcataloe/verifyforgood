from infrastructure.charity_status.scoring.calculator import calculate_v1_scores


def test_v1_scores_with_990_enrichment_data():
    record = {
        "filing_req_cd": "1",
    }
    verification = {
        "irs_status": "active",
        "tax_deductible": True,
        "ntee_category": "Human Services",
        "recent_990_on_file": True,
        "revoked": False,
    }
    metrics = {
        "programExpenseRatio": 0.8,
        "liabilitiesToAssetsRatio": 0.4,
        "monthsOfRunway": 8,
        "operatingMargin": 0.05,
    }
    governance = {
        "whistleblower_policy": True,
        "material_diversion_reported": False,
        "public_disclosure_available": True,
    }
    quality = {
        "narrativeMissing": False,
        "scoreConfidence": "high",
    }
    filing = {
        "mission_description_present": True,
        "program_accomplishments_present": True,
        "leadership_disclosed": True,
    }

    result = calculate_v1_scores(
        record=record,
        verification=verification,
        ein_valid=True,
        filing_record=filing,
        metrics_record=metrics,
        governance_record=governance,
        quality_record=quality,
        name_match=True,
    )

    assert result.explanation["model_version"] == "1.1.0"
    assert "irs_form_990_xml" in result.explanation["score_data_sources"]
    assert result.scores["financial_resilience"] is not None
    assert result.explanation["factors"]["program_expense_ratio"] == 0.8


def test_v1_scores_fallback_no_990():
    verification = {
        "irs_status": "active",
        "tax_deductible": True,
        "ntee_category": None,
        "recent_990_on_file": None,
        "revoked": False,
    }

    result = calculate_v1_scores(record={}, verification=verification, ein_valid=True)

    assert result.scores["financial_resilience"] is None
    assert result.explanation["score_data_sources"] == ["irs_eo_bmf_athena"]
    assert any("Form 990 enrichment unavailable" in note for note in result.explanation["notes"])


def test_v1_scores_hard_rule_ineligible_and_revoked_cap():
    verification = {
        "irs_status": "inactive",
        "tax_deductible": True,
        "ntee_category": "Education",
        "recent_990_on_file": True,
        "revoked": True,
    }

    result = calculate_v1_scores(record={"filing_req_cd": "1"}, verification=verification, ein_valid=True)

    assert result.explanation["eligibility"] == "INELIGIBLE"
    assert result.scores["overall"] <= 30
