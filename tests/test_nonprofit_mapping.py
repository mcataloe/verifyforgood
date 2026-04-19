from infrastructure.verification.query.nonprofit_lookup import map_nonprofit_record


def test_map_nonprofit_record_normalized_shape():
    row = {
        "name": "Example Foundation",
        "state": "TX",
        "status": "1",
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "B20",
        "tax_period": "202412",
        "asset_amt": "",
        "income_amt": None,
        "revenue_amt": "10000",
    }

    payload = map_nonprofit_record("123456789", row).to_dict()

    assert payload["organization"]["ein"] == "12-3456789"
    assert payload["verification"]["irs_status"] == "active"
    assert payload["verification"]["tax_deductible"] is True
    assert payload["verification"]["entity_type"] == "Charitable Organization"
    assert payload["verification"]["ntee_category"] == "Education"
    assert payload["model"]["version"] == "1.0.0"
    assert payload["source_record"]["tax_period"] == "202412"


def test_map_nonprofit_record_unknown_codes_fallback():
    row = {
        "name": "Unknown Org",
        "status": "",
        "deductibility": "9",
        "subsection": "77",
        "ntee_cd": "Q99",
        "tax_period": "bad",
    }

    payload = map_nonprofit_record("123456789", row).to_dict()

    assert payload["verification"]["irs_status"] == "unknown"
    assert payload["verification"]["tax_deductible"] is None
    assert payload["verification"]["entity_type"] == "77"
    assert payload["verification"]["ntee_category"] == "International and Foreign Affairs"
    assert payload["verification"]["recent_990_on_file"] is None


def test_map_nonprofit_record_accepts_padded_numeric_status_codes():
    row = {
        "name": "Padded Status Org",
        "state": "DC",
        "status": "01",
        "deductibility": "01",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202412",
    }

    payload = map_nonprofit_record("123456789", row).to_dict()

    assert payload["verification"]["irs_status"] == "active"
    assert payload["verification"]["tax_deductible"] is True

