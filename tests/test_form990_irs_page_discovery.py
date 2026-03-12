from __future__ import annotations

from datetime import datetime, timezone

from infrastructure.charity_status.form990.irs_page_discovery import (
    IrsYearSource,
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


def test_discover_irs_page_sources_extracts_zip_and_index(monkeypatch):
    html = b"""
<html><body>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2024/download990xml_2024.zip">2024 ZIP</a>
<a href="https://apps.irs.gov/pub/epostcard/990/xml/2024/index_2024.csv">2024 Index</a>
<a href="/pub/epostcard/990/xml/2023/download990xml_2023.zip">2023 ZIP</a>
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
    assert len(sources) == 2
    by_year = {item.year: item for item in sources}
    assert by_year["2024"].zip_url is not None
    assert by_year["2024"].index_url is not None
    assert by_year["2023"].zip_url is not None
    assert by_year["2023"].source_signature


def test_sources_to_catalog_shape():
    source = IrsYearSource(
        year="2024",
        zip_url="https://example.org/2024.zip",
        index_url="https://example.org/2024.csv",
        source_page_url="https://www.irs.gov/charities-non-profits/form-990-series-downloads",
        discovered_at="2026-01-01T00:00:00+00:00",
        source_signature="sig",
    )
    catalog = sources_to_catalog([source])
    assert catalog[0]["year"] == "2024"
    assert catalog[0]["zip_url"] == "https://example.org/2024.zip"
    assert catalog[0]["index_url"] == "https://example.org/2024.csv"


def test_discovery_state_changed_detection():
    current = [
        IrsYearSource(
            year="2024",
            zip_url="https://example.org/2024.zip",
            index_url="https://example.org/2024.csv",
            source_page_url="https://example.org/page",
            discovered_at="2026-01-01T00:00:00+00:00",
            source_signature="sig-1",
        )
    ]
    previous_same = [{"year": "2024", "zip_url": "https://example.org/2024.zip", "index_url": "https://example.org/2024.csv", "source_signature": "sig-1"}]
    previous_changed = [{"year": "2024", "zip_url": "https://example.org/2024-v2.zip", "index_url": "https://example.org/2024.csv", "source_signature": "sig-2"}]
    assert discovery_state_changed(current, previous_same) is False
    assert discovery_state_changed(current, previous_changed) is True
