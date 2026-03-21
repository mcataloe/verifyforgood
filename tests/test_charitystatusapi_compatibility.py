import importlib
import warnings

from charity_status.query.nonprofit_lookup import map_nonprofit_record
from verification_platform.organization_verification.organization_lookup import map_organization_record


def test_lowercase_legacy_namespace_imports_and_warns():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        module = importlib.import_module("charitystatusapi")

    assert module.NonprofitResponse is not None
    assert any(item.category is DeprecationWarning for item in captured)


def test_camelcase_legacy_namespace_imports_and_warns():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        module = importlib.import_module("CharityStatusAPI")

    assert module.NonprofitResponse is not None
    assert any(item.category is DeprecationWarning for item in captured)


def test_legacy_namespace_query_module_resolves_without_changes():
    legacy_lookup = importlib.import_module("charitystatusapi.query.nonprofit_lookup")
    legacy_upper_lookup = importlib.import_module("CharityStatusAPI.query.nonprofit_lookup")

    assert legacy_lookup.map_nonprofit_record is map_nonprofit_record
    assert legacy_upper_lookup.map_nonprofit_record is map_nonprofit_record


def test_legacy_namespace_output_matches_neutral_namespace():
    row = {
        "name": "Compat Org",
        "state": "IL",
        "status": "1",
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "asset_amt": "",
        "income_amt": "",
        "revenue_amt": "",
    }

    legacy_payload = importlib.import_module("charitystatusapi.query.nonprofit_lookup").map_nonprofit_record("123456789", row).to_dict()
    neutral_payload = map_organization_record("123456789", row).to_dict()

    assert legacy_payload == neutral_payload
