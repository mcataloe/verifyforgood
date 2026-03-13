from __future__ import annotations

from datetime import datetime, timezone

from infrastructure.charity_status.form990.irs_page_discovery import (
    IrsYearSource,
    diff_source_catalog,
    discover_irs_form990_sources,
    discovery_state_changed,
    sources_to_catalog,
)


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200, headers: dict[str, str] | None = None):
        self._body = body
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_discover_irs_page_sources_extracts_csv_and_zip_patterns(monkeypatch):
    html = b"""
<html><body>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv">2025 Index</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11B.zip">2025 11B ZIP</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11C.zip">2025 11C ZIP</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2020/2020_TEOS_XML_CT1.zip">2020 CT1 ZIP</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2020/download990xml_2020_1.zip">2020 Legacy ZIP</a>
</body></html>
"""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=60: _FakeResponse(html, headers={"ETag": "abc", "Last-Modified": "Thu, 01 Jan 2026 00:00:00 GMT"}),
    )
    sources = discover_irs_form990_sources(
        "https://www.irs.gov/charities-non-profits/form-990-series-downloads",
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert len(sources) == 5
    names = {(item.source_year, item.source_kind, item.source_archive_key) for item in sources}
    assert ("2025", "csv_index", "index_2025") in names
    assert ("2025", "zip_archive", "2025_teos_xml_11b") in names
    assert ("2025", "zip_archive", "2025_teos_xml_11c") in names
    assert ("2020", "zip_archive", "2020_teos_xml_ct1") in names
    assert ("2020", "zip_archive", "download990xml_2020_1") in names
    assert all(item.source_signature for item in sources)


def test_sources_to_catalog_shape():
    source = IrsYearSource(
        source_year="2024",
        source_kind="zip_archive",
        source_url="https://example.org/2024_TEOS_XML_11B.zip",
        source_filename="2024_TEOS_XML_11B.zip",
        source_archive_key="2024_teos_xml_11b",
        discovered_at="2026-01-01T00:00:00+00:00",
        source_signature="sig",
        page_url="https://www.irs.gov/charities-non-profits/form-990-series-downloads",
    )
    catalog = sources_to_catalog([source])
    assert catalog[0]["source_year"] == "2024"
    assert catalog[0]["source_kind"] == "zip_archive"
    assert catalog[0]["archive_name"] == "2024_teos_xml_11b"
    assert catalog[0]["zip_url"] == "https://example.org/2024_TEOS_XML_11B.zip"


def test_discovery_state_diff_detection():
    current = [
        IrsYearSource(
            source_year="2024",
            source_kind="csv_index",
            source_url="https://example.org/index_2024.csv",
            source_filename="index_2024.csv",
            source_archive_key="index_2024",
            discovered_at="2026-01-01T00:00:00+00:00",
            source_signature="sig-1",
            page_url="https://example.org/page",
        )
    ]
    previous_same = [
        {
            "source_year": "2024",
            "source_kind": "csv_index",
            "source_url": "https://example.org/index_2024.csv",
            "source_filename": "index_2024.csv",
            "source_archive_key": "index_2024",
            "source_signature": "sig-1",
            "page_url": "https://example.org/page",
        }
    ]
    previous_changed = [
        {
            "source_year": "2024",
            "source_kind": "csv_index",
            "source_url": "https://example.org/index_2024_v2.csv",
            "source_filename": "index_2024.csv",
            "source_archive_key": "index_2024",
            "source_signature": "sig-2",
            "page_url": "https://example.org/page",
        }
    ]
    previous_removed = previous_same + [
        {
            "source_year": "2024",
            "source_kind": "zip_archive",
            "source_url": "https://example.org/2024_TEOS_XML_11B.zip",
            "source_filename": "2024_TEOS_XML_11B.zip",
            "source_archive_key": "2024_teos_xml_11b",
            "source_signature": "sig-zip",
            "page_url": "https://example.org/page",
        }
    ]

    same_diff = diff_source_catalog(current, previous_same).to_dict()
    changed_diff = diff_source_catalog(current, previous_changed).to_dict()
    removed_diff = diff_source_catalog(current, previous_removed).to_dict()

    assert same_diff["new_sources"] == []
    assert same_diff["changed_sources"] == []
    assert same_diff["removed_sources"] == []
    assert same_diff["unchanged_sources"] == 1
    assert len(changed_diff["changed_sources"]) == 1
    assert len(removed_diff["removed_sources"]) == 1
    assert discovery_state_changed(current, previous_same) is False
    assert discovery_state_changed(current, previous_changed) is True


def test_discover_irs_page_sources_extracts_multiple_archives_same_year(monkeypatch):
    html = b"""
<html><body>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11B.zip">2024 11B ZIP</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11C.zip">2024 11C ZIP</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11D.zip">2024 11D ZIP</a>
</body></html>
"""
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=60: _FakeResponse(html))
    sources = discover_irs_form990_sources("https://www.irs.gov/charities-non-profits/form-990-series-downloads")
    assert len(sources) == 3
    names = {item.source_archive_key for item in sources}
    assert "2024_teos_xml_11b" in names
    assert "2024_teos_xml_11c" in names
    assert "2024_teos_xml_11d" in names
