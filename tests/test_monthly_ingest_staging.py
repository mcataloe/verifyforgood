import hashlib
from datetime import datetime, timezone

import pytest

from charity_status.form990.monthly_staging import stage_form990_monthly_source
from charity_status.ingest import shape_staging_result, validate_staging_result_payload


class FakeS3Client:
    def __init__(self):
        self.put_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)


def _env() -> dict[str, str]:
    return {
        "BUCKET": "charity-data",
        "FORM990_RAW_SOURCE_PREFIX": "form990/raw-sources/",
        "FORM990_MANIFEST_PREFIX": "form990/normalized/manifests/",
        "FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS": "300",
        "APP_ENV": "prod",
        "AWS_REGION": "us-east-1",
        "MONTHLY_INGEST_WORKFLOW_BASENAME": "monthly-ingest",
        "MONTHLY_INGEST_WORKFLOW_VERSION": "2026-03",
    }


def _event(*, source_key: str = "monthly-workflows/pending/job-123/source.zip", skip_staging: bool = False, schedule_context: dict | None = None) -> dict:
    payload = {
        "source_bucket": "charity-data",
        "source_key": source_key,
        "destination_bucket": "charity-data",
        "destination_prefix": "form990/normalized/manifests/",
        "job_id": "job-123",
        "correlation_id": "corr-123",
        "workflow_version": "2026-03",
    }
    return {
        "input": {
            **payload,
            "skip_staging": skip_staging,
            "schedule_context": schedule_context or {},
        },
        "resolved_input": payload,
        "workflow_name": "monthly-ingest-prod",
    }


def test_shape_staging_result_exposes_bucket_key_aliases_for_step_functions():
    result = shape_staging_result(
        bucket="charity-data",
        key="form990/raw-sources/2026/zip_archive/file.zip",
        job_id="job-123",
        correlation_id="corr-123",
        size=12,
        checksum="abc123",
        checksum_algorithm="sha256",
        source_timestamp="2026-03-01T00:00:00+00:00",
    )

    payload = result.to_dict()
    assert payload["bucket"] == "charity-data"
    assert payload["key"] == "form990/raw-sources/2026/zip_archive/file.zip"
    assert payload["source_bucket"] == payload["bucket"]
    assert payload["source_key"] == payload["key"]
    assert payload["status"] == "staged"
    assert validate_staging_result_payload(payload) == []


def test_stage_form990_monthly_source_downloads_zip_and_persists_raw_source_key():
    fake_s3 = FakeS3Client()
    now = datetime(2026, 3, 1, tzinfo=timezone.utc)
    body = b"monthly zip payload"
    checksum = hashlib.sha256(body).hexdigest()

    result = stage_form990_monthly_source(
        _event(
            schedule_context={
                "staging": {
                    "source_url": "https://example.org/2026_TEOS_XML_02A.zip",
                    "source_year": "2026",
                    "source_archive_key": "2026_teos_xml_02a",
                    "source_filename": "2026_TEOS_XML_02A.zip",
                    "source_timestamp": "2026-02-28T12:00:00Z",
                }
            }
        ),
        env=_env(),
        s3_client=fake_s3,
        downloader=lambda source_url, timeout_seconds: (body, "application/zip"),
        now=now,
    )

    assert result["bucket"] == "charity-data"
    assert result["key"] == f"form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sha256-{checksum}/2026_TEOS_XML_02A.zip"
    assert result["source_bucket"] == "charity-data"
    assert result["source_key"] == result["key"]
    assert result["size"] == len(body)
    assert result["checksum"] == checksum
    assert result["checksum_algorithm"] == "sha256"
    assert result["source_timestamp"] == "2026-02-28T12:00:00Z"
    assert len(fake_s3.put_calls) == 1
    assert fake_s3.put_calls[0]["Bucket"] == "charity-data"
    assert fake_s3.put_calls[0]["Key"] == result["key"]
    assert fake_s3.put_calls[0]["ContentType"] == "application/zip"
    assert fake_s3.put_calls[0]["Metadata"]["job_id"] == "job-123"
    assert fake_s3.put_calls[0]["Metadata"]["checksum_sha256"] == checksum


def test_stage_form990_monthly_source_can_infer_filename_archive_key_and_year_from_url():
    fake_s3 = FakeS3Client()
    body = b"inferred"
    checksum = hashlib.sha256(body).hexdigest()

    result = stage_form990_monthly_source(
        _event(
            schedule_context={
                "source_url": "https://example.org/downloads/2025_TEOS_XML_12B.zip",
            }
        ),
        env=_env(),
        s3_client=fake_s3,
        downloader=lambda source_url, timeout_seconds: (body, "application/zip"),
    )

    assert result["key"] == f"form990/raw-sources/2025/zip_archive/2025_teos_xml_12b/sha256-{checksum}/2025_TEOS_XML_12B.zip"


def test_stage_form990_monthly_source_returns_existing_location_when_skip_staging_true():
    fake_s3 = FakeS3Client()

    result = stage_form990_monthly_source(
        _event(
            source_key="form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/existing/2026_TEOS_XML_02A.zip",
            skip_staging=True,
        ),
        env=_env(),
        s3_client=fake_s3,
    )

    assert result == {
        "bucket": "charity-data",
        "key": "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/existing/2026_TEOS_XML_02A.zip",
        "source_bucket": "charity-data",
        "source_key": "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/existing/2026_TEOS_XML_02A.zip",
        "job_id": "job-123",
        "correlation_id": "corr-123",
        "status": "skipped",
        "workflow_version": "2026-03",
    }
    assert fake_s3.put_calls == []


def test_stage_form990_monthly_source_requires_upstream_schedule_context():
    with pytest.raises(ValueError, match="schedule_context.source_url is required"):
        stage_form990_monthly_source(
            _event(schedule_context={}),
            env=_env(),
            s3_client=FakeS3Client(),
        )


def test_stage_form990_monthly_source_surfaces_fetch_failures_without_s3_write():
    fake_s3 = FakeS3Client()

    with pytest.raises(RuntimeError, match="download failed"):
        stage_form990_monthly_source(
            _event(
                schedule_context={
                    "source_url": "https://example.org/2026_TEOS_XML_02A.zip",
                    "source_year": "2026",
                    "source_archive_key": "2026_teos_xml_02a",
                    "source_filename": "2026_TEOS_XML_02A.zip",
                }
            ),
            env=_env(),
            s3_client=fake_s3,
            downloader=lambda source_url, timeout_seconds: (_ for _ in ()).throw(RuntimeError("download failed")),
        )

    assert fake_s3.put_calls == []
