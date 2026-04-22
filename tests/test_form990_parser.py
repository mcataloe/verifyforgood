import pathlib

from infrastructure.verification.backend.ingest.federal.form990.extractors.metadata import extract_metadata_fields
from infrastructure.verification.backend.ingest.federal.form990.parser import XmlParseError, parse_xml


def test_extract_metadata_from_sample_xml():
    content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    parsed = parse_xml(content)
    metadata = extract_metadata_fields(parsed)

    assert metadata["ein"] == "123456789"
    assert metadata["tax_year"] == "2023"
    assert metadata["tax_period_begin"] == "2023-01-01"
    assert metadata["tax_period_end"] == "2023-12-31"
    assert metadata["filing_date"] == "2024-05-15"
    assert metadata["amended_return"] is False
    assert metadata["return_type"] == "990"


def test_parse_malformed_xml_raises():
    content = pathlib.Path("tests/fixtures/form990/form990_malformed.xml").read_bytes()

    try:
        parse_xml(content)
        assert False, "expected parse failure"
    except XmlParseError:
        assert True


def test_missing_fields_resolve_to_none():
    content = b"<Return xmlns='http://www.irs.gov/efile'><Filer><EIN>111111111</EIN></Filer></Return>"
    metadata = extract_metadata_fields(parse_xml(content))

    assert metadata["ein"] == "111111111"
    assert metadata["tax_year"] is None
    assert metadata["amended_return"] is None
    assert metadata["return_type"] is None

