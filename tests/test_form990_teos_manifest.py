from __future__ import annotations

import json
from datetime import datetime, timezone

from infrastructure.charity_status.form990.teos_manifest import S3TeosZipManifestRepository
from infrastructure.charity_status.form990.teos_zip_discovery import TeosZipDiscoveryRecord
from infrastructure.charity_status.form990.teos_zip_probe import TeosZipProbeFailure, TeosZipProbeResult


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
        raw_xml_prefix="teos/raw/xml/",
    )

    summary = repository.sync_discovered_records(
        run_id="run1",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        probe_results={
            ("2025", "2025_TEOS_XML_01A"): TeosZipProbeResult(
                source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                etag='"etag-1"',
                last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
                content_length=1234,
                checked_at="2026-03-20T00:00:00+00:00",
                method_used="HEAD",
            )
        },
        checked_at=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    assert summary.discovered_count == 1
    assert summary.new_count == 1
    assert summary.changed_count == 0
    assert summary.scheduled_download_count == 1
    assert summary.catalog_keys == ("form990/normalized/manifests/teos-zip/runs/run1/year=2025/catalog.json",)

    state_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_01A.json"
    state_payload = json.loads(s3.store[("test-bucket", state_key)]["Body"].decode("utf-8"))
    assert state_payload["current_sync_status"] == "discovered"
    assert state_payload["download_status"] == "scheduled"
    assert state_payload["etag"] == '"etag-1"'
    assert state_payload["destination_raw_s3_prefix"] == "teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_01A"


def test_teos_manifest_sync_marks_missing_records_not_listed():
    s3 = FakeS3()
    repository = S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="teos/raw/xml/",
    )
    repository.sync_discovered_records(
        run_id="run1",
        discovered_sources=[
            _record("2025", "2025_TEOS_XML_01A"),
            _record("2025", "2025_TEOS_XML_02A"),
        ],
        probe_results={
            ("2025", "2025_TEOS_XML_01A"): TeosZipProbeResult(
                source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                etag='"etag-1"',
                last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
                content_length=1234,
                checked_at="2026-03-20T00:00:00+00:00",
                method_used="HEAD",
            ),
            ("2025", "2025_TEOS_XML_02A"): TeosZipProbeResult(
                source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_02A.zip",
                resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_02A.zip",
                etag='"etag-2"',
                last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
                content_length=5678,
                checked_at="2026-03-20T00:00:00+00:00",
                method_used="HEAD",
            ),
        },
        checked_at="2026-03-20T00:00:00+00:00",
    )

    summary = repository.sync_discovered_records(
        run_id="run2",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        probe_results={
            ("2025", "2025_TEOS_XML_01A"): TeosZipProbeResult(
                source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                etag='"etag-1"',
                last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
                content_length=1234,
                checked_at="2026-03-21T00:00:00+00:00",
                method_used="HEAD",
            )
        },
        checked_at="2026-03-21T00:00:00+00:00",
    )

    assert summary.discovered_count == 1
    assert summary.removed_count == 1
    assert summary.unchanged_count == 1

    missing_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_02A.json"
    missing_payload = json.loads(s3.store[("test-bucket", missing_key)]["Body"].decode("utf-8"))
    assert missing_payload["current_sync_status"] == "not_listed"
    assert missing_payload["last_checked_at"] == "2026-03-21T00:00:00+00:00"


def test_teos_manifest_sync_marks_unchanged_zip_as_skipped_unchanged():
    s3 = FakeS3()
    repository = S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="teos/raw/xml/",
    )
    initial_probe = TeosZipProbeResult(
        source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
        resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
        etag='"etag-1"',
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
        checked_at="2026-03-20T00:00:00+00:00",
        method_used="HEAD",
    )

    repository.sync_discovered_records(
        run_id="run1",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        probe_results={("2025", "2025_TEOS_XML_01A"): initial_probe},
        checked_at="2026-03-20T00:00:00+00:00",
    )
    summary = repository.sync_discovered_records(
        run_id="run2",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        probe_results={("2025", "2025_TEOS_XML_01A"): initial_probe},
        checked_at="2026-03-21T00:00:00+00:00",
    )

    assert summary.unchanged_count == 1
    assert summary.skipped_download_count == 1
    state_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_01A.json"
    state_payload = json.loads(s3.store[("test-bucket", state_key)]["Body"].decode("utf-8"))
    assert state_payload["download_status"] == "skipped_unchanged"


def test_teos_manifest_sync_records_probe_failures_without_aborting_year_sync():
    s3 = FakeS3()
    repository = S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="teos/raw/xml/",
    )

    summary = repository.sync_discovered_records(
        run_id="run1",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        probe_results={
            ("2025", "2025_TEOS_XML_01A"): TeosZipProbeFailure(
                source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                checked_at="2026-03-20T00:00:00+00:00",
                error="HTTP Error 500: Internal Server Error",
            )
        },
        checked_at="2026-03-20T00:00:00+00:00",
    )

    assert summary.probe_failed_count == 1
    state_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_01A.json"
    state_payload = json.loads(s3.store[("test-bucket", state_key)]["Body"].decode("utf-8"))
    assert state_payload["current_sync_status"] == "probe_failed"
    assert state_payload["download_status"] == "probe_failed"
    assert "HTTP Error 500" in state_payload["last_error"]


def test_teos_manifest_sync_resets_processing_state_when_zip_changes():
    s3 = FakeS3()
    repository = S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="teos/raw/xml/",
    )
    repository.save_record(
        repository.sync_discovered_records(
            run_id="seed",
            discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
            probe_results={
                ("2025", "2025_TEOS_XML_01A"): TeosZipProbeResult(
                    source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                    resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                    etag='"etag-1"',
                    last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
                    content_length=1234,
                    checked_at="2026-03-20T00:00:00+00:00",
                    method_used="HEAD",
                )
            },
            checked_at="2026-03-20T00:00:00+00:00",
        ).records[0]
    )
    existing = repository.load_record("2025", "2025_TEOS_XML_01A")
    repository.save_record(
        existing.__class__(
            **{
                **existing.to_dict(),
                "download_status": "downloaded",
                "extraction_status": "extracted",
                "processing_status": "success",
            }
        )
    )

    repository.sync_discovered_records(
        run_id="run2",
        discovered_sources=[_record("2025", "2025_TEOS_XML_01A")],
        probe_results={
            ("2025", "2025_TEOS_XML_01A"): TeosZipProbeResult(
                source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
                etag='"etag-2"',
                last_modified="Fri, 21 Mar 2026 00:00:00 GMT",
                content_length=2234,
                checked_at="2026-03-21T00:00:00+00:00",
                method_used="HEAD",
            )
        },
        checked_at="2026-03-21T00:00:00+00:00",
    )

    state_key = "form990/normalized/manifests/teos-zip/state/latest/year=2025/source_batch=2025_TEOS_XML_01A.json"
    state_payload = json.loads(s3.store[("test-bucket", state_key)]["Body"].decode("utf-8"))
    assert state_payload["download_status"] == "scheduled"
    assert state_payload["extraction_status"] == "pending"
    assert state_payload["processing_status"] == "pending"
