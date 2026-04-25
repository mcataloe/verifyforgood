from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from verification.backend.ingest.federal.form990 import monthly_processing
from verification.backend.ingest.federal.form990.monthly_processing import MonthlyIngestSourceObject, process_form990_archive
from verification.backend.ingest.federal.form990.source_catalog import SOURCE_KIND_ZIP_ARCHIVE, build_source_artifact
from verification.backend.ingest.federal import local_runner


class FakeS3:
    def __init__(self):
        self.store: dict[tuple[str, str], dict[str, object]] = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}


class FakeArchiveMetadataService:
    def __init__(self):
        self.archive = SimpleNamespace(archive_id=41, filename="archive.zip")
        self.should_process = True
        self.reason = "etag_changed"
        self.record_archive_probe_calls: list[dict[str, object]] = []
        self.ensure_archive_record_calls: list[dict[str, object]] = []
        self.mark_archive_processing_completed_calls: list[dict[str, object]] = []
        self.mark_archive_processing_failed_calls: list[dict[str, object]] = []

    def record_archive_probe(self, *, source_url, filename, probe):
        self.record_archive_probe_calls.append(
            {"source_url": source_url, "filename": filename, "probe": probe}
        )
        self.archive.filename = filename
        return SimpleNamespace(
            archive=self.archive,
            should_process=self.should_process,
            reason=self.reason,
        )

    def ensure_archive_record(self, *, source_url, filename, checked_at, status="pending"):
        self.ensure_archive_record_calls.append(
            {"source_url": source_url, "filename": filename, "checked_at": checked_at, "status": status}
        )
        self.archive.filename = filename
        return self.archive

    def mark_archive_processing_completed(self, archive_id, *, started_at=None, ended_at=None, processed_at=None, status="processed"):
        self.mark_archive_processing_completed_calls.append(
            {
                "archive_id": archive_id,
                "started_at": started_at,
                "ended_at": ended_at,
                "processed_at": processed_at,
                "status": status,
            }
        )
        return self.archive

    def mark_archive_processing_failed(self, archive_id, *, started_at=None, failed_at=None):
        self.mark_archive_processing_failed_calls.append(
            {"archive_id": archive_id, "started_at": started_at, "failed_at": failed_at}
        )
        return self.archive


def _make_zip(*members: tuple[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in members:
            archive.writestr(name, body)
    return stream.getvalue()


def _valid_xml(ein="123456789", tax_year="2024") -> bytes:
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


def _artifact_from_file(path: Path, *, archive_key: str, year: str = "2026"):
    return build_source_artifact(
        source_year=year,
        source_kind=SOURCE_KIND_ZIP_ARCHIVE,
        source_url=path.resolve().as_uri(),
        source_filename=path.name,
        source_archive_key=archive_key,
        discovered_at="2026-04-03T00:00:00+00:00",
        page_url="test://local",
    )


def _configure_local_runner(monkeypatch):
    monkeypatch.setattr(local_runner, "_build_archive_metadata_service", lambda env, logger: None)
    monkeypatch.setattr(local_runner, "build_form990_nonprofit_persistence_service", lambda env=None: None)


def test_cli_archive_url_processes_one_archive_and_cleans_workspace(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_02A.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))
    calls: list[tuple[Path, Path]] = []

    def fake_process_form990_archive(**kwargs):
        calls.append((Path(kwargs["archive_path"]), Path(kwargs["extracted_workdir"])))
        Path(kwargs["extracted_workdir"]).mkdir(parents=True, exist_ok=True)
        (Path(kwargs["extracted_workdir"]) / "obj-1.xml").write_text("<Return/>", encoding="utf-8")
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    workspace = tmp_path / "workspace"
    exit_code = local_runner.run_local_form990_ingest(
        archive_url=archive_path.resolve().as_uri(),
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(workspace),
        limit=None,
        env={},
    )

    assert exit_code == 0
    assert len(calls) == 1
    assert not (workspace / "archives" / "2026_teos_xml_02a.zip").exists()
    assert not (workspace / "extracted" / "2026_teos_xml_02a").exists()


def test_cli_keep_temp_preserves_workspace_files(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_02B.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))

    def fake_process_form990_archive(**kwargs):
        extracted_dir = Path(kwargs["extracted_workdir"])
        extracted_dir.mkdir(parents=True, exist_ok=True)
        (extracted_dir / "obj-1.xml").write_text("<Return/>", encoding="utf-8")
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    workspace = tmp_path / "workspace"
    exit_code = local_runner.run_local_form990_ingest(
        archive_url=archive_path.resolve().as_uri(),
        single_archive=False,
        strict=False,
        keep_temp=True,
        workspace=str(workspace),
        limit=None,
        env={},
    )

    assert exit_code == 0
    assert (workspace / "archives" / "2026_teos_xml_02b.zip").exists()
    assert (workspace / "extracted" / "2026_teos_xml_02b" / "obj-1.xml").exists()


def test_cli_passes_shared_progress_reporter_to_archive_processing(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_02D.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))
    captured = {}
    progress_reporter = object()

    def fake_process_form990_archive(**kwargs):
        captured["progress_reporter"] = kwargs.get("progress_reporter")
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "build_progress_reporter", lambda: progress_reporter)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    exit_code = local_runner.run_local_form990_ingest(
        archive_url=archive_path.resolve().as_uri(),
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={},
    )

    assert exit_code == 0
    assert captured["progress_reporter"] is progress_reporter


def test_cli_passes_xml_parser_worker_count_to_archive_processing(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_02E.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))
    captured: dict[str, object] = {}

    def fake_process_form990_archive(**kwargs):
        captured["xml_parser_workers"] = kwargs.get("xml_parser_workers")
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    exit_code = local_runner.run_local_form990_ingest(
        archive_url=archive_path.resolve().as_uri(),
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        xml_parser_workers=3,
        env={},
    )

    assert exit_code == 0
    assert captured["xml_parser_workers"] == 3


def test_cli_passes_persist_batch_size_from_env_to_archive_processing(tmp_path, monkeypatch):
    archive_path = tmp_path / "2026_TEOS_XML_02EB.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))
    captured: dict[str, object] = {}

    def fake_process_form990_archive(**kwargs):
        captured["persist_batch_size"] = kwargs.get("persist_batch_size")
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    exit_code = local_runner.run_local_form990_ingest(
        archive_url=archive_path.resolve().as_uri(),
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={"FORM990_PERSIST_BATCH_SIZE": "250"},
    )

    assert exit_code == 0
    assert captured["persist_batch_size"] == 250


def test_cli_logs_resolved_xml_parser_worker_count(tmp_path, monkeypatch, capsys):
    archive_path = tmp_path / "2026_TEOS_XML_02EA.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))

    def fake_process_form990_archive(**kwargs):
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    exit_code = local_runner.run_local_form990_ingest(
        archive_url=archive_path.resolve().as_uri(),
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={"FORM990_XML_PARSER_WORKERS": "12"},
    )

    assert exit_code == 0
    logged = capsys.readouterr().out
    assert '"component": "form990.cli"' in logged
    assert '"message": "resolved xml parser workers=12"' in logged


def test_cli_records_archive_probe_and_marks_completion_for_http_sources(tmp_path, monkeypatch):
    archive_bytes = _make_zip(("obj-1.xml", b"<Return/>"))
    metadata_service = FakeArchiveMetadataService()
    captured: dict[str, object] = {}

    def fake_download_archive_to_path(*, url, destination, timeout_seconds):
        destination.write_bytes(archive_bytes)

    def fake_process_form990_archive(**kwargs):
        captured["archive_record"] = kwargs.get("archive_record")
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    monkeypatch.setattr(local_runner, "_build_archive_metadata_service", lambda env, logger: metadata_service)
    monkeypatch.setattr(local_runner, "build_form990_nonprofit_persistence_service", lambda env=None: None)
    monkeypatch.setattr(local_runner, "_download_archive_to_path", fake_download_archive_to_path)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)
    monkeypatch.setattr(
        local_runner,
        "probe_archive_metadata",
        lambda source_url: SimpleNamespace(
            source_url=source_url,
            resolved_source_url=source_url,
            etag='"etag-41"',
            normalized_etag="etag-41",
            last_modified="Thu, 24 Apr 2026 00:00:00 GMT",
            content_length=1234,
            response_status=200,
            checked_at="2026-04-24T00:00:00+00:00",
            method_used="HEAD",
        ),
    )

    exit_code = local_runner.run_local_form990_ingest(
        archive_url="https://example.org/2026_TEOS_XML_02F.zip",
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={},
    )

    assert exit_code == 0
    assert len(metadata_service.record_archive_probe_calls) == 1
    assert metadata_service.ensure_archive_record_calls == []
    assert captured["archive_record"] is metadata_service.archive
    assert len(metadata_service.mark_archive_processing_completed_calls) == 1
    assert metadata_service.mark_archive_processing_failed_calls == []


def test_cli_skips_unchanged_archive_by_default_after_probe(tmp_path, monkeypatch, capsys):
    metadata_service = FakeArchiveMetadataService()
    metadata_service.should_process = False
    metadata_service.reason = "unchanged_archive"

    download_calls: list[dict[str, object]] = []
    process_calls: list[dict[str, object]] = []

    monkeypatch.setattr(local_runner, "_build_archive_metadata_service", lambda env, logger: metadata_service)
    monkeypatch.setattr(local_runner, "build_form990_nonprofit_persistence_service", lambda env=None: None)
    monkeypatch.setattr(
        local_runner,
        "_download_archive_to_path",
        lambda **kwargs: download_calls.append(kwargs),
    )
    monkeypatch.setattr(
        local_runner,
        "process_form990_archive",
        lambda **kwargs: process_calls.append(kwargs),
    )
    monkeypatch.setattr(
        local_runner,
        "probe_archive_metadata",
        lambda source_url: SimpleNamespace(
            source_url=source_url,
            resolved_source_url=source_url,
            etag='"etag-43"',
            normalized_etag="etag-43",
            last_modified="Thu, 24 Apr 2026 00:00:00 GMT",
            content_length=5555,
            response_status=200,
            checked_at="2026-04-24T00:00:00+00:00",
            method_used="HEAD",
        ),
    )

    exit_code = local_runner.run_local_form990_ingest(
        archive_url="https://example.org/2026_TEOS_XML_02H.zip",
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={},
    )

    assert exit_code == 0
    assert len(metadata_service.record_archive_probe_calls) == 1
    assert download_calls == []
    assert process_calls == []
    assert metadata_service.mark_archive_processing_completed_calls == []
    assert metadata_service.mark_archive_processing_failed_calls == []
    logged = capsys.readouterr().out
    assert '"message": "archive unchanged by probe reason=unchanged_archive; skipping local processing"' in logged


def test_cli_force_archive_reprocess_overrides_unchanged_probe(tmp_path, monkeypatch, capsys):
    archive_bytes = _make_zip(("obj-1.xml", b"<Return/>"))
    metadata_service = FakeArchiveMetadataService()
    metadata_service.should_process = False
    metadata_service.reason = "unchanged_archive"
    process_calls: list[dict[str, object]] = []

    def fake_download_archive_to_path(*, url, destination, timeout_seconds):
        destination.write_bytes(archive_bytes)

    def fake_process_form990_archive(**kwargs):
        process_calls.append(kwargs)
        return {
            "status": "success",
            "records_processed": 1,
            "parsed_count": 1,
            "failed_count": 0,
        }

    monkeypatch.setattr(local_runner, "_build_archive_metadata_service", lambda env, logger: metadata_service)
    monkeypatch.setattr(local_runner, "build_form990_nonprofit_persistence_service", lambda env=None: None)
    monkeypatch.setattr(local_runner, "_download_archive_to_path", fake_download_archive_to_path)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)
    monkeypatch.setattr(
        local_runner,
        "probe_archive_metadata",
        lambda source_url: SimpleNamespace(
            source_url=source_url,
            resolved_source_url=source_url,
            etag='"etag-44"',
            normalized_etag="etag-44",
            last_modified="Thu, 24 Apr 2026 00:00:00 GMT",
            content_length=6666,
            response_status=200,
            checked_at="2026-04-24T00:00:00+00:00",
            method_used="HEAD",
        ),
    )

    exit_code = local_runner.run_local_form990_ingest(
        archive_url="https://example.org/2026_TEOS_XML_02I.zip",
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={"FORM990_FORCE_ARCHIVE_REPROCESS": "true"},
    )

    assert exit_code == 0
    assert len(metadata_service.record_archive_probe_calls) == 1
    assert len(process_calls) == 1
    assert len(metadata_service.mark_archive_processing_completed_calls) == 1
    logged = capsys.readouterr().out
    assert '"message": "archive unchanged by probe reason=unchanged_archive; forcing local reprocess"' in logged


def test_cli_marks_archive_failed_when_processing_raises_after_probe(tmp_path, monkeypatch):
    archive_bytes = _make_zip(("obj-1.xml", b"<Return/>"))
    metadata_service = FakeArchiveMetadataService()

    def fake_download_archive_to_path(*, url, destination, timeout_seconds):
        destination.write_bytes(archive_bytes)

    monkeypatch.setattr(local_runner, "_build_archive_metadata_service", lambda env, logger: metadata_service)
    monkeypatch.setattr(local_runner, "build_form990_nonprofit_persistence_service", lambda env=None: None)
    monkeypatch.setattr(local_runner, "_download_archive_to_path", fake_download_archive_to_path)
    monkeypatch.setattr(local_runner, "process_form990_archive", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        local_runner,
        "probe_archive_metadata",
        lambda source_url: SimpleNamespace(
            source_url=source_url,
            resolved_source_url=source_url,
            etag='"etag-42"',
            normalized_etag="etag-42",
            last_modified="Thu, 24 Apr 2026 00:00:00 GMT",
            content_length=4321,
            response_status=200,
            checked_at="2026-04-24T00:00:00+00:00",
            method_used="HEAD",
        ),
    )

    exit_code = local_runner.run_local_form990_ingest(
        archive_url="https://example.org/2026_TEOS_XML_02G.zip",
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={},
    )

    assert exit_code == 1
    assert len(metadata_service.record_archive_probe_calls) == 1
    assert metadata_service.mark_archive_processing_completed_calls == []
    assert len(metadata_service.mark_archive_processing_failed_calls) == 1


def test_cli_single_archive_and_limit_bound_selected_archives(tmp_path, monkeypatch):
    archives = []
    for suffix in ("02A", "02B", "02C"):
        path = tmp_path / f"2026_TEOS_XML_{suffix}.zip"
        path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))
        archives.append(_artifact_from_file(path, archive_key=f"2026_teos_xml_{suffix.lower()}"))

    processed: list[str] = []

    def fake_process_form990_archive(**kwargs):
        processed.append(str(kwargs["processing_context"]["job_id"]))
        return {"status": "success", "records_processed": 1, "parsed_count": 1, "failed_count": 0}

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)
    monkeypatch.setattr(local_runner, "_resolve_archive_sources", lambda env, archive_url=None: archives)

    single_exit = local_runner.run_local_form990_ingest(
        archive_url=None,
        single_archive=True,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace-single"),
        limit=None,
        env={},
    )
    assert single_exit == 0
    assert len(processed) == 1

    processed.clear()
    limited_exit = local_runner.run_local_form990_ingest(
        archive_url=None,
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace-limit"),
        limit=2,
        env={},
    )
    assert limited_exit == 0
    assert len(processed) == 2


def test_cli_non_strict_logs_archive_failure_and_continues(tmp_path, monkeypatch, capsys):
    first = tmp_path / "2026_TEOS_XML_03A.zip"
    second = tmp_path / "2026_TEOS_XML_03B.zip"
    first.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))
    second.write_bytes(_make_zip(("obj-2.xml", b"<Return/>")))
    archives = [
        _artifact_from_file(first, archive_key="2026_teos_xml_03a"),
        _artifact_from_file(second, archive_key="2026_teos_xml_03b"),
    ]
    processed: list[str] = []

    def fake_process_form990_archive(**kwargs):
        archive_name = Path(kwargs["archive_path"]).stem
        processed.append(archive_name)
        if archive_name == "2026_teos_xml_03a":
            raise RuntimeError("boom")
        return {"status": "success", "records_processed": 1, "parsed_count": 1, "failed_count": 0}

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)
    monkeypatch.setattr(local_runner, "_resolve_archive_sources", lambda env, archive_url=None: archives)

    exit_code = local_runner.run_local_form990_ingest(
        archive_url=None,
        single_archive=False,
        strict=False,
        keep_temp=False,
        workspace=str(tmp_path / "workspace"),
        limit=None,
        env={},
    )

    assert exit_code == 1
    assert processed == ["2026_teos_xml_03a", "2026_teos_xml_03b"]
    logged = capsys.readouterr().out
    assert '"component": "form990.archive"' in logged
    assert '"archive": "2026_teos_xml_03a"' in logged
    assert '"message": "archive processing failed"' in logged


def test_cli_strict_stops_on_first_failure_and_includes_traceback(tmp_path, monkeypatch, capsys):
    archive_path = tmp_path / "2026_TEOS_XML_04A.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", b"<Return/>")))

    def fake_process_form990_archive(**kwargs):
        raise RuntimeError("strict failure")

    _configure_local_runner(monkeypatch)
    monkeypatch.setattr(local_runner, "process_form990_archive", fake_process_form990_archive)

    with pytest.raises(RuntimeError, match="strict failure"):
        local_runner.run_local_form990_ingest(
            archive_url=archive_path.resolve().as_uri(),
            single_archive=False,
            strict=True,
            keep_temp=False,
            workspace=str(tmp_path / "workspace"),
            limit=None,
            env={},
        )

    logged = capsys.readouterr().out
    assert '"traceback":' in logged


def test_process_form990_archive_reports_xml_failures_with_file_context_without_s3_artifacts(tmp_path):
    archive_path = tmp_path / "2026_TEOS_XML_05A.zip"
    archive_path.write_bytes(_make_zip(("bad-object.xml", b"<Return>")))
    xml_errors: list[tuple[str | None, str]] = []

    result = process_form990_archive(
        archive_path=str(archive_path),
        extracted_workdir=str(tmp_path / "extracted"),
        processing_context={
            "archive_identity": "form990/raw-sources/2026/zip_archive/2026_teos_xml_05a/sig-1/2026_TEOS_XML_05A.zip",
            "job_id": "local-cli-job",
            "correlation_id": "local-cli-corr",
            "workflow_version": "local-cli",
            "source_url": "https://www.irs.gov/pub/irs-soi/2026_TEOS_XML_05A.zip",
        },
        source_object=MonthlyIngestSourceObject(
            source_year="2026",
            source_kind=SOURCE_KIND_ZIP_ARCHIVE,
            source_archive_key="2026_teos_xml_05a",
            source_signature="sig-1",
            source_filename="2026_TEOS_XML_05A.zip",
        ),
        xml_error_handler=lambda file_name, exc, status: xml_errors.append((file_name, status)),
    )

    assert result["status"] == "partial_success"
    assert xml_errors == [("bad-object.xml", "malformed_xml")]
    assert result["artifact_paths"] is None


def test_process_form990_archive_deletes_selected_xml_files_after_parsing(tmp_path):
    archive_path = tmp_path / "2026_TEOS_XML_05B.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", _valid_xml())))

    result = process_form990_archive(
        archive_path=str(archive_path),
        extracted_workdir=str(tmp_path / "extracted-cleanup"),
        processing_context={
            "archive_identity": "local/archive.zip",
            "job_id": "cleanup-job",
            "correlation_id": "cleanup-corr",
            "workflow_version": "local-cli",
        },
        source_object=MonthlyIngestSourceObject(
            source_year="2026",
            source_kind=SOURCE_KIND_ZIP_ARCHIVE,
            source_archive_key="2026_teos_xml_05b",
            source_signature="sig-2",
            source_filename="2026_TEOS_XML_05B.zip",
        ),
        nonprofit_persistence_service=None,
    )

    assert result["status"] == "success"
    assert list((tmp_path / "extracted-cleanup").glob("*.xml")) == []


def test_process_form990_archive_runs_without_bucket_based_processing(tmp_path):
    archive_path = tmp_path / "2026_TEOS_XML_05C.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", _valid_xml())))

    result = process_form990_archive(
        archive_path=str(archive_path),
        extracted_workdir=str(tmp_path / "extracted-no-s3"),
        processing_context={
            "archive_identity": "local/archive.zip",
            "job_id": "no-s3-job",
            "correlation_id": "no-s3-corr",
            "workflow_version": "local-cli",
        },
        source_object=MonthlyIngestSourceObject(
            source_year="2026",
            source_kind=SOURCE_KIND_ZIP_ARCHIVE,
            source_archive_key="2026_teos_xml_05c",
            source_signature="sig-3",
            source_filename="2026_TEOS_XML_05C.zip",
        ),
    )

    assert result["status"] == "success"

