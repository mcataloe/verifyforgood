import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from infrastructure.verification.form990 import monthly_processing
from infrastructure.verification.form990.monthly_processing import (
    MonthlyIngestMalformedArchiveError,
    MonthlyIngestSourceObject,
    MonthlyIngestSourceObjectNotFoundError,
    MonthlyIngestTaskInputError,
    parse_form990_source_object,
    process_form990_archive,
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


class RecordingProgressSession:
    def __init__(self):
        self.calls = []
        self.completed = False

    def item_completed(self, increments=None, *, last_item=None):
        self.calls.append({"increments": dict(increments or {}), "last_item": last_item})

    def complete(self):
        self.completed = True


class RecordingProgressReporter:
    def __init__(self):
        self.starts = []
        self.sessions = []

    def start(self, *, total_items, fields, update_every=10):
        session = RecordingProgressSession()
        self.starts.append(
            {
                "total_items": total_items,
                "field_keys": [field.key for field in fields],
                "update_every": update_every,
            }
        )
        self.sessions.append(session)
        return session


def _worker_env(**overrides):
    payload = {
        "source_key": "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
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
        "MONTHLY_INGEST_SOURCE_KEY": payload["source_key"],
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
        "infrastructure.verification.form990.monthly_processing._download_source_archive",
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
        "infrastructure.verification.form990.monthly_processing._download_source_archive",
        lambda source_url: _write_temp_archive(archive_bytes, checksum),
    )

    with pytest.raises(MonthlyIngestMalformedArchiveError):
        run_form990_monthly_processing_task(env=_worker_env())
    monkeypatch.undo()


def test_worker_raises_for_missing_source_object():
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "infrastructure.verification.form990.monthly_processing._download_source_archive",
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
        "infrastructure.verification.form990.monthly_processing._download_source_archive",
        lambda source_url: _write_temp_archive(archive_bytes, checksum),
    )

    with pytest.raises(MonthlyIngestMalformedArchiveError, match="processable XML members"):
        run_form990_monthly_processing_task(env=_worker_env())
    monkeypatch.undo()


def test_worker_skips_archive_when_head_metadata_is_unchanged(monkeypatch):
    metadata_service = FakeArchiveMetadataService(skip_archive=True)
    monkeypatch.setattr(
        "infrastructure.verification.form990.monthly_processing._probe_archive_metadata",
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
        "infrastructure.verification.form990.monthly_processing._download_source_archive",
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


def test_process_form990_archive_reports_selection_progress_before_parse_progress(tmp_path):
    metadata_service = FakeArchiveMetadataService()
    archive_bytes = _make_zip(
        ("folder/obj-1.xml", _valid_xml(ein="123456789")),
        ("folder/obj-2.xml", _valid_xml(ein="987654321")),
    )
    archive_path, checksum, size = _write_temp_archive(archive_bytes, hashlib.sha256(archive_bytes).hexdigest())

    try:
        archive_record = metadata_service.ensure_archive_record(
            source_url="https://example.org/2026_TEOS_XML_02A.zip",
            filename="2026_TEOS_XML_02A.zip",
            checked_at=datetime.now(timezone.utc),
        )
        extracted_dir = tmp_path / "initial-extract"
        extracted_members = monthly_processing.extract_zip_xml_members_to_workdir(
            archive_path=archive_path,
            workdir=str(extracted_dir),
            max_xml_file_size_bytes=monthly_processing.DEFAULT_MAX_XML_FILE_SIZE_BYTES,
        )
        first_member_hash = monthly_processing._hash_local_xml_file(extracted_members[0].local_path)
        metadata_service.upsert_extracted_file(
            archive_id=archive_record.archive_id,
            filename=extracted_members[0].member_name,
            content_hash=first_member_hash,
            parse_status="parsed",
        )
        for member in extracted_members:
            monthly_processing._delete_local_xml_file(member.local_path)

        progress_reporter = RecordingProgressReporter()
        result = process_form990_archive(
            archive_path=archive_path,
            archive_checksum=checksum,
            archive_size=size,
            extracted_workdir=str(tmp_path / "selection-progress"),
            processing_context={
                "source_key": "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
                "job_id": "selection-progress-job",
                "correlation_id": "selection-progress-corr",
                "workflow_version": "2026-03",
                "source_url": "https://example.org/2026_TEOS_XML_02A.zip",
            },
            source_object=MonthlyIngestSourceObject(
                source_year="2026",
                source_kind="zip_archive",
                source_archive_key="2026_teos_xml_02a",
                source_signature="sig-1",
                source_filename="2026_TEOS_XML_02A.zip",
            ),
            archive_metadata_service=metadata_service,
            archive_record=archive_record,
            progress_reporter=progress_reporter,
        )

        assert result["selected_member_count"] == 1
        assert result["skipped_unchanged_member_count"] == 1
        assert progress_reporter.starts[0] == {
            "total_items": 2,
            "field_keys": ["selected", "skipped"],
            "update_every": 10,
        }
        assert progress_reporter.sessions[0].calls == [
            {"increments": {"skipped": 1}, "last_item": "obj-1.xml"},
            {"increments": {"selected": 1}, "last_item": "obj-2.xml"},
        ]
        assert progress_reporter.sessions[0].completed is True
        assert progress_reporter.starts[1]["field_keys"] == ["parsed", "failed"]
        assert progress_reporter.sessions[1].calls == [{"increments": {"parsed": 1}, "last_item": "obj-2.xml"}]
    finally:
        import os

        os.unlink(archive_path)


def test_process_form990_archive_logs_split_persistence_stage_timings(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_06A.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", _valid_xml())))
    events: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(
        monthly_processing,
        "_log_structured",
        lambda event, **fields: events.append((event, fields)),
    )

    result = process_form990_archive(
        archive_path=str(archive_path),
        extracted_workdir=str(tmp_path / "timing-extracted"),
        processing_context={
            "source_key": "local/archive.zip",
            "job_id": "timing-job",
            "correlation_id": "timing-corr",
            "workflow_version": "local-cli",
        },
        source_object=MonthlyIngestSourceObject(
            source_year="2026",
            source_kind="zip_archive",
            source_archive_key="2026_teos_xml_06a",
            source_signature="sig-6",
            source_filename="2026_TEOS_XML_06A.zip",
        ),
    )

    assert result["status"] == "success"
    stage_event = next(fields for event, fields in events if event == "monthly_ingest.worker.stage_timings")
    assert stage_event["total_duration_ms"] >= 0
    assert stage_event["unzip_duration_ms"] >= 0
    assert stage_event["selection_duration_ms"] >= 0
    assert stage_event["parse_duration_ms"] >= 0
    assert stage_event["nonprofit_persistence_duration_ms"] >= 0
    assert stage_event["extracted_file_metadata_duration_ms"] >= 0
    assert stage_event["persistence_duration_ms"] == (
        stage_event["nonprofit_persistence_duration_ms"] + stage_event["extracted_file_metadata_duration_ms"]
    )
    assert stage_event["parsed_count"] == 1
    assert stage_event["failed_count"] == 0
    assert stage_event["selected_member_count"] == 1
    assert stage_event["extracted_member_count"] == 1


def test_process_form990_archive_forwards_canonical_raw_filing_records(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_07A.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", _valid_xml())))
    persistence_calls: list[dict[str, object]] = []

    class RecordingPersistenceService:
        def persist_normalized_records(self, filing_records, *, canonical_raw_filing_records=None, persisted_at=None, progress_session=None):
            persistence_calls.append(
                {
                    "filing_records": filing_records,
                    "canonical_raw_filing_records": canonical_raw_filing_records,
                }
            )
            return SimpleNamespace(
                to_dict=lambda: {
                    "nonprofits_upserted": 1,
                    "filings_upserted": 1,
                    "sources_upserted": 1,
                    "skipped_records": 0,
                }
            )

    result = process_form990_archive(
        archive_path=str(archive_path),
        extracted_workdir=str(tmp_path / "canonical-raw"),
        processing_context={
            "source_key": "local/archive.zip",
            "job_id": "raw-job",
            "correlation_id": "raw-corr",
            "workflow_version": "local-cli",
        },
        source_object=MonthlyIngestSourceObject(
            source_year="2026",
            source_kind="zip_archive",
            source_archive_key="2026_teos_xml_07a",
            source_signature="sig-7",
            source_filename="2026_TEOS_XML_07A.zip",
        ),
        nonprofit_persistence_service=RecordingPersistenceService(),
    )

    assert result["status"] == "success"
    assert len(persistence_calls) == 1
    assert len(persistence_calls[0]["canonical_raw_filing_records"]) == 1
    raw_filing = persistence_calls[0]["canonical_raw_filing_records"][0]
    assert raw_filing["parser_version"] == "form990.xml_parser.v1"
    assert raw_filing["raw_filing_json"]["Return"]["ReturnData"]["IRS990"]["Filer"]["EIN"] == "123456789"


def _write_temp_archive(payload: bytes, checksum: str) -> tuple[str, str, int]:
    import tempfile
    from pathlib import Path

    handle = tempfile.NamedTemporaryFile(prefix="monthly-test-", suffix=".zip", delete=False)
    handle.write(payload)
    handle.close()
    return handle.name, checksum, Path(handle.name).stat().st_size

