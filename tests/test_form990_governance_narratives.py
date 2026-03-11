import pathlib

from infrastructure.charity_status.form990.extractors.governance import extract_governance_fields
from infrastructure.charity_status.form990.extractors.narratives import extract_narrative_fields
from infrastructure.charity_status.form990.parser import parse_xml


def test_extract_governance_fields_from_sample_xml():
    parsed = parse_xml(pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes())
    values = extract_governance_fields(parsed)

    assert values["independent_board_majority"] is True
    assert values["conflict_of_interest_policy"] is True
    assert values["whistleblower_policy"] is False
    assert values["records_retention_policy"] is True
    assert values["contemporaneous_board_minutes"] is True
    assert values["material_diversion_reported"] is False
    assert values["compensation_review_process"] is True
    assert values["public_disclosure_available"] is True
    assert values["audited_financials_indicator"] is True


def test_extract_narrative_fields_from_sample_xml():
    parsed = parse_xml(pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes())
    values = extract_narrative_fields(parsed)

    assert values["mission_description_present"] is True
    assert values["program_accomplishments_present"] is True
    assert values["leadership_disclosed"] is True
    assert values["narrative_sections_missing"] == []


def test_extract_narrative_fields_missing_sections():
    parsed = parse_xml(b"<Return xmlns='http://www.irs.gov/efile'><ReturnData/></Return>")
    values = extract_narrative_fields(parsed)

    assert values["mission_description_present"] is False
    assert values["program_accomplishments_present"] is False
    assert values["leadership_disclosed"] is False
    assert len(values["narrative_sections_missing"]) == 3
