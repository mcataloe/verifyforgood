from datetime import datetime, timezone

from infrastructure.charity_status.form990.storage import manifest_key, normalized_metadata_key, raw_xml_key


def test_storage_key_generation_is_stable():
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    assert normalized_metadata_key("form990/normalized/metadata/", now=ts) == "form990/normalized/metadata/metadata_20260102T030405Z.jsonl"
    assert manifest_key("form990/normalized/manifests/", now=ts) == "form990/normalized/manifests/manifest_20260102T030405Z.json"
    assert raw_xml_key("form990/raw/", "123456789", "2023", "abc123") == "form990/raw/123456789/2023/abc123.xml"
