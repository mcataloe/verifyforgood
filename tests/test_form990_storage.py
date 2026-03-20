from datetime import datetime, timezone

from infrastructure.charity_status.form990.storage import (
    checkpoint_key,
    discovery_diff_key,
    discovery_manifest_key,
    filing_catalog_key,
    filing_diff_key,
    filing_manifest_key,
    manifest_key,
    normalized_metadata_key,
    raw_source_key,
    raw_xml_key,
    teos_raw_xml_member_key,
    teos_raw_xml_source_batch_prefix,
    teos_zip_manifest_run_catalog_key,
    teos_zip_manifest_state_key,
    teos_zip_manifest_state_prefix,
    source_download_manifest_key,
    source_download_state_entry_key,
    source_download_state_prefix,
    state_manifest_key,
)


def test_storage_key_generation_is_stable():
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    assert normalized_metadata_key("form990/normalized/metadata/", now=ts) == "form990/normalized/metadata/metadata_20260102T030405Z.jsonl"
    assert manifest_key("form990/normalized/manifests/", now=ts) == "form990/normalized/manifests/manifest_20260102T030405Z.json"
    assert raw_xml_key("form990/raw/", "123456789", "2023", "abc123") == "form990/raw/123456789/2023/abc123.xml"
    assert raw_xml_key("form990/raw/", "123456789", "2025", "abc123", source_batch="2025_TEOS_XML_01A") == "form990/raw/year=2025/source_batch=2025_TEOS_XML_01A/ein=123456789/abc123.xml"
    assert raw_source_key("form990/raw-sources/", "2024", "zip_archive", "2024_teos_xml_11b", "sig-1", "2024_TEOS_XML_11B.zip") == "form990/raw-sources/2024/zip_archive/2024_teos_xml_11b/sig-1/2024_TEOS_XML_11B.zip"
    assert discovery_manifest_key("form990/normalized/manifests/", "run1") == "form990/normalized/manifests/discovery/runs/run1/catalog.json"
    assert discovery_diff_key("form990/normalized/manifests/", "run1") == "form990/normalized/manifests/discovery/runs/run1/diff.json"
    assert source_download_manifest_key("form990/normalized/manifests/", "run1", 3) == "form990/normalized/manifests/source-download/runs/run1/batch_00003.json"
    assert source_download_state_prefix("form990/normalized/manifests/") == "form990/normalized/manifests/source-download/state/latest"
    assert source_download_state_entry_key("form990/normalized/manifests/", "2024", "csv_index", "index_2024") == "form990/normalized/manifests/source-download/state/latest/2024/csv_index/index_2024.json"
    assert teos_zip_manifest_state_prefix("form990/normalized/manifests/") == "form990/normalized/manifests/teos-zip/state/latest"
    assert teos_zip_manifest_state_key("form990/normalized/manifests/", "2025", "2025_TEOS_XML_01A") == "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_01A.json"
    assert teos_zip_manifest_run_catalog_key("form990/normalized/manifests/", "run1", "2025") == "form990/normalized/manifests/teos-zip/runs/run1/year=2025/catalog.json"
    assert teos_raw_xml_source_batch_prefix("form990/raw/", "2025", "2025_TEOS_XML_01A") == "form990/raw/year=2025/source_batch=2025_TEOS_XML_01A"
    assert teos_raw_xml_member_key("teos/raw/xml/", "2025", "2025_TEOS_XML_01A", "nested/202500123_public.xml") == "teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_01A/nested_202500123_public.xml"
    assert filing_catalog_key("form990/normalized/manifests/", "run1") == "form990/normalized/manifests/filings/run1/catalog.json"
    assert filing_diff_key("form990/normalized/manifests/", "run1") == "form990/normalized/manifests/filings/run1/diff.json"
    assert filing_manifest_key("form990/normalized/manifests/", "run1", 3) == "form990/normalized/manifests/filings/run1/batch_00003.json"
    assert checkpoint_key("form990/normalized/manifests/") == "form990/normalized/manifests/checkpoint/latest.json"
    assert state_manifest_key("form990/normalized/manifests/") == "form990/normalized/manifests/state/latest_filing_manifest.json"
