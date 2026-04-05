import hashlib
import io
import json
import zipfile
from types import SimpleNamespace

import pytest

from infrastructure.charity_status.form990.monthly_processing import (
    MonthlyIngestMalformedArchiveError,
    MonthlyIngestSourceObjectNotFoundError,
    MonthlyIngestTaskInputError,
    parse_form990_source_object,
    run_form990_monthly_processing_task,
)


class FakeArchiveMetadataService:
    def __init__(self, *, skip_archive: bool = False):
        self.skip_archive = skip_archive
        self.archives = {}
        self.files = {}

    def record_archive_probe(self, *, source_url, filename, probe):
        archive = self.archives.get(source_url)
        if archive is None:
            archive = SimpleNamespace(
                archive_id=len(self.archives) + 1,
                source_url=source_url,
                filename=filename,
                update_started_at=None,
                update_ended_at=None,
                processing_duration_ms=None,
                last_processed_at=None,
            )
            self.archives[source_url] = archive
        return SimpleNamespace(archive=archive, should_process=not self.skip_archive, reason="unchanged_archive" if self.skip_archive else "new_archive")

    def ensure_archive_record(self, *, source_url, filename, checked_at, status="pending"):
        archive = self.archives.get(source_url)
        if archive is None:
            archive = SimpleNamespace(
                archive_id=len(self.archives) + 1,
                source_url=source_url,
                filename=filename,
                update_started_at=None,
                update_ended_at=None,
                processing_duration_ms=None,
                last_processed_at=None,
            )
            self.archives[source_url] = archive
        return archive

    def get_extracted_file(self, archive_id, filename):
        return self.files.get((archive_id, filename))

    def upsert_extracted_file(self, *, archive_id, filename, content_hash, parse_status, parsed_at=None, error_message=None):
        record = SimpleNamespace(
            archive_id=archive_id,
            filename=filename,
            content_hash=content_hash,
            parse_status=parse_status,
            parsed_at=parsed_at,
            error_message=error_message,
        )
        self.files[(archive_id, filename)] = record
        return record

    def mark_archive_processing_started(self, archive_id, *, started_at=None):
        for archive in self.archives.values():
            if archive.archive_id == archive_id:
                archive.update_started_at = started_at.isoformat() if started_at is not None else None
                archive.status = "processing"
                return archive
        return None

    def mark_archive_processing_completed(self, archive_id, *, started_at=None, ended_at=None, processed_at=None, status="processed"):
        for archive in self.archives.values():
            if archive.archive_id == archive_id:
                archive.update_started_at = started_at.isoformat() if started_at is not None else archive.update_started_at
                archive.update_ended_at = ended_at.isoformat() if ended_at is not None else None
                archive.last_processed_at = processed_at.isoformat() if processed_at is not None else None
                if started_at is not None and ended_at is not None:
                    archive.processing_duration_ms = int((ended_at - started_at).total_seconds() * 1000)
                archive.status = status
                return archive
        return None

    def mark_archive_processing_failed(self, archive_id, *, started_at=None, failed_at=None):
        return self.mark_archive_processing_completed(
            archive_id,
            started_at=started_at,
            ended_at=failed_at,
            processed_at=failed_at,
            status="failed",
        )


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
    env = _worker_env()
    env.pop("MONTHLY_INGEST_SOURCE_KEY")

    with pytest.raises(MonthlyIngestTaskInputError, match="MONTHLY_INGEST_SOURCE_KEY is required"):
        run_form990_monthly_processing_task(env=env)


def test_worker_processes_staged_zip_without_s3_artifacts(monkeypatch):
    archive_bytes = _make_zip(("folder/obj-1.xml", _valid_xml()))
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    monkeypatch.setattr(
        "infrastructure.charity_status.form990.monthly_processing._download_source_archive",
        lambda source_url: _write_temp_archive(archive_bytes, checksum),
    )

    result = run_form990_monthly_processing_task(env=_worker_env())

    assert result["status"] == "success"
    assert result["artifact_paths"] is None
    assert result["records_processed"] == 1
    assert result["parsed_count"] == 1
    assert result["failed_count"] == 0


def test_worker_raises_for_malformed_zip():
    archive_bytes = b"not-a-zip"
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "infrastructure.charity_status.form990.monthly_processing._download_source_archive",
        lambda source_url: _write_temp_archive(archive_bytes, checksum),
    )

    with pytest.raises(MonthlyIngestMalformedArchiveError):
        run_form990_monthly_processing_task(env=_worker_env())
    monkeypatch.undo()


def test_worker_raises_for_missing_source_object():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "infrastructure.charity_status.form990.monthly_processing._download_source_archive",
        lambda source_url: (_ for _ in ()).throw(MonthlyIngestSourceObjectNotFoundError(f"source archive not found at {source_url}")),
    )

    with pytest.raises(MonthlyIngestSourceObjectNotFoundError):
        run_form990_monthly_processing_task(env=_worker_env())
    monkeypatch.undo()


def test_worker_fails_when_zip_contains_no_processable_xml_members():
    archive_bytes = _make_zip(("README.txt", b"ignored"))
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "infrastructure.charity_status.form990.monthly_processing._download_source_archive",
        lambda source_url: _write_temp_archive(archive_bytes, checksum),
    )

    with pytest.raises(MonthlyIngestMalformedArchiveError, match="processable XML members"):
        run_form990_monthly_processing_task(env=_worker_env())
    monkeypatch.undo()


def test_worker_skips_archive_when_head_metadata_is_unchanged(monkeypatch):
    metadata_service = FakeArchiveMetadataService(skip_archive=True)
    monkeypatch.setattr(
        "infrastructure.charity_status.form990.monthly_processing._probe_archive_metadata",
        lambda source_url, checked_at: SimpleNamespace(
            source_url=source_url,
            resolved_source_url=source_url,
            etag='"etag-1"',
            normalized_etag="etag-1",
            last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
            content_length=1234,
            response_status=200,
            checked_at=checked_at.isoformat(),
            method_used="HEAD",
        ),
    )

    result = run_form990_monthly_processing_task(
        env=_worker_env(
            payload_overrides={
                "schedule_context": {
                    "source_url": "https://example.org/2026_TEOS_XML_02A.zip",
                }
            }
        ),
        archive_metadata_service=metadata_service,
    )

    assert result["status"] == "success"
    assert result["skipped_archive"] is True
    assert result["skip_reason"] == "unchanged_archive"


def test_worker_skips_unchanged_xml_files_when_hash_matches():
    metadata_service = FakeArchiveMetadataService()
    archive_bytes = _make_zip(("folder/obj-1.xml", _valid_xml()))
    checksum = hashlib.sha256(archive_bytes).hexdigest()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "infrastructure.charity_status.form990.monthly_processing._download_source_archive",
        lambda source_url: _write_temp_archive(archive_bytes, checksum),
    )

    first = run_form990_monthly_processing_task(
        env=_worker_env(),
        archive_metadata_service=metadata_service,
    )
    second = run_form990_monthly_processing_task(
        env=_worker_env(),
        archive_metadata_service=metadata_service,
    )

    assert first["parsed_count"] == 1
    assert second["parsed_count"] == 0
    assert second["records_processed"] == 0
    assert second["skipped_unchanged_member_count"] == 1
    monkeypatch.undo()


def _write_temp_archive(payload: bytes, checksum: str) -> tuple[str, str, int]:
    import tempfile
    from pathlib import Path

    handle = tempfile.NamedTemporaryFile(prefix="monthly-test-", suffix=".zip", delete=False)
    handle.write(payload)
    handle.close()
    return handle.name, checksum, Path(handle.name).stat().st_size
