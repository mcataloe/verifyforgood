from __future__ import annotations

import json
import pathlib

from infrastructure.charity_status.form990 import Form990IngestService
from infrastructure.charity_status.form990.teos_batch_processing import (
    PROCESSING_STATUS_PENDING,
    PROCESSING_STATUS_SUCCEEDED,
    process_teos_manifest_batch,
)
from infrastructure.charity_status.form990.teos_manifest import S3TeosZipManifestRepository, TeosZipManifestRecord


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        return {"Body": _Body(self.store[(Bucket, Key)]["Body"])}

    def list_objects_v2(self, Bucket, Prefix, **kwargs):
        del kwargs
        contents = [{"Key": key} for (bucket, key), _value in self.store.items() if bucket == Bucket and key.startswith(Prefix)]
        return {"Contents": contents, "IsTruncated": False}


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self, size: int = -1):
        if isinstance(self._value, bytes):
            if size is None or size < 0:
                value, self._value = self._value, b""
                return value
            value = self._value[:size]
            self._value = self._value[size:]
            return value
        text = str(self._value).encode("utf-8")
        if size is None or size < 0:
            self._value = b""
            return text
        value = text[:size]
        self._value = text[size:]
        return value


def _manifest_record(*, processing_status: str = PROCESSING_STATUS_PENDING) -> TeosZipManifestRecord:
    return TeosZipManifestRecord(
        tax_year="2025",
        source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11C.zip",
        zip_basename="2025_TEOS_XML_11C",
        discovered_at="2026-03-20T00:00:00+00:00",
        last_checked_at="2026-03-20T00:00:00+00:00",
        resolved_source_url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11C.zip",
        content_length=1234,
        etag='"etag-11c"',
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        current_sync_status="changed",
        download_status="downloaded",
        extraction_status="extracted",
        processing_status=processing_status,
        destination_raw_s3_prefix="teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C",
        downloaded_zip_s3_key="form990/raw-sources/2025/zip_archive/2025_teos_xml_11c/sig/2025_TEOS_XML_11C.zip",
        extracted_file_count=1,
        last_error=None,
        created_at="2026-03-20T00:00:00+00:00",
        updated_at="2026-03-20T00:00:00+00:00",
    )


def _service(s3):
    return Form990IngestService(
        bucket="test-bucket",
        raw_prefix="form990/raw/",
        metadata_prefix="form990/normalized/metadata/",
        manifest_prefix="form990/normalized/manifests/",
        metrics_prefix="form990/normalized/metrics/",
        governance_prefix="form990/normalized/governance/",
        quality_prefix="form990/normalized/quality/",
        relationships_prefix="form990/normalized/relationships/",
        s3_client=s3,
    )


def _repository(s3):
    return S3TeosZipManifestRepository(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        raw_xml_prefix="teos/raw/xml/",
    )


def test_process_teos_manifest_batch_parses_raw_source_batch_successfully():
    s3 = FakeS3()
    repository = _repository(s3)
    record = _manifest_record()
    repository.save_record(record)
    xml_bytes = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    s3.put_object(
        Bucket="test-bucket",
        Key="teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C/202500123_public.xml",
        Body=xml_bytes,
    )

    result = process_teos_manifest_batch(
        service=_service(s3),
        repository=repository,
        manifest_record=record,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
    )

    assert result.skipped is False
    assert result.manifest_record.processing_status == "success"
    assert result.ingest_result["parsed_count"] == 1
    assert any(
        bucket == "test-bucket" and key.startswith("form990/raw/year=2025/source_batch=2025_TEOS_XML_11C/")
        for bucket, key in s3.store
    )
    persisted = repository.load_record("2025", "2025_TEOS_XML_11C")
    assert persisted is not None
    assert persisted.processing_status == "success"


def test_process_teos_manifest_batch_skips_already_processed_unchanged_batch():
    s3 = FakeS3()
    repository = _repository(s3)
    record = _manifest_record(processing_status=PROCESSING_STATUS_SUCCEEDED)
    repository.save_record(record)
    s3.put_object(
        Bucket="test-bucket",
        Key="teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C/202500123_public.xml",
        Body=pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes(),
    )

    result = process_teos_manifest_batch(
        service=_service(s3),
        repository=repository,
        manifest_record=record,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
    )

    assert result.skipped is True
    assert result.ingest_result["status"] == "skipped"
    assert result.ingest_result["records_processed"] == 0


def test_process_teos_manifest_batch_records_failed_processing_diagnostics():
    s3 = FakeS3()
    repository = _repository(s3)
    record = _manifest_record()
    repository.save_record(record)
    s3.put_object(
        Bucket="test-bucket",
        Key="teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C/202500123_public.xml",
        Body=b"<Return><bad></Return>",
    )

    result = process_teos_manifest_batch(
        service=_service(s3),
        repository=repository,
        manifest_record=record,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
    )

    assert result.skipped is False
    assert result.manifest_record.processing_status == "failed"
    assert result.ingest_result["failed_count"] == 1
    persisted = repository.load_record("2025", "2025_TEOS_XML_11C")
    assert persisted is not None
    assert persisted.processing_status == "failed"
    assert persisted.last_error is not None
    assert "mismatched tag" in persisted.last_error.lower()
