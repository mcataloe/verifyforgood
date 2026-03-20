from __future__ import annotations

import json
from datetime import datetime, timezone

from infrastructure.charity_status.form990.teos_manifest import S3TeosZipManifestRepository
from infrastructure.charity_status.form990.teos_zip_discovery import TeosZipDiscoveryRecord


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        return {"Body": _Body(self.store[(Bucket, Key)]["Body"])}

    def list_objects_v2(self, Bucket, Prefix):
        return {"Contents": [{"Key": key} for (bucket, key), _value in self.store.items() if bucket == Bucket and key.startswith(Prefix)]}


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self):
        if isinstance(self._value, bytes):
            return self._value
        return str(self._value).encode("utf-8")


def _record(year: str, batch: str) -> TeosZipDiscoveryRecord:
    return TeosZipDiscoveryRecord(
        tax_year=year,
        source_url=f"https://apps.irs.gov/pub/epostcard/990/xml/{year}/{batch}.zip",
        source_filename=f"{batch}.zip",
        zip_basename=batch,
        discovered_at="2026-03-20T00:00:00+00:00",
        page_url="https://www.irs.gov/charities-non-profits/form-990-series-downloads",
    )


def test_teos_manifest_sync_persists_state_and_run_catalog():
    s3 = FakeS3()
    repository = S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="form990/raw/",
    )

    summary = repository.sync_discovered_records(
        run_id="run1",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        checked_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    assert summary.discovered_count == 1
    assert summary.new_count == 1
    assert summary.changed_count == 0
    assert summary.catalog_keys == ("form990/normalized/manifests/teos-zip/runs/run1/year=2025/catalog.json",)

    state_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_01A.json"
    state_payload = json.loads(s3.store[("test-bucket", state_key)]["Body"].decode("utf-8"))
    assert state_payload["current_sync_status"] == "discovered"
    assert state_payload["download_status"] == "pending"
    assert state_payload["destination_raw_s3_prefix"] == "form990/raw/year=2025/source_batch=2025_TEOS_XML_01A"


def test_teos_manifest_sync_marks_missing_records_not_listed():
    s3 = FakeS3()
    repository = S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="form990/raw/",
    )
    repository.sync_discovered_records(
        run_id="run1",
        discovered_sources=[
            _record("2025", "2025_TEOS_XML_01A"),
            _record("2025", "2025_TEOS_XML_02A"),
        ],
        checked_at="2026-03-20T00:00:00+00:00",
    )

    summary = repository.sync_discovered_records(
        run_id="run2",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        checked_at="2026-03-21T00:00:00+00:00",
    )

    assert summary.discovered_count == 1
    assert summary.removed_count == 1
    assert summary.unchanged_count == 1

    missing_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_02A.json"
    missing_payload = json.loads(s3.store[("test-bucket", missing_key)]["Body"].decode("utf-8"))
    assert missing_payload["current_sync_status"] == "not_listed"
    assert missing_payload["last_checked_at"] == "2026-03-21T00:00:00+00:00"
