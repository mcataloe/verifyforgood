from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from infrastructure.charity_status.form990.static_source_discovery import (
    STATIC_MANIFEST_PAGE_URL,
    _parse_manifest_text,
    discover_static_form990_sources,
)


def test_parse_manifest_text_extracts_mixed_artifacts_and_deduplicates():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    text = """
Index file for 2025 (CSV) https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv
https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11B.zip

noise that should be ignored
https://apps.irs.gov/pub/epostcard/990/xml/2020/download990xml_2020_1.zip
duplicate https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv
"""

    sources = _parse_manifest_text(text, now=now)

    assert [
        (item.source_year, item.source_kind, item.source_archive_key)
        for item in sources
    ] == [
        ("2020", "zip_archive", "download990xml_2020_1"),
        ("2025", "csv_index", "index_2025"),
        ("2025", "zip_archive", "2025_teos_xml_11b"),
    ]
    assert all(item.discovered_at == "2026-01-01T00:00:00+00:00" for item in sources)


def test_discover_static_form990_sources_uses_stable_manifest_identity(tmp_path: Path):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manifest_path = tmp_path / "Form990Links.txt"
    manifest_path.write_text(
        "\n".join(
            [
                "Index file for 2024 (CSV) https://apps.irs.gov/pub/epostcard/990/xml/2024/index_2024.csv",
                "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11A.zip",
            ]
        ),
        encoding="utf-8",
    )

    first = discover_static_form990_sources(now=now, manifest_path=manifest_path)
    second = discover_static_form990_sources(now=now, manifest_path=manifest_path)

    assert len(first) == 2
    assert [item.source_archive_key for item in first] == ["index_2024", "2024_teos_xml_11a"]
    assert all(item.page_url == STATIC_MANIFEST_PAGE_URL for item in first)
    assert [item.source_signature for item in first] == [item.source_signature for item in second]


def test_discover_static_form990_sources_loads_packaged_manifest():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    sources = discover_static_form990_sources(now=now)
    identities = {(item.source_year, item.source_kind, item.source_archive_key) for item in sources}

    assert ("2025", "csv_index", "index_2025") in identities
    assert ("2025", "zip_archive", "2025_teos_xml_11b") in identities
    assert ("2020", "zip_archive", "download990xml_2020_1") in identities
