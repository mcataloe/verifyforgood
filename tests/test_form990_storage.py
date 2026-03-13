from datetime import datetime, timezone

from infrastructure.charity_status.form990.storage import checkpoint_key, discovery_diff_key, discovery_manifest_key, filing_manifest_key, manifest_key, normalized_metadata_key, raw_xml_key, state_manifest_key


def test_storage_key_generation_is_stable():
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    assert normalized_metadata_key("form990/normalized/metadata/", now=ts) == "form990/normalized/metadata/metadata_20260102T030405Z.jsonl"
    assert manifest_key("form990/normalized/manifests/", now=ts) == "form990/normalized/manifests/manifest_20260102T030405Z.json"
    assert raw_xml_key("form990/raw/", "123456789", "2023", "abc123") == "form990/raw/123456789/2023/abc123.xml"
    assert discovery_manifest_key("form990/normalized/manifests/", "run1") == "form990/normalized/manifests/discovery/runs/run1/catalog.json"
    assert discovery_diff_key("form990/normalized/manifests/", "run1") == "form990/normalized/manifests/discovery/runs/run1/diff.json"
    assert filing_manifest_key("form990/normalized/manifests/", "run1", 3) == "form990/normalized/manifests/filings/run1/batch_00003.json"
    assert checkpoint_key("form990/normalized/manifests/") == "form990/normalized/manifests/checkpoint/latest.json"
    assert state_manifest_key("form990/normalized/manifests/") == "form990/normalized/manifests/state/latest_filing_manifest.json"
