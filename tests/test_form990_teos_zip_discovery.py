from __future__ import annotations

from datetime import datetime, timezone

from infrastructure.verification.backend.ingest.federal.form990.teos_zip_discovery import discover_teos_zip_links, parse_teos_zip_links


def test_parse_teos_zip_links_filters_to_target_year_and_normalizes_absolute_urls():
    html = """
<html><body>
  <a href="/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip">2025 01A</a>
  <a href="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_02A.zip">2025 02A</a>
  <a href="https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11B.zip">2024 11B</a>
  <a href="https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv">2025 index</a>
  <a href="/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip">duplicate</a>
</body></html>
"""
    records = parse_teos_zip_links(
        html,
        page_url="https://www.irs.gov/charities-non-profits/form-990-series-downloads",
        target_year="2025",
        now=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    assert [(item.tax_year, item.zip_basename) for item in records] == [
        ("2025", "2025_TEOS_XML_01A"),
        ("2025", "2025_TEOS_XML_02A"),
    ]
    assert records[0].source_url == "https://www.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip"
    assert all(item.discovered_at == "2026-03-20T00:00:00+00:00" for item in records)


def test_discover_teos_zip_links_uses_injected_fetcher():
    fetched = {}

    def _fetcher(page_url: str, timeout_seconds: int) -> str:
        fetched["page_url"] = page_url
        fetched["timeout_seconds"] = timeout_seconds
        return """
<html><body>
  <a href="https://apps.irs.gov/pub/epostcard/990/xml/2026/2026_TEOS_XML_03A.zip">2026 03A</a>
</body></html>
"""

    records = discover_teos_zip_links(
        "https://www.irs.gov/charities-non-profits/form-990-series-downloads",
        target_year="2026",
        timeout_seconds=15,
        now=datetime(2026, 3, 20, tzinfo=timezone.utc),
        fetcher=_fetcher,
    )

    assert fetched == {
        "page_url": "https://www.irs.gov/charities-non-profits/form-990-series-downloads",
        "timeout_seconds": 15,
    }
    assert len(records) == 1
    assert records[0].zip_basename == "2026_TEOS_XML_03A"


def test_parse_teos_zip_links_rejects_invalid_target_year():
    try:
        parse_teos_zip_links("<html></html>", page_url="https://example.org", target_year="26")
    except ValueError as exc:
        assert "target_year must be a four-digit year" in str(exc)
    else:
        raise AssertionError("expected invalid target year to raise ValueError")

