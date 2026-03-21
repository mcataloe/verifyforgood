import io
import json
import zipfile

import pytest

from infrastructure.charity_status.form990.monthly_processing import (
    MonthlyIngestMalformedArchiveError,
    MonthlyIngestSourceObjectNotFoundError,
    MonthlyIngestTaskInputError,
    parse_form990_source_object,
    run_form990_monthly_processing_task,
)


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        return {"Body": _Body(self.store[(Bucket, Key)]["Body"])}


class _Body:
    def __init__(self, payload):
        self._stream = io.BytesIO(payload if isinstance(payload, bytes) else str(payload).encode("utf-8"))

    def read(self, size=-1):
        return self._stream.read(size)


def _worker_env(**overrides):
    payload = {
        "source_bucket": "source-bucket",
        "source_key": "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
        "destination_bucket": "dest-bucket",
        "destination_prefix": "form990/normalized/manifests/",
        "job_id": "job-123",
        "correlation_id": "corr-123",
        "workflow_version": "2026-03",
    }
    payload.update(overrides.pop("payload_overrides", {}))
    return {
        "MONTHLY_INGEST_WORKFLOW_NAME": "monthly-ingest-prod",
        "MONTHLY_INGEST_WORKFLOW_VERSION": payload["workflow_version"],
        "MONTHLY_INGEST_JOB_ID": payload["job_id"],
        "MONTHLY_INGEST_CORRELATION_ID": payload["correlation_id"],
        "MONTHLY_INGEST_SOURCE_BUCKET": payload["source_bucket"],
        "MONTHLY_INGEST_SOURCE_KEY": payload["source_key"],
        "MONTHLY_INGEST_DESTINATION_BUCKET": payload["destination_bucket"],
        "MONTHLY_INGEST_DESTINATION_PREFIX": payload["destination_prefix"],
        "MONTHLY_INGEST_INPUT_JSON": json.dumps(payload, sort_keys=True),
        "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES": "20971520",
        **overrides,
    }


def _make_zip(*members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in members:
            archive.writestr(name, body)
    return stream.getvalue()


def _valid_xml(ein="123456789", tax_year="2024"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Return xmlns="http://www.irs.gov/efile">
  <ReturnHeader><TaxYr>{tax_year}</TaxYr></ReturnHeader>
  <ReturnData>
    <IRS990>
      <Filer><EIN>{ein}</EIN></Filer>
    </IRS990>
  </ReturnData>
</Return>
""".encode("utf-8")


def test_parse_form990_source_object_requires_raw_source_zip_contract():
    source = parse_form990_source_object(
        "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip"
    )

    assert source.source_year == "2026"
    assert source.source_kind == "zip_archive"
    assert source.source_archive_key == "2026_teos_xml_02a"

    with pytest.raises(MonthlyIngestTaskInputError, match="raw source contract"):
        parse_form990_source_object("too/short.zip")


def test_worker_rejects_invalid_runtime_input_before_processing():
    fake_s3 = FakeS3()
    env = _worker_env()
    env.pop("MONTHLY_INGEST_DESTINATION_PREFIX")

    with pytest.raises(MonthlyIngestTaskInputError, match="MONTHLY_INGEST_DESTINATION_PREFIX is required"):
        run_form990_monthly_processing_task(env=env, s3_client=fake_s3)


def test_worker_processes_staged_zip_and_writes_job_scoped_artifacts():
    fake_s3 = FakeS3()
    source_key = "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip"
    fake_s3.put_object(
        Bucket="source-bucket",
        Key=source_key,
        Body=_make_zip(("folder/obj-1.xml", _valid_xml())),
    )

    result = run_form990_monthly_processing_task(env=_worker_env(), s3_client=fake_s3)

    job_prefix = "form990/normalized/manifests/monthly-workflows/jobs/job-123"
    assert result["status"] == "success"
    assert result["manifest_s3_key"] == f"{job_prefix}/manifest.json"
    assert result["artifact_index_s3_key"] == f"{job_prefix}/artifacts.json"
    assert result["summary_s3_key"] == f"{job_prefix}/summary.json"
    assert ("dest-bucket", result["manifest_s3_key"]) in fake_s3.store
    assert ("dest-bucket", result["artifact_index_s3_key"]) in fake_s3.store
    assert ("dest-bucket", result["summary_s3_key"]) in fake_s3.store

    artifact_index = json.loads(fake_s3.store[("dest-bucket", result["artifact_index_s3_key"])]["Body"].decode("utf-8"))
    assert artifact_index["artifacts"]["raw_xml_prefix"] == f"{job_prefix}/raw-xml/"
    assert artifact_index["artifacts"]["processing_manifest_s3_key"].startswith(f"{job_prefix}/processing/manifest_")
    assert artifact_index["artifacts"]["filing_records_s3_key"].startswith(f"{job_prefix}/datasets/metadata/filings_")

    summary = json.loads(fake_s3.store[("dest-bucket", result["summary_s3_key"])]["Body"].decode("utf-8"))
    assert summary["records_processed"] == 1
    assert summary["parsed_count"] == 1
    assert summary["failed_count"] == 0


def test_worker_raises_for_malformed_zip_and_writes_failure_summary():
    fake_s3 = FakeS3()
    source_key = "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip"
    fake_s3.put_object(Bucket="source-bucket", Key=source_key, Body=b"not-a-zip")

    with pytest.raises(MonthlyIngestMalformedArchiveError):
        run_form990_monthly_processing_task(env=_worker_env(), s3_client=fake_s3)

    summary = json.loads(
        fake_s3.store[("dest-bucket", "form990/normalized/manifests/monthly-workflows/jobs/job-123/summary.json")]["Body"].decode(
            "utf-8"
        )
    )
    assert summary["status"] == "failed"
    assert summary["job_id"] == "job-123"


def test_worker_raises_for_missing_source_object_and_writes_failure_summary():
    fake_s3 = FakeS3()

    with pytest.raises(MonthlyIngestSourceObjectNotFoundError):
        run_form990_monthly_processing_task(env=_worker_env(), s3_client=fake_s3)

    manifest = json.loads(
        fake_s3.store[("dest-bucket", "form990/normalized/manifests/monthly-workflows/jobs/job-123/manifest.json")]["Body"].decode(
            "utf-8"
        )
    )
    assert manifest["status"] == "failed"
    assert "source object not found" in manifest["error"]


def test_worker_fails_when_zip_contains_no_processable_xml_members():
    fake_s3 = FakeS3()
    source_key = "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip"
    fake_s3.put_object(
        Bucket="source-bucket",
        Key=source_key,
        Body=_make_zip(("README.txt", b"ignored")),
    )

    with pytest.raises(MonthlyIngestMalformedArchiveError, match="processable XML members"):
        run_form990_monthly_processing_task(env=_worker_env(), s3_client=fake_s3)
