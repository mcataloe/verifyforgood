from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from infrastructure.verification.form990.source_catalog import diff_source_catalog, select_sources_by_years
from infrastructure.verification.form990.static_source_discovery import (
    GENERATED_NEXT_YEAR_PAGE_URL,
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

    first = discover_static_form990_sources(
        now=now,
        manifest_path=manifest_path,
        enable_next_year_generation=False,
    )
    second = discover_static_form990_sources(
        now=now,
        manifest_path=manifest_path,
        enable_next_year_generation=False,
    )

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
    assert ("2026", "csv_index", "index_2026") in identities
    assert ("2026", "zip_archive", "2026_teos_xml_11d") in identities
    assert ("2020", "zip_archive", "download990xml_2020_1") in identities


def test_discover_static_form990_sources_generates_single_next_year_from_latest_teos_pattern(tmp_path: Path):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manifest_path = tmp_path / "Form990Links.txt"
    manifest_path.write_text(
        "\n".join(
            [
                "Index file for 2025 (CSV) https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_02A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_03A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_04A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_05A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_06A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_07A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_08A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_09A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_10A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11B.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11C.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11D.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_12A.zip",
                "https://apps.irs.gov/pub/epostcard/990/xml/2020/download990xml_2020_1.zip",
            ]
        ),
        encoding="utf-8",
    )

    sources = discover_static_form990_sources(now=now, manifest_path=manifest_path)
    generated = [item for item in sources if item.source_year == "2026"]

    assert len(generated) == 16
    assert {item.source_kind for item in generated} == {"csv_index", "zip_archive"}
    assert {item.page_url for item in generated} == {f"{GENERATED_NEXT_YEAR_PAGE_URL}/2025-to-2026"}
    assert ("2026", "csv_index", "index_2026") in {
        (item.source_year, item.source_kind, item.source_archive_key) for item in generated
    }
    assert ("2026", "zip_archive", "2026_teos_xml_11d") in {
        (item.source_year, item.source_kind, item.source_archive_key) for item in generated
    }
    assert all(item.source_year != "2027" for item in sources)


def test_discover_static_form990_sources_can_disable_next_year_generation(tmp_path: Path):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manifest_path = tmp_path / "Form990Links.txt"
    manifest_path.write_text(
        "\n".join(
            [
                "Index file for 2025 (CSV) https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11A.zip",
            ]
        ),
        encoding="utf-8",
    )

    sources = discover_static_form990_sources(
        now=now,
        manifest_path=manifest_path,
        enable_next_year_generation=False,
    )

    assert [item.source_year for item in sources] == ["2025", "2025"]
    assert all(item.page_url == STATIC_MANIFEST_PAGE_URL for item in sources)


def test_discover_static_form990_sources_rejects_malformed_manifest(tmp_path: Path):
    manifest_path = tmp_path / "Form990Links.txt"
    manifest_path.write_text("this file does not contain any supported source urls", encoding="utf-8")

    try:
        discover_static_form990_sources(manifest_path=manifest_path)
    except ValueError as exc:
        assert "did not contain any parseable CSV or ZIP source URLs" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected malformed manifest to raise ValueError")


def test_generated_sources_flow_through_selection_and_diff(tmp_path: Path):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manifest_path = tmp_path / "Form990Links.txt"
    manifest_path.write_text(
        "\n".join(
            [
                "Index file for 2025 (CSV) https://apps.irs.gov/pub/epostcard/990/xml/2025/index_2025.csv",
                "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11A.zip",
            ]
        ),
        encoding="utf-8",
    )

    explicit_only = discover_static_form990_sources(
        now=now,
        manifest_path=manifest_path,
        enable_next_year_generation=False,
    )
    with_generated = discover_static_form990_sources(now=now, manifest_path=manifest_path)

    selected_2026 = select_sources_by_years(with_generated, {"2026"})
    diff = diff_source_catalog(with_generated, [item.to_dict() for item in explicit_only]).to_dict()

    assert len(selected_2026) == 2
    assert all(item.source_year == "2026" for item in selected_2026)
    assert len(diff["new_sources"]) == 2
    assert diff["removed_sources"] == []
    assert diff["changed_sources"] == []

