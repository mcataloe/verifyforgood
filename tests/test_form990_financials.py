import pathlib

from infrastructure.charity_status.form990.extractors.financials import extract_financial_fields
from infrastructure.charity_status.form990.parser import parse_xml


def test_extract_financial_fields_from_sample_xml():
    parsed = parse_xml(pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes())
    values = extract_financial_fields(parsed)

    assert values["total_revenue"] == 1000000.0
    assert values["total_expenses"] == 800000.0
    assert values["program_service_expenses"] == 600000.0
    assert values["management_general_expenses"] == 100000.0
    assert values["fundraising_expenses"] == 50000.0
    assert values["contributions_revenue"] == 700000.0
    assert values["total_assets_eoy"] == 2000000.0
    assert values["total_liabilities_eoy"] == 500000.0
    assert values["net_assets_eoy"] == 1500000.0
    assert values["grants_paid"] == 250000.0
    assert values["officer_compensation"] == 120000.0


def test_extract_financial_fields_handles_partial_document():
    parsed = parse_xml(b"<Return xmlns='http://www.irs.gov/efile'><ReturnData/></Return>")
    values = extract_financial_fields(parsed)

    assert all(value is None for value in values.values())
