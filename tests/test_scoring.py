from infrastructure.charity_status.scoring.calculator import SCORING_MODEL_VERSION, calculate_v1_scores
import pytest


def test_v2_scores_with_990_and_peer_benchmarking():
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
    peer_group = {"ntee": "P", "org_type": "03", "revenue_band": "1m_to_10m", "state": "IL"}
    peer_stats = {
        "count": 120,
        "metrics": {
            "programExpenseRatio": {"p25": 0.6, "median": 0.7, "p75": 0.78},
            "liabilitiesToAssetsRatio": {"p25": 0.35, "median": 0.5, "p75": 0.65},
            "operatingMargin": {"p25": 0.0, "median": 0.03, "p75": 0.08},
            "monthsOfRunway": {"p25": 4, "median": 6, "p75": 10},
        },
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
        peer_group=peer_group,
        peer_stats=peer_stats,
    )

    assert result.explanation["model_version"] == SCORING_MODEL_VERSION
    assert result.explanation["peer_benchmarking_used"] is True
    assert result.explanation["peer_group_size"] == 120
    assert "program_expense_ratio" in result.explanation["benchmarked_metrics"]


def test_v2_scores_fallback_no_990_or_peer():
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
    assert result.explanation["peer_benchmarking_used"] is False


def test_v2_scores_peer_group_too_small_fallback():
    verification = {
        "irs_status": "active",
        "tax_deductible": True,
        "ntee_category": "Education",
        "recent_990_on_file": True,
        "revoked": False,
    }
    result = calculate_v1_scores(
        record={"filing_req_cd": "1"},
        verification=verification,
        ein_valid=True,
        metrics_record={"programExpenseRatio": 0.7},
        peer_group={"ntee": "B", "org_type": "03", "revenue_band": "250k_to_1m", "state": None},
        peer_stats={"count": 5, "metrics": {"programExpenseRatio": {"p25": 0.5, "median": 0.6, "p75": 0.7}}},
    )

    assert result.explanation["peer_benchmarking_used"] is False


def test_v2_scores_hard_rule_ineligible_and_revoked_cap():
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


def test_weighting_default_profile_applied():
    verification = {"irs_status": "active", "tax_deductible": True, "ntee_category": "Education", "recent_990_on_file": True, "revoked": False}
    result = calculate_v1_scores(
        record={"filing_req_cd": "1"},
        verification=verification,
        ein_valid=True,
        metrics_record={"programExpenseRatio": 0.8},
    )
    wp = result.explanation["weighting_profile"]
    assert wp["applied"] == "default_v1"
    assert wp["fallback_applied"] is False


def test_weighting_compliance_heavy_profile_changes_aggregation():
    verification = {"irs_status": "active", "tax_deductible": True, "ntee_category": "Education", "recent_990_on_file": True, "revoked": False}
    base = calculate_v1_scores(
        record={"filing_req_cd": "1"},
        verification=verification,
        ein_valid=True,
        metrics_record={"programExpenseRatio": 0.8},
        governance_record={"public_disclosure_available": False},
        quality_record={"narrativeMissing": True},
        weighting_profile_id="default_v1",
    )
    heavy = calculate_v1_scores(
        record={"filing_req_cd": "1"},
        verification=verification,
        ein_valid=True,
        metrics_record={"programExpenseRatio": 0.8},
        governance_record={"public_disclosure_available": False},
        quality_record={"narrativeMissing": True},
        weighting_profile_id="compliance_heavy_v1",
    )
    assert heavy.explanation["weighting_profile"]["applied"] == "compliance_heavy_v1"
    assert heavy.scores["overall"] >= base.scores["overall"]


def test_weighting_transparency_light_profile():
    verification = {"irs_status": "active", "tax_deductible": True, "ntee_category": "Education", "recent_990_on_file": True, "revoked": False}
    light = calculate_v1_scores(
        record={"filing_req_cd": "1"},
        verification=verification,
        ein_valid=True,
        metrics_record={"programExpenseRatio": 0.8},
        governance_record={"public_disclosure_available": False},
        quality_record={"narrativeMissing": True},
        weighting_profile_id="transparency_light_v1",
    )
    assert light.explanation["weighting_profile"]["applied"] == "transparency_light_v1"
    assert light.explanation["weighting_profile"]["weights"]["transparency"] == 0.1


def test_weighting_invalid_profile_fallback_and_error():
    verification = {"irs_status": "active", "tax_deductible": True, "ntee_category": "Education", "recent_990_on_file": True, "revoked": False}
    fallback = calculate_v1_scores(
        record={"filing_req_cd": "1"},
        verification=verification,
        ein_valid=True,
        weighting_profile_id="unknown_profile",
    )
    assert fallback.explanation["weighting_profile"]["applied"] == "default_v1"
    assert fallback.explanation["weighting_profile"]["fallback_applied"] is True

    with pytest.raises(ValueError, match="Unknown weighting profile"):
        calculate_v1_scores(
            record={"filing_req_cd": "1"},
            verification=verification,
            ein_valid=True,
            weighting_profile_id="unknown_profile",
            fallback_invalid_weighting_profile=False,
        )
