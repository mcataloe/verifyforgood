from __future__ import annotations

from infrastructure.charity_status.form990.discovery import discover_archives, fetch_index_records
from infrastructure.charity_status.form990.manifest import diff_manifest_entries
from infrastructure.charity_status.form990.source_catalog import normalize_configured_sources
from infrastructure.charity_status.form990.models import Form990IndexRecord


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_discovery_inventory_and_old_naming_compatibility():
    catalog = [
        {"index_url": "https://apps.irs.gov/pub/epostcard/data-download-xml-2024.json"},
        {"index_url": "https://apps.irs.gov/pub/epostcard/2019-xml-index.csv", "archive_name": "2019_xml_index"},
    ]
    discovered = discover_archives(catalog, mode="bootstrap", now_year=2026)
    assert len(discovered) == 2
    assert discovered[0].source_year == "2019"
    assert discovered[1].source_year == "2024"


def test_index_csv_row_parsing(monkeypatch):
    csv_payload = b"EIN,TaxYr,FilingDt,ReturnType,ObjectId,URL\n530196605,2023,2024-05-15,990,obj-1,https://example.org/obj-1.xml\n"
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=60: _FakeResponse(csv_payload),
    )
    records = fetch_index_records(
        index_url="https://apps.irs.gov/pub/epostcard/2023-index.csv",
        source_year="2023",
        source_archive="2023-index.csv",
    )
    assert len(records) == 1
    assert records[0].ein == "530196605"
    assert records[0].source_year == "2023"
    assert records[0].source_signature is not None


def test_index_csv_positional_row_parsing(monkeypatch):
    csv_payload = b".EFILE,852780739,202312,2024,MISSION FLIGHT ACADEMY,990EZ,93492348002084,202433489349200208,2024_TEOS_XML_12A\n"
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=60: _FakeResponse(csv_payload),
    )
    records = fetch_index_records(
        index_url="https://apps.irs.gov/pub/epostcard/990/xml/2024/index_2024.csv",
        source_year="2024",
        source_archive="index_2024.csv",
    )
    assert len(records) == 1
    assert records[0].ein == "852780739"
    assert records[0].tax_year == "2024"
    assert records[0].return_type == "990EZ"
    assert records[0].irs_object_id == "202433489349200208"
    assert records[0].xml_url.endswith("202433489349200208_public.xml")


def test_manifest_diff_behavior():
    current = [
        Form990IndexRecord(
            ein="1",
            tax_year="2023",
            filing_date="2024-01-01",
            return_type="990",
            irs_object_id="a",
            xml_url="u1",
            source_signature="sig-a-v2",
        ),
        Form990IndexRecord(
            ein="2",
            tax_year="2023",
            filing_date="2024-01-02",
            return_type="990",
            irs_object_id="b",
            xml_url="u2",
            source_signature="sig-b-v1",
        ),
    ]
    previous_entries = [
        {"irs_object_id": "a", "source_signature": "sig-a-v1"},
        {"irs_object_id": "c", "source_signature": "sig-c-v1"},
    ]
    new_records, changed_records, unchanged = diff_manifest_entries(current, previous_entries)
    assert len(new_records) == 1
    assert new_records[0].irs_object_id == "b"
    assert len(changed_records) == 1
    assert changed_records[0].irs_object_id == "a"
    assert unchanged == 0


def test_configured_source_catalog_backward_compatibility():
    sources = normalize_configured_sources(
        [
            {"year": "2024", "index_url": "https://example.org/index_2024.csv"},
            {"source_year": "2024", "zip_url": "https://example.org/2024_TEOS_XML_11B.zip", "archive_name": "2024_teos_xml_11b"},
        ]
    )
    assert len(sources) == 2
    assert sources[0].source_year == "2024"
    assert {item.source_kind for item in sources} == {"csv_index", "zip_archive"}
