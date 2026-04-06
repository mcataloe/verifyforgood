from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from charity_status.form990 import monthly_processing
from charity_status.form990.monthly_processing import MonthlyIngestSourceObject, process_form990_archive
from charity_status.form990.source_catalog import SOURCE_KIND_ZIP_ARCHIVE, build_source_artifact
from charity_status_backend.ingest_task import local_runner


class FakeS3:
    def __init__(self):
        self.store: dict[tuple[str, str], dict[str, object]] = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}


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
            "source_key": "form990/raw-sources/2026/zip_archive/2026_teos_xml_05a/sig-1/2026_TEOS_XML_05A.zip",
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

    assert result["status"] == "failed"
    assert xml_errors == [("bad-object.xml", "malformed_xml")]
    assert result["artifact_paths"] is None


def test_process_form990_archive_deletes_selected_xml_files_after_parsing(tmp_path):
    archive_path = tmp_path / "2026_TEOS_XML_05B.zip"
    archive_path.write_bytes(_make_zip(("obj-1.xml", _valid_xml())))

    result = process_form990_archive(
        archive_path=str(archive_path),
        extracted_workdir=str(tmp_path / "extracted-cleanup"),
        processing_context={
            "source_key": "local/archive.zip",
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
            "source_key": "local/archive.zip",
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
