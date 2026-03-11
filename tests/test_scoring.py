from infrastructure.charity_status.scoring.calculator import calculate_v1_scores


def test_v1_scores_with_partial_data():
    record = {
        "asset_amt": None,
        "income_amt": None,
        "revenue_amt": "",
    }
    verification = {
        "irs_status": "active",
        "tax_deductible": True,
        "ntee_category": None,
        "recent_990_on_file": True,
    }

    result = calculate_v1_scores(record=record, verification=verification, ein_valid=True, name_match=True)

    assert result.scores["compliance"] >= 80
    assert result.scores["financial_resilience"] is None
    assert result.explanation["confidence"] in {"medium", "high"}
    assert result.explanation["factors"]["financial_fields_present"] is False
    assert result.explanation["factors"]["name_match"] is True
    assert result.explanation["model_version"] == "1.0.0"


def test_v1_scores_without_record():
    verification = {
        "irs_status": "unknown",
        "tax_deductible": None,
        "ntee_category": None,
        "recent_990_on_file": None,
    }

    result = calculate_v1_scores(record=None, verification=verification, ein_valid=True)

    assert result.scores["overall"] <= 50
    assert result.scores["transparency"] is None
    assert result.explanation["factors"]["record_found"] is False
