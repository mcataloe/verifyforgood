from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import zipfile64.zipfile as zipfile

from verification.backend.ingest.federal.form990.canonical import hash_local_xml_file
from verification.backend.ingest.federal.form990.extractors.metadata import extract_metadata_fields
from verification.backend.ingest.federal.form990.hardening import classify_error, validate_runtime_config
from verification.backend.ingest.federal.form990.ingest import finalize_form990_filing_records, parse_form990_record_xml
from verification.backend.ingest.federal.form990.models import Form990IndexRecord, Form990MetadataRecord, Form990ParseStatus
from verification.backend.ingest.federal.form990.parser import XmlParseError, parse_xml
from verification.backend.ingest.shared import EcsTaskRuntimeContract, MonthlyIngestWorkflowInput
from verification.backend.shared.ops import ProgressField, ProgressReporter
from verification.backend.shared.runtime_logging import configure_runtime_logging, log_structured
LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)

DEFAULT_MAX_XML_FILE_SIZE_BYTES = 20 * 1024 * 1024
DEFAULT_FORM990_PERSIST_BATCH_SIZE = 100
MAX_FORM990_PERSIST_BATCH_SIZE = 1000


class MonthlyIngestTaskInputError(ValueError):
    pass


class MonthlyIngestSourceObjectNotFoundError(FileNotFoundError):
    pass


class MonthlyIngestMalformedArchiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class MonthlyIngestSourceObject:
    source_year: str
    source_kind: str
    source_archive_key: str
    source_signature: str
    source_filename: str


@dataclass(frozen=True)
class LocalExtractedXmlMember:
    member_name: str
    local_path: str | None
    content_length: int


@dataclass(frozen=True)
class _RuntimeArchiveProbe:
    source_url: str
    resolved_source_url: str | None
    etag: str | None
    normalized_etag: str | None
    last_modified: str | None
    content_length: int | None
    response_status: int
    checked_at: str
    method_used: str


@dataclass(frozen=True)
class _ArchiveProcessingContext:
    archive_identity: str
    job_id: str
    correlation_id: str
    workflow_version: str
    source_url: str | None = None


@dataclass
class _WorkerArchiveReaderEntry:
    archive: zipfile.ZipFile
    members: tuple[zipfile.ZipInfo, ...]


class _ThreadLocalArchiveReaderPool:
    def __init__(self, *, archive_path: str):
        self._archive_path = archive_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._entries_by_thread_id: dict[int, _WorkerArchiveReaderEntry] = {}

    def current(self) -> _WorkerArchiveReaderEntry:
        entry = getattr(self._local, "entry", None)
        if entry is not None and getattr(entry.archive, "fp", None) is not None:
            return entry
        archive = zipfile.ZipFile(self._archive_path, mode="r")
        entry = _WorkerArchiveReaderEntry(
            archive=archive,
            members=tuple(archive.infolist()),
        )
        self._local.entry = entry
        with self._lock:
            self._entries_by_thread_id[threading.get_ident()] = entry
        return entry

    def close_all(self) -> None:
        with self._lock:
            entries = list(self._entries_by_thread_id.values())
            self._entries_by_thread_id.clear()
        for entry in entries:
            entry.archive.close()


@dataclass(frozen=True)
class _LocalXmlMemberTask:
    archive_path: str
    extracted_workdir: str
    member_index: int
    member_name: str
    archive_identity: str
    source_object: MonthlyIngestSourceObject
    existing_content_hash: str | None = None
    archive_reader_pool: _ThreadLocalArchiveReaderPool | None = None


@dataclass(frozen=True)
class _QueuedXmlMemberTask:
    archive_path: str
    member_index: int
    member_name: str
    archive_identity: str
    source_object: MonthlyIngestSourceObject
    existing_content_hash: str | None = None
    archive_reader_pool: _ThreadLocalArchiveReaderPool | None = None


@dataclass(frozen=True)
class _LocalXmlParseTask:
    member: LocalExtractedXmlMember
    record: Form990IndexRecord
    source_reference: str
    xml_bytes: bytes
    xml_content_hash: str | None = None


@dataclass(frozen=True)
class _ParsedXmlMemberResult:
    member: LocalExtractedXmlMember
    filing_record: dict[str, Any] | None = None
    relationship_records: tuple[dict[str, Any], ...] = ()
    canonical_raw_filing_record: dict[str, Any] | None = None
    content_hash: str | None = None
    was_selected: bool = False
    was_skipped_unchanged: bool = False
    worker_extract_duration_ms: int = 0
    worker_hash_duration_ms: int = 0
    worker_selection_duration_ms: int = 0
    worker_read_duration_ms: int = 0
    worker_parse_duration_ms: int = 0
    worker_total_duration_ms: int = 0


@dataclass
class _StreamingParsePersistenceState:
    started: datetime
    nonprofit_persistence_service: Any | None
    archive_metadata_service: Any | None
    archive_id: int | None
    persist_batch_size: int
    aggregated_records: list[dict[str, Any]] = field(default_factory=list)
    parsed_result_batch: list[_ParsedXmlMemberResult] = field(default_factory=list)
    parsed_count: int = 0
    failed_count: int = 0
    records_processed: int = 0
    extracted_member_count: int = 0
    selected_member_count: int = 0
    skipped_unchanged_member_count: int = 0
    nonprofit_persistence_elapsed_ms: int = 0
    extracted_file_metadata_elapsed_ms: int = 0
    worker_extract_elapsed_ms: int = 0
    worker_hash_elapsed_ms: int = 0
    worker_selection_elapsed_ms: int = 0
    worker_read_elapsed_ms: int = 0
    worker_parse_elapsed_ms: int = 0
    worker_total_elapsed_ms: int = 0
    parse_wait_elapsed_ms: int = 0
    persist_batch_count: int = 0
    max_persist_batch_size: int = 0
    parse_task_count: int = 0


def run_form990_monthly_processing_task(
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    archive_metadata_service: Any | None = None,
    nonprofit_persistence_service: Any | None = None,
) -> dict[str, Any]:
    source = dict(os.environ) if env is None else dict(env)
    started_at = now or datetime.now(timezone.utc)
    contract = EcsTaskRuntimeContract()
    input_payload = _load_workflow_input(source, contract)
    config_errors = _validate_runtime_environment(source)
    if config_errors:
        raise MonthlyIngestTaskInputError("; ".join(config_errors))
    source_object = parse_form990_source_object(input_payload.archive_identity)
    processing_context = _ArchiveProcessingContext(
        archive_identity=input_payload.archive_identity,
        job_id=input_payload.job_id,
        correlation_id=input_payload.correlation_id,
        workflow_version=input_payload.workflow_version,
        source_url=input_payload.archive_url,
    )
    _log_structured(
        "monthly_ingest.worker.start",
        job_id=input_payload.job_id,
        correlation_id=input_payload.correlation_id,
        archive_identity=input_payload.archive_identity,
    )
    archive_source_url = _resolve_archive_source_url(input_payload) or _default_archive_source_url(source_object)
    archive_record = None
    archive_probe_outcome = None
    if archive_metadata_service is not None and archive_source_url and archive_source_url.startswith(("http://", "https://")):
        probe_outcome = _probe_archive_metadata(
            archive_source_url,
            checked_at=started_at,
        )
        archive_probe_outcome = archive_metadata_service.record_archive_probe(
            source_url=archive_source_url,
            filename=source_object.source_filename,
            probe=probe_outcome,
        )
        archive_record = archive_probe_outcome.archive
        if not archive_probe_outcome.should_process:
            skipped_result = {
                "status": "success",
                "job_id": input_payload.job_id,
                "correlation_id": input_payload.correlation_id,
                "records_processed": 0,
                "parsed_count": 0,
                "failed_count": 0,
                "skipped_archive": True,
                "skip_reason": archive_probe_outcome.reason,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "artifact_paths": None,
            }
            _log_structured(
                "monthly_ingest.worker.skipped_archive",
                job_id=input_payload.job_id,
                correlation_id=input_payload.correlation_id,
                source_url=archive_source_url,
                reason=archive_probe_outcome.reason,
            )
            return skipped_result

    try:
        archive_path, archive_checksum, archive_size = _download_source_archive(
            source_url=archive_source_url,
        )
    except Exception as exc:
        raise

    if archive_metadata_service is not None and archive_record is None:
        archive_record = archive_metadata_service.ensure_archive_record(
            source_url=archive_source_url,
            filename=source_object.source_filename,
            checked_at=started_at,
        )

    try:
        with tempfile.TemporaryDirectory(prefix="monthly-ingest-xml-") as workdir:
            result = process_form990_archive(
                archive_path=archive_path,
                archive_checksum=archive_checksum,
                archive_size=archive_size,
                extracted_workdir=workdir,
                processing_context=processing_context,
                source_object=source_object,
                started_at=started_at,
                archive_metadata_service=archive_metadata_service,
                archive_record=archive_record,
                nonprofit_persistence_service=nonprofit_persistence_service,
                max_xml_file_size_bytes=int(source.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES") or DEFAULT_MAX_XML_FILE_SIZE_BYTES),
                persist_batch_size=_resolve_form990_persist_batch_size(source),
            )
            if str(result.get("status") or "").strip().lower() == "failed":
                raise RuntimeError(f"monthly ingest processing failed with {int(result.get('failed_count') or 0)} failed record(s)")
            if archive_metadata_service is not None and archive_record is not None:
                archive_metadata_service.mark_archive_processing_completed(
                    archive_record.archive_id,
                    started_at=started_at,
                    ended_at=_datetime_or_now(result.get("completed_at")),
                    processed_at=_datetime_or_now(result.get("completed_at")),
                )
            _log_structured(
                "monthly_ingest.worker.completed",
                job_id=input_payload.job_id,
                correlation_id=input_payload.correlation_id,
                status=result["status"],
                records_processed=result["records_processed"],
                parsed_count=result["parsed_count"],
                failed_count=result["failed_count"],
            )
            return result
    except Exception as exc:
        _log_structured(
            "monthly_ingest.worker.failed",
            job_id=input_payload.job_id,
            correlation_id=input_payload.correlation_id,
            error_type=classify_error(exc),
            error=str(exc),
        )
        if archive_metadata_service is not None and archive_record is not None:
            archive_metadata_service.mark_archive_processing_failed(
                archive_record.archive_id,
                started_at=started_at,
                failed_at=datetime.now(timezone.utc),
            )
        raise
    finally:
        try:
            os.unlink(archive_path)
        except OSError:
            pass


def parse_form990_source_object(archive_identity: str) -> MonthlyIngestSourceObject:
    parts = [part for part in str(archive_identity or "").strip("/").split("/") if part]
    if len(parts) < 5:
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_ARCHIVE_IDENTITY must use the raw source contract")
    source_year, source_kind, source_archive_key, source_signature, source_filename = parts[-5:]
    if source_kind != "zip_archive":
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_ARCHIVE_IDENTITY must reference a zip_archive source object")
    if not source_filename.lower().endswith(".zip"):
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_ARCHIVE_IDENTITY must reference a .zip object")
    return MonthlyIngestSourceObject(
        source_year=source_year,
        source_kind=source_kind,
        source_archive_key=source_archive_key,
        source_signature=source_signature,
        source_filename=source_filename,
    )


def extract_zip_xml_members_to_workdir(
    *,
    archive_path: str,
    workdir: str,
    max_xml_file_size_bytes: int,
) -> list[LocalExtractedXmlMember]:
    extracted: list[LocalExtractedXmlMember] = []
    Path(workdir).mkdir(parents=True, exist_ok=True)
    _log_structured(
        "monthly_ingest.worker.unzip_start",
        level=logging.DEBUG,
        archive_path=archive_path,
        extracted_workdir=workdir,
    )
    try:
        _log_structured(
            "monthly_ingest.worker.unzip_in_progress",
            level=logging.DEBUG,
            archive_path=archive_path,
        )
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            for index, member in enumerate(archive.infolist()):
                if member.is_dir() or not member.filename.lower().endswith(".xml"):
                    continue
                if member.file_size > max_xml_file_size_bytes:
                    continue
                member_name = member.filename.replace("\\", "/")
                output_name = f"{index:05d}_{Path(member_name).name}"
                output_path = Path(workdir) / output_name
                with archive.open(member, mode="r") as source_handle, output_path.open("wb") as target_handle:
                    while True:
                        chunk = source_handle.read(64 * 1024)
                        if not chunk:
                            break
                        target_handle.write(chunk)
                extracted.append(
                    LocalExtractedXmlMember(
                        member_name=member_name,
                        local_path=str(output_path),
                        content_length=output_path.stat().st_size,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise MonthlyIngestMalformedArchiveError(f"bad zip archive at {archive_path}") from exc
    _log_structured(
        "monthly_ingest.worker.unzip_complete",
        level=logging.DEBUG,
        archive_path=archive_path,
        extracted_member_count=len(extracted),
    )
    return extracted


def build_local_index_records(
    *,
    extracted_members: list[LocalExtractedXmlMember],
    archive_identity: str,
    source_object: MonthlyIngestSourceObject,
    archive_checksum: str,
) -> tuple[list[Form990IndexRecord], dict[str, str]]:
    records: list[Form990IndexRecord] = []
    local_file_lookup: dict[str, str] = {}
    for member in extracted_members:
        xml_bytes = Path(member.local_path).read_bytes()
        xml_reference = _xml_reference(archive_identity=archive_identity, member_name=member.member_name)
        local_file_lookup[xml_reference] = member.local_path
        irs_object_id = _object_id_from_member_name(member.member_name)
        if not irs_object_id:
            continue
        try:
            parsed = parse_xml(xml_bytes)
            fields = extract_metadata_fields(parsed)
        except XmlParseError:
            fields = {}
        records.append(
            Form990IndexRecord(
                ein=_as_text(fields.get("ein")),
                tax_year=_as_text(fields.get("tax_year")) or source_object.source_year,
                filing_date=_as_text(fields.get("filing_date")),
                return_type=_as_text(fields.get("return_type")) or "990",
                irs_object_id=irs_object_id,
                xml_url=xml_reference,
                source_year=source_object.source_year,
                source_archive=source_object.source_archive_key,
                source_signature=_record_signature(
                    irs_object_id=irs_object_id,
                    xml_bytes=xml_bytes,
                    archive_checksum=archive_checksum,
                    source_year=source_object.source_year,
                    source_archive_key=source_object.source_archive_key,
                ),
            )
        )
    return records, local_file_lookup


def process_form990_archive(
    *,
    archive_path: str,
    extracted_workdir: str,
    processing_context: Mapping[str, str],
    source_object: MonthlyIngestSourceObject,
    archive_checksum: str | None = None,
    archive_size: int | None = None,
    started_at: datetime | None = None,
    archive_metadata_service: Any | None = None,
    archive_record: Any | None = None,
    nonprofit_persistence_service: Any | None = None,
    max_xml_file_size_bytes: int = DEFAULT_MAX_XML_FILE_SIZE_BYTES,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None = None,
    progress_reporter: ProgressReporter | None = None,
    xml_parser_workers: int = 1,
    persist_batch_size: int = DEFAULT_FORM990_PERSIST_BATCH_SIZE,
) -> dict[str, Any]:
    if isinstance(processing_context, _ArchiveProcessingContext):
        context = processing_context
    else:
        context = _ArchiveProcessingContext(
            archive_identity=str(processing_context.get("archive_identity") or "").strip(),
            job_id=str(processing_context.get("job_id") or "").strip(),
            correlation_id=str(processing_context.get("correlation_id") or "").strip(),
            workflow_version=str(processing_context.get("workflow_version") or "").strip(),
            source_url=_as_text(processing_context.get("source_url")),
        )
    started = started_at or datetime.now(timezone.utc)
    total_started_at = time.perf_counter()
    checksum = archive_checksum or _hash_file(archive_path)
    size = int(archive_size) if archive_size is not None else Path(archive_path).stat().st_size
    archive_identity = context.source_url or f"workspace://{context.archive_identity}"
    if archive_metadata_service is not None and archive_record is None:
        archive_record = archive_metadata_service.ensure_archive_record(
            source_url=archive_identity,
            filename=source_object.source_filename,
            checked_at=started,
        )
    if archive_metadata_service is not None and archive_record is not None:
        archive_metadata_service.mark_archive_processing_started(
            archive_record.archive_id,
            started_at=started,
        )
        _log_structured(
            "monthly_ingest.worker.archive_metadata_recorded",
            level=logging.DEBUG,
            job_id=context.job_id,
            archive_id=getattr(archive_record, "archive_id", None),
            source_url=archive_identity,
            filename=source_object.source_filename,
        )

    _log_structured(
        "monthly_ingest.worker.unzip_about_to_start",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        extracted_workdir=extracted_workdir,
    )
    processable_members = _processable_archive_members(
        archive_path=archive_path,
        max_xml_file_size_bytes=max_xml_file_size_bytes,
    )
    if not processable_members:
        raise MonthlyIngestMalformedArchiveError("zip archive did not contain any processable XML members")

    parser_workers = max(1, int(xml_parser_workers or 1))
    resolved_persist_batch_size = _clamp_persist_batch_size(persist_batch_size)
    existing_extracted_files_by_name = _list_existing_extracted_files_by_name(
        archive_metadata_service=archive_metadata_service,
        archive_record=archive_record,
    )
    selection_progress_session = (
        progress_reporter.start(
            total_items=len(processable_members),
            fields=[
                ProgressField(key="selected", label="selected", color="green"),
                ProgressField(key="skipped", label="skipped", color="blue"),
            ],
            update_every=10,
        )
        if progress_reporter is not None
        else None
    )
    parse_progress_session = (
        progress_reporter.start(
            total_items=len(processable_members),
            fields=[
                ProgressField(key="parsed", label="parsed", color="green"),
                ProgressField(key="failed", label="failed", color="red"),
            ],
            update_every=10,
        )
        if progress_reporter is not None
        else None
    )
    parse_persistence_state = _StreamingParsePersistenceState(
        started=started,
        nonprofit_persistence_service=nonprofit_persistence_service,
        archive_metadata_service=archive_metadata_service,
        archive_id=getattr(archive_record, "archive_id", None),
        persist_batch_size=resolved_persist_batch_size,
    )
    parse_started_at = time.perf_counter()
    max_pending_tasks = max(1, parser_workers * 4)
    archive_reader_pool = _ThreadLocalArchiveReaderPool(archive_path=archive_path)
    try:
        worker_states = _run_queued_xml_member_workers(
            archive_path=archive_path,
            archive_identity=context.archive_identity,
            source_object=source_object,
            processable_members=processable_members,
            existing_extracted_files_by_name=existing_extracted_files_by_name,
            archive_reader_pool=archive_reader_pool,
            worker_count=parser_workers,
            queue_maxsize=max_pending_tasks,
            xml_error_handler=xml_error_handler,
            selection_progress_session=selection_progress_session,
            parse_progress_session=parse_progress_session,
            started=started,
            nonprofit_persistence_service=nonprofit_persistence_service,
            archive_metadata_service=archive_metadata_service,
            archive_id=getattr(archive_record, "archive_id", None),
            persist_batch_size=resolved_persist_batch_size,
        )
        _merge_worker_parse_persistence_states(
            target=parse_persistence_state,
            worker_states=worker_states,
        )
        if parse_progress_session is not None:
            parse_progress_session.set_total_items(parse_persistence_state.parse_task_count)
    except zipfile.BadZipFile as exc:
        raise MonthlyIngestMalformedArchiveError(f"bad zip archive at {archive_path}") from exc
    finally:
        archive_reader_pool.close_all()
        if selection_progress_session is not None:
            selection_progress_session.complete()
        if parse_progress_session is not None:
            parse_progress_session.complete()
    unzip_elapsed_ms = parse_persistence_state.worker_extract_elapsed_ms
    selection_elapsed_ms = parse_persistence_state.worker_selection_elapsed_ms
    hash_elapsed_ms = parse_persistence_state.worker_hash_elapsed_ms
    _log_structured(
        "monthly_ingest.worker.extracted",
        job_id=context.job_id,
        extracted_member_count=parse_persistence_state.extracted_member_count,
        selected_member_count=parse_persistence_state.selected_member_count,
        skipped_unchanged_member_count=parse_persistence_state.skipped_unchanged_member_count,
        archive_checksum=checksum,
        archive_size_bytes=size,
    )

    _log_structured(
        "monthly_ingest.worker.records_parse_about_to_start",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        record_count=parse_persistence_state.parse_task_count,
        selected_member_count=parse_persistence_state.selected_member_count,
    )
    if parse_persistence_state.parse_task_count:
        parse_elapsed_ms = _elapsed_ms(parse_started_at)
        ingest_result = _streaming_parse_persistence_result(parse_persistence_state)
        nonprofit_persistence_elapsed_ms = parse_persistence_state.nonprofit_persistence_elapsed_ms
        extracted_file_metadata_elapsed_ms = parse_persistence_state.extracted_file_metadata_elapsed_ms
    else:
        ingest_result = {
            "status": "success",
            "records_processed": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "records": [],
            "artifact_paths": None,
            "nonprofit_persistence": None,
        }
        parse_elapsed_ms = 0
        nonprofit_persistence_elapsed_ms = 0
        extracted_file_metadata_elapsed_ms = 0

    _log_structured(
        "monthly_ingest.worker.records_parse_completed",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        parsed_count=int(ingest_result.get("parsed_count") or 0),
        failed_count=int(ingest_result.get("failed_count") or 0),
        records_processed=int(ingest_result.get("records_processed") or 0),
    )

    completed_at = datetime.now(timezone.utc)
    total_elapsed_ms = _elapsed_ms(total_started_at)
    persistence_elapsed_ms = nonprofit_persistence_elapsed_ms + extracted_file_metadata_elapsed_ms
    parse_files_per_second = _items_per_second(int(ingest_result.get("parsed_count") or 0), parse_elapsed_ms)
    persist_records_per_second = _items_per_second(int(ingest_result.get("records_processed") or 0), persistence_elapsed_ms)
    worker_parallelism_ratio = _ratio(state=parse_persistence_state.worker_total_elapsed_ms, total=parse_elapsed_ms)
    average_persist_batch_size = _ratio(
        state=int(ingest_result.get("records_processed") or 0),
        total=parse_persistence_state.persist_batch_count,
    )
    _log_structured(
        "monthly_ingest.worker.stage_timings",
        level=logging.INFO,
        job_id=context.job_id,
        archive_path=archive_path,
        unzip_duration_ms=unzip_elapsed_ms,
        selection_duration_ms=selection_elapsed_ms,
        hash_duration_ms=hash_elapsed_ms,
        parse_duration_ms=parse_elapsed_ms,
        nonprofit_persistence_duration_ms=nonprofit_persistence_elapsed_ms,
        extracted_file_metadata_duration_ms=extracted_file_metadata_elapsed_ms,
        persistence_duration_ms=persistence_elapsed_ms,
        parse_wait_duration_ms=parse_persistence_state.parse_wait_elapsed_ms,
        worker_read_duration_ms=parse_persistence_state.worker_read_elapsed_ms,
        worker_parse_duration_ms=parse_persistence_state.worker_parse_elapsed_ms,
        worker_total_duration_ms=parse_persistence_state.worker_total_elapsed_ms,
        worker_parallelism_ratio=worker_parallelism_ratio,
        total_duration_ms=total_elapsed_ms,
        extracted_member_count=parse_persistence_state.extracted_member_count,
        selected_member_count=parse_persistence_state.selected_member_count,
        parsed_count=int(ingest_result.get("parsed_count") or 0),
        failed_count=int(ingest_result.get("failed_count") or 0),
        skipped_unchanged_member_count=parse_persistence_state.skipped_unchanged_member_count,
        parse_files_per_second=parse_files_per_second,
        persist_records_per_second=persist_records_per_second,
        persist_batch_count=parse_persistence_state.persist_batch_count,
        average_persist_batch_size=average_persist_batch_size,
        max_persist_batch_size=parse_persistence_state.max_persist_batch_size,
        xml_parser_workers=parser_workers,
    )
    return {
        "status": str(ingest_result.get("status") or "failed"),
        "job_id": context.job_id,
        "correlation_id": context.correlation_id,
        "records_processed": int(ingest_result.get("records_processed") or 0),
        "parsed_count": int(ingest_result.get("parsed_count") or 0),
        "failed_count": int(ingest_result.get("failed_count") or 0),
        "records": ingest_result.get("records") or [],
        "skipped_unchanged_member_count": parse_persistence_state.skipped_unchanged_member_count,
        "archive_size_bytes": size,
        "archive_checksum_sha256": checksum,
        "selected_member_count": parse_persistence_state.selected_member_count,
        "extracted_member_count": parse_persistence_state.extracted_member_count,
        "artifact_paths": None,
        "completed_at": completed_at.isoformat(),
    }


def _processable_archive_members(*, archive_path: str, max_xml_file_size_bytes: int) -> list[tuple[int, zipfile.ZipInfo]]:
    try:
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            return [
                (index, member)
                for index, member in enumerate(archive.infolist())
                if not member.is_dir()
                and member.filename.lower().endswith(".xml")
                and member.file_size <= max_xml_file_size_bytes
            ]
    except zipfile.BadZipFile as exc:
        raise MonthlyIngestMalformedArchiveError(f"bad zip archive at {archive_path}") from exc


def _extract_zip_member_to_workdir(
    *,
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    member_index: int,
    workdir: str,
) -> LocalExtractedXmlMember:
    Path(workdir).mkdir(parents=True, exist_ok=True)
    member_name = member.filename.replace("\\", "/")
    output_name = f"{member_index:05d}_{Path(member_name).name}"
    output_path = Path(workdir) / output_name
    with archive.open(member, mode="r") as source_handle, output_path.open("wb") as target_handle:
        while True:
            chunk = source_handle.read(64 * 1024)
            if not chunk:
                break
            target_handle.write(chunk)
    return LocalExtractedXmlMember(
        member_name=member_name,
        local_path=str(output_path),
        content_length=output_path.stat().st_size,
    )


def _read_zip_member_bytes(
    *,
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
) -> bytes:
    payload = bytearray()
    with archive.open(member, mode="r") as source_handle:
        while True:
            chunk = source_handle.read(64 * 1024)
            if not chunk:
                break
            payload.extend(chunk)
    return bytes(payload)


def _read_zip_member_bytes_from_archive_path(
    *,
    archive_reader_pool: _ThreadLocalArchiveReaderPool | None,
    archive_path: str,
    member_index: int,
    expected_member_name: str,
) -> tuple[LocalExtractedXmlMember, bytes]:
    if archive_reader_pool is None:
        archive_reader_pool = _ThreadLocalArchiveReaderPool(archive_path=archive_path)
    reader_entry = archive_reader_pool.current()
    try:
        member = reader_entry.members[member_index]
    except IndexError as exc:
        raise MonthlyIngestMalformedArchiveError(
            f"zip archive member index {member_index} missing at {archive_path}"
        ) from exc
    member_name = member.filename.replace("\\", "/")
    if member_name != expected_member_name:
        raise MonthlyIngestMalformedArchiveError(
            f"zip archive member mismatch at index {member_index}: expected {expected_member_name}, found {member_name}"
        )
    xml_bytes = _read_zip_member_bytes(
        archive=reader_entry.archive,
        member=member,
    )
    return (
        LocalExtractedXmlMember(
            member_name=member_name,
            local_path=None,
            content_length=len(xml_bytes),
        ),
        xml_bytes,
    )


def _build_local_xml_parse_task(
    *,
    member: LocalExtractedXmlMember,
    archive_identity: str,
    source_object: MonthlyIngestSourceObject,
    xml_bytes: bytes,
    xml_content_hash: str | None = None,
) -> _LocalXmlParseTask | None:
    irs_object_id = _object_id_from_member_name(member.member_name)
    if not irs_object_id:
        return None
    xml_reference = _xml_reference(archive_identity=archive_identity, member_name=member.member_name)
    return _LocalXmlParseTask(
        member=member,
        source_reference=xml_reference,
        xml_bytes=xml_bytes,
        xml_content_hash=xml_content_hash,
        record=Form990IndexRecord(
            ein=None,
            tax_year=source_object.source_year,
            filing_date=None,
            return_type="990",
            irs_object_id=irs_object_id,
            xml_url=xml_reference,
            source_year=source_object.source_year,
            source_archive=source_object.source_archive_key,
            source_signature=None,
        ),
    )


def _process_local_xml_member_task(
    task: _LocalXmlMemberTask,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None,
) -> _ParsedXmlMemberResult:
    task_started_at = time.perf_counter()
    extract_duration_ms = 0
    hash_duration_ms = 0
    selection_duration_ms = 0
    extracted_member, xml_bytes = _read_zip_member_bytes_from_archive_path(
        archive_reader_pool=task.archive_reader_pool,
        archive_path=task.archive_path,
        member_index=task.member_index,
        expected_member_name=task.member_name,
    )
    extract_duration_ms = _elapsed_ms(task_started_at)
    hash_started_at = time.perf_counter()
    content_hash = _hash_xml_bytes(xml_bytes)
    hash_duration_ms = _elapsed_ms(hash_started_at)
    selection_started_at = time.perf_counter()
    if task.existing_content_hash and task.existing_content_hash == content_hash:
        selection_duration_ms = _elapsed_ms(selection_started_at)
        return _ParsedXmlMemberResult(
            member=extracted_member,
            content_hash=content_hash,
            was_skipped_unchanged=True,
            worker_extract_duration_ms=extract_duration_ms,
            worker_hash_duration_ms=hash_duration_ms,
            worker_selection_duration_ms=selection_duration_ms,
            worker_total_duration_ms=_elapsed_ms(task_started_at),
        )
    parse_task = _build_local_xml_parse_task(
        member=extracted_member,
        archive_identity=task.archive_identity,
        source_object=task.source_object,
        xml_bytes=xml_bytes,
        xml_content_hash=content_hash,
    )
    selection_duration_ms = _elapsed_ms(selection_started_at)
    if parse_task is None:
        return _ParsedXmlMemberResult(
            member=extracted_member,
            content_hash=content_hash,
            was_selected=True,
            worker_extract_duration_ms=extract_duration_ms,
            worker_hash_duration_ms=hash_duration_ms,
            worker_selection_duration_ms=selection_duration_ms,
            worker_total_duration_ms=_elapsed_ms(task_started_at),
        )
    parsed_result = _parse_local_xml_parse_task(parse_task, xml_error_handler)
    return replace(
        parsed_result,
        content_hash=content_hash,
        was_selected=True,
        worker_extract_duration_ms=extract_duration_ms,
        worker_hash_duration_ms=hash_duration_ms,
        worker_selection_duration_ms=selection_duration_ms,
        worker_total_duration_ms=_elapsed_ms(task_started_at),
    )


def _parse_local_xml_parse_task(
    task: _LocalXmlParseTask,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None,
) -> _ParsedXmlMemberResult:
    task_started_at = time.perf_counter()
    read_duration_ms = 0
    parse_duration_ms = 0
    try:
        record_error_handler = (
            (lambda record, exc, status: _notify_xml_error(record=record, exc=exc, status=status, handler=xml_error_handler))
            if xml_error_handler is not None
            else None
        )
        try:
            parse_started_at = time.perf_counter()
            parsed_record = parse_form990_record_xml(
                task.record,
                xml_bytes=task.xml_bytes,
                source_reference=task.source_reference,
                xml_content_hash=task.xml_content_hash,
                record_error_handler=record_error_handler,
            )
            parse_duration_ms = _elapsed_ms(parse_started_at)
            return _ParsedXmlMemberResult(
                member=task.member,
                filing_record=parsed_record.filing_record,
                relationship_records=parsed_record.relationship_records,
                canonical_raw_filing_record=parsed_record.canonical_raw_filing_record,
                content_hash=task.xml_content_hash,
                was_selected=True,
                worker_read_duration_ms=read_duration_ms,
                worker_parse_duration_ms=parse_duration_ms,
                worker_total_duration_ms=_elapsed_ms(task_started_at),
            )
        except Exception as exc:
            parse_duration_ms = _elapsed_ms(task_started_at) - read_duration_ms
            if record_error_handler is not None:
                record_error_handler(task.record, exc, Form990ParseStatus.PARSE_ERROR.value)
            return _ParsedXmlMemberResult(
                member=task.member,
                filing_record=Form990MetadataRecord(
                    ein=task.record.ein,
                    tax_year=task.record.tax_year,
                    tax_period_begin=None,
                    tax_period_end=None,
                    filing_date=task.record.filing_date,
                    amended_return=None,
                    return_type=task.record.return_type,
                    irs_object_id=task.record.irs_object_id,
                    xml_source_reference=task.source_reference,
                    raw_file_reference=None,
                    parse_status=Form990ParseStatus.PARSE_ERROR,
                    parse_error=str(exc),
                ).to_dict(),
                content_hash=task.xml_content_hash,
                was_selected=True,
                worker_read_duration_ms=max(read_duration_ms, 0),
                worker_parse_duration_ms=max(parse_duration_ms, 0),
                worker_total_duration_ms=_elapsed_ms(task_started_at),
            )
    finally:
        pass


def _run_queued_xml_member_workers(
    *,
    archive_path: str,
    archive_identity: str,
    source_object: MonthlyIngestSourceObject,
    processable_members: list[tuple[int, zipfile.ZipInfo]],
    existing_extracted_files_by_name: Mapping[str, Any],
    archive_reader_pool: _ThreadLocalArchiveReaderPool,
    worker_count: int,
    queue_maxsize: int,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None,
    selection_progress_session: Any | None,
    parse_progress_session: Any | None,
    started: datetime,
    nonprofit_persistence_service: Any | None,
    archive_metadata_service: Any | None,
    archive_id: int | None,
    persist_batch_size: int,
) -> list[_StreamingParsePersistenceState]:
    task_queue: queue.Queue[Any] = queue.Queue(maxsize=max(1, queue_maxsize))
    stop_sentinel = object()
    stop_event = threading.Event()
    progress_lock = threading.Lock()
    result_lock = threading.Lock()
    worker_states: list[_StreamingParsePersistenceState] = []
    worker_errors: list[BaseException] = []

    def worker_target() -> None:
        worker_failed = False
        state = _StreamingParsePersistenceState(
            started=started,
            nonprofit_persistence_service=nonprofit_persistence_service,
            archive_metadata_service=archive_metadata_service,
            archive_id=archive_id,
            persist_batch_size=persist_batch_size,
        )
        try:
            while True:
                task = task_queue.get()
                try:
                    if task is stop_sentinel:
                        return
                    result = _process_queued_xml_member_task(task, xml_error_handler)
                    _record_processed_member_result(
                        result=result,
                        selection_progress_session=selection_progress_session,
                        parse_progress_session=parse_progress_session,
                        progress_lock=progress_lock,
                        state=state,
                    )
                finally:
                    task_queue.task_done()
        except BaseException as exc:
            worker_failed = True
            stop_event.set()
            with result_lock:
                worker_errors.append(exc)
        finally:
            if not worker_failed:
                try:
                    _flush_streaming_parse_result_batch(state)
                except BaseException as exc:
                    stop_event.set()
                    with result_lock:
                        worker_errors.append(exc)
            with result_lock:
                worker_states.append(state)

    workers = [
        threading.Thread(target=worker_target, name=f"form990-xml-{index + 1}", daemon=True)
        for index in range(max(1, worker_count))
    ]
    for worker in workers:
        worker.start()

    try:
        for index, member in processable_members:
            if stop_event.is_set():
                break
            member_name = member.filename.replace("\\", "/")
            existing_content_hash = (
                str(getattr(existing_extracted_files_by_name.get(member_name), "content_hash", "") or "").strip()
                or None
            )
            task = _QueuedXmlMemberTask(
                archive_path=archive_path,
                member_index=index,
                member_name=member_name,
                archive_identity=archive_identity,
                source_object=source_object,
                existing_content_hash=existing_content_hash,
                archive_reader_pool=archive_reader_pool,
            )
            _put_worker_queue_item(
                task_queue=task_queue,
                item=task,
                stop_event=stop_event,
            )
    finally:
        if stop_event.is_set():
            _drain_worker_queue(task_queue)
        for _ in workers:
            _put_worker_queue_item(
                task_queue=task_queue,
                item=stop_sentinel,
                stop_event=None,
            )
        for worker in workers:
            worker.join()

    if worker_errors:
        raise worker_errors[0]
    return worker_states


def _put_worker_queue_item(
    *,
    task_queue: queue.Queue[Any],
    item: Any,
    stop_event: threading.Event | None,
) -> None:
    while True:
        if stop_event is not None and stop_event.is_set():
            return
        try:
            task_queue.put(item, timeout=0.1)
            return
        except queue.Full:
            continue


def _drain_worker_queue(task_queue: queue.Queue[Any]) -> None:
    while True:
        try:
            task_queue.get_nowait()
        except queue.Empty:
            return
        else:
            task_queue.task_done()


def _process_queued_xml_member_task(
    task: _QueuedXmlMemberTask,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None,
) -> _ParsedXmlMemberResult:
    return _process_local_xml_member_task(
        _LocalXmlMemberTask(
            archive_path=task.archive_path,
            extracted_workdir="",
            member_index=task.member_index,
            member_name=task.member_name,
            archive_identity=task.archive_identity,
            source_object=task.source_object,
            existing_content_hash=task.existing_content_hash,
            archive_reader_pool=task.archive_reader_pool,
        ),
        xml_error_handler,
    )


def _record_processed_member_result(
    *,
    result: _ParsedXmlMemberResult,
    selection_progress_session: Any | None,
    parse_progress_session: Any | None,
    progress_lock: threading.Lock,
    state: _StreamingParsePersistenceState,
) -> None:
    state.extracted_member_count += 1
    if result.was_selected:
        state.selected_member_count += 1
    if result.was_skipped_unchanged:
        state.skipped_unchanged_member_count += 1
    state.worker_extract_elapsed_ms += int(result.worker_extract_duration_ms or 0)
    state.worker_hash_elapsed_ms += int(result.worker_hash_duration_ms or 0)
    state.worker_selection_elapsed_ms += int(result.worker_selection_duration_ms or 0)
    state.worker_read_elapsed_ms += int(result.worker_read_duration_ms or 0)
    state.worker_parse_elapsed_ms += int(result.worker_parse_duration_ms or 0)
    state.worker_total_elapsed_ms += int(result.worker_total_duration_ms or 0)
    if selection_progress_session is not None:
        with progress_lock:
            selection_progress_session.item_completed(
                _progress_increments_for_member(result),
                last_item=Path(result.member.member_name).name,
            )
    if result.filing_record is not None:
        state.parse_task_count += 1
        state.parsed_result_batch.append(result)
        if parse_progress_session is not None:
            with progress_lock:
                parse_progress_session.item_completed(
                    _progress_increments_for_filing(result.filing_record),
                    last_item=Path(result.member.member_name).name,
                )
    if len(state.parsed_result_batch) >= state.persist_batch_size:
        _flush_streaming_parse_result_batch(state)


def _merge_worker_parse_persistence_states(
    *,
    target: _StreamingParsePersistenceState,
    worker_states: list[_StreamingParsePersistenceState],
) -> None:
    for state in worker_states:
        target.aggregated_records.extend(state.aggregated_records)
        target.parsed_count += state.parsed_count
        target.failed_count += state.failed_count
        target.records_processed += state.records_processed
        target.extracted_member_count += state.extracted_member_count
        target.selected_member_count += state.selected_member_count
        target.skipped_unchanged_member_count += state.skipped_unchanged_member_count
        target.nonprofit_persistence_elapsed_ms += state.nonprofit_persistence_elapsed_ms
        target.extracted_file_metadata_elapsed_ms += state.extracted_file_metadata_elapsed_ms
        target.worker_extract_elapsed_ms += state.worker_extract_elapsed_ms
        target.worker_hash_elapsed_ms += state.worker_hash_elapsed_ms
        target.worker_selection_elapsed_ms += state.worker_selection_elapsed_ms
        target.worker_read_elapsed_ms += state.worker_read_elapsed_ms
        target.worker_parse_elapsed_ms += state.worker_parse_elapsed_ms
        target.worker_total_elapsed_ms += state.worker_total_elapsed_ms
        target.parse_wait_elapsed_ms += state.parse_wait_elapsed_ms
        target.persist_batch_count += state.persist_batch_count
        target.max_persist_batch_size = max(target.max_persist_batch_size, state.max_persist_batch_size)
        target.parse_task_count += state.parse_task_count


def _flush_streaming_parse_result_batch(state: _StreamingParsePersistenceState) -> None:
    if not state.parsed_result_batch:
        return
    batch_size = len(state.parsed_result_batch)
    state.persist_batch_count += 1
    state.max_persist_batch_size = max(state.max_persist_batch_size, batch_size)
    nonprofit_persistence_started_at = time.perf_counter()
    filing_records = [result.filing_record for result in state.parsed_result_batch]
    canonical_raw_filing_records = [
        result.canonical_raw_filing_record
        for result in state.parsed_result_batch
        if result.canonical_raw_filing_record is not None
    ]
    ingest_result = finalize_form990_filing_records(
        filing_records,
        started=state.started,
        nonprofit_persistence_service=state.nonprofit_persistence_service,
        canonical_raw_filing_records=canonical_raw_filing_records,
    ).to_dict()
    state.nonprofit_persistence_elapsed_ms += _elapsed_ms(nonprofit_persistence_started_at)
    state.extracted_file_metadata_elapsed_ms += _persist_extracted_file_result_batch(
        archive_metadata_service=state.archive_metadata_service,
        archive_id=state.archive_id,
        parsed_result_batch=state.parsed_result_batch,
    )
    state.aggregated_records.extend(ingest_result.get("records") or [])
    state.parsed_count += int(ingest_result.get("parsed_count") or 0)
    state.failed_count += int(ingest_result.get("failed_count") or 0)
    state.records_processed += int(ingest_result.get("records_processed") or 0)
    state.parsed_result_batch.clear()


def _streaming_parse_persistence_result(state: _StreamingParsePersistenceState) -> dict[str, Any]:
    status = "success" if state.failed_count == 0 else "partial_success"
    return {
        "status": status,
        "records_processed": state.records_processed,
        "parsed_count": state.parsed_count,
        "failed_count": state.failed_count,
        "records": state.aggregated_records,
        "artifact_paths": None,
        "nonprofit_persistence": None,
    }


def _progress_increments_for_member(result: _ParsedXmlMemberResult) -> dict[str, int]:
    if result.was_skipped_unchanged:
        return {"skipped": 1}
    if result.was_selected:
        return {"selected": 1}
    return {}


def _progress_increments_for_filing(filing_record: Mapping[str, Any]) -> dict[str, int]:
    status = str(filing_record.get("parse_status") or "").strip().lower()
    if status == Form990ParseStatus.PARSED.value:
        return {"parsed": 1}
    if status in {Form990ParseStatus.MALFORMED_XML.value, Form990ParseStatus.PARSE_ERROR.value}:
        return {"failed": 1}
    return {}


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _items_per_second(count: int, duration_ms: int) -> float | None:
    if duration_ms <= 0:
        return None
    return round(float(count) / (float(duration_ms) / 1000.0), 2)


def _ratio(state: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(float(state) / float(total), 2)


def _load_workflow_input(source: Mapping[str, str], contract: EcsTaskRuntimeContract) -> MonthlyIngestWorkflowInput:
    env_errors = contract.validate_environment(source)
    if env_errors:
        raise MonthlyIngestTaskInputError("; ".join(env_errors))
    payload = json.loads(str(source.get("MONTHLY_INGEST_INPUT_JSON") or "{}"))
    if not isinstance(payload, dict):
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_INPUT_JSON must decode to an object")
    return MonthlyIngestWorkflowInput.from_mapping(payload)


def _validate_runtime_environment(source: Mapping[str, str]) -> list[str]:
    return validate_runtime_config(
        required_text={
            "MONTHLY_INGEST_ARCHIVE_IDENTITY": source.get("MONTHLY_INGEST_ARCHIVE_IDENTITY"),
            "MONTHLY_INGEST_ARCHIVE_URL": source.get("MONTHLY_INGEST_ARCHIVE_URL"),
        },
        positive_ints={
            "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES": int(source.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES") or DEFAULT_MAX_XML_FILE_SIZE_BYTES),
        },
    )


def _download_source_archive(*, source_url: str | None) -> tuple[str, str, int]:
    if not source_url:
        raise MonthlyIngestSourceObjectNotFoundError("archive source URL was not provided")
    digest = hashlib.sha256()
    file_handle = tempfile.NamedTemporaryFile(prefix="monthly-ingest-archive-", suffix=".zip", delete=False)
    total_bytes = 0
    try:
        request = urllib.request.Request(source_url, method="GET")
        with urllib.request.urlopen(request, timeout=300) as response:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                file_handle.write(chunk)
                digest.update(chunk)
                total_bytes += len(chunk)
    except Exception as exc:
        file_handle.close()
        Path(file_handle.name).unlink(missing_ok=True)
        raise MonthlyIngestSourceObjectNotFoundError(f"source archive not found at {source_url}") from exc
    finally:
        file_handle.close()
    return file_handle.name, digest.hexdigest(), total_bytes


def _load_local_xml(record: Form990IndexRecord, local_file_lookup: Mapping[str, str]) -> tuple[bytes, str]:
    reference = str(record.xml_url or "").strip()
    local_path = local_file_lookup.get(reference)
    if not local_path:
        raise FileNotFoundError(f"local XML payload not found for {reference or record.irs_object_id}")
    return Path(local_path).read_bytes(), reference


def _delete_local_xml_for_record(record: Form990IndexRecord, local_file_lookup: Mapping[str, str]) -> None:
    reference = str(record.xml_url or "").strip()
    local_path = local_file_lookup.get(reference)
    if local_path:
        _delete_local_xml_file(local_path)


def _cleanup_remaining_local_xml(local_file_lookup: Mapping[str, str]) -> None:
    for local_path in dict(local_file_lookup).values():
        _delete_local_xml_file(local_path)


def _delete_local_xml_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except TypeError:
        target = Path(path)
        if target.exists():
            target.unlink()


def _xml_reference(*, archive_identity: str, member_name: str) -> str:
    return f"workspace://{archive_identity}#{member_name}"


def _resolve_archive_source_url(workflow_input: MonthlyIngestWorkflowInput) -> str | None:
    archive_url = str(workflow_input.archive_url or "").strip()
    if archive_url:
        return archive_url
    schedule_context = workflow_input.schedule_context
    if isinstance(schedule_context, Mapping):
        value = str(schedule_context.get("source_url") or "").strip()
        if value:
            return value
    return None


def _default_archive_source_url(source_object: MonthlyIngestSourceObject) -> str:
    return f"https://apps.irs.gov/pub/epostcard/990/xml/{source_object.source_year}/{source_object.source_filename}"


def _probe_archive_metadata(source_url: str, *, checked_at: datetime) -> Any:
    import urllib.request
    from urllib.error import HTTPError

    request = urllib.request.Request(source_url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return _archive_probe_payload(response=response, source_url=source_url, checked_at=checked_at, method="HEAD")
    except HTTPError as exc:
        if int(exc.code) not in {403, 405, 501}:
            raise
    request = urllib.request.Request(source_url, method="GET")
    request.add_header("Range", "bytes=0-0")
    with urllib.request.urlopen(request, timeout=60) as response:
        response.read(1)
        return _archive_probe_payload(response=response, source_url=source_url, checked_at=checked_at, method="GET")


def _archive_probe_payload(*, response: Any, source_url: str, checked_at: datetime, method: str) -> Any:
    headers = response.headers
    etag = _as_text(headers.get("ETag"))
    return _RuntimeArchiveProbe(
        source_url=source_url,
        resolved_source_url=_as_text(getattr(response, "geturl", lambda: source_url)()),
        etag=etag,
        normalized_etag=_normalize_etag(etag),
        last_modified=_as_text(headers.get("Last-Modified")),
        content_length=_optional_int(headers.get("Content-Length")),
        response_status=int(getattr(response, "status", 200)),
        checked_at=checked_at.isoformat(),
        method_used=method,
    )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_etag(value: Any) -> str | None:
    text = _as_text(value)
    if not text:
        return None
    if text.startswith("W/"):
        text = text[2:].strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    text = text.strip()
    return text or None


def _hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _notify_xml_error(
    *,
    record: Form990IndexRecord,
    exc: Exception,
    status: str,
    handler: Callable[[str | None, Exception, str], None] | None,
) -> None:
    if handler is None:
        return
    reference = str(record.xml_url or "").strip()
    member_name = reference.split("#", 1)[1] if "#" in reference else None
    handler(member_name or record.irs_object_id, exc, status)


def _datetime_or_now(value: Any) -> datetime:
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _list_existing_extracted_files_by_name(
    *,
    archive_metadata_service: Any | None,
    archive_record: Any | None,
) -> dict[str, Any]:
    if archive_metadata_service is None or archive_record is None:
        return {}
    list_method = getattr(archive_metadata_service, "list_extracted_files_for_archive", None)
    if not callable(list_method):
        return {}
    records = list_method(archive_record.archive_id) or []
    return {
        str(getattr(record, "filename", "") or "").strip(): record
        for record in records
        if str(getattr(record, "filename", "") or "").strip()
    }


def _persist_extracted_file_result_batch(
    *,
    archive_metadata_service: Any | None,
    archive_id: int | None,
    parsed_result_batch: list[_ParsedXmlMemberResult],
) -> int:
    if archive_metadata_service is None or archive_id is None or not parsed_result_batch:
        return 0
    extracted_file_persistence_started_at = time.perf_counter()
    now = datetime.now(timezone.utc)
    batch_records = [
        {
            "filename": result.member.member_name,
            "content_hash": result.content_hash,
            "parse_status": str(result.filing_record.get("parse_status") or "parsed").strip() or "parsed",
            "error_message": _as_text(result.filing_record.get("parse_error")),
        }
        for result in parsed_result_batch
        if result.filing_record is not None
    ]
    if not batch_records:
        return _elapsed_ms(extracted_file_persistence_started_at)
    batch_upsert = getattr(archive_metadata_service, "upsert_extracted_files_batch", None)
    if callable(batch_upsert):
        batch_upsert(
            archive_id=archive_id,
            records=batch_records,
            parsed_at=now,
        )
        return _elapsed_ms(extracted_file_persistence_started_at)
    for result in parsed_result_batch:
        if result.filing_record is None:
            continue
        member = result.member
        filing = result.filing_record
        parse_status = str(filing.get("parse_status") or "parsed").strip() or "parsed"
        error_message = _as_text(filing.get("parse_error"))
        archive_metadata_service.upsert_extracted_file(
            archive_id=archive_id,
            filename=member.member_name,
            content_hash=result.content_hash,
            parse_status=parse_status,
            parsed_at=now,
            error_message=error_message,
        )
    return _elapsed_ms(extracted_file_persistence_started_at)


def _object_id_from_member_name(member_name: str) -> str:
    name = str(member_name or "").strip()
    if not name:
        return ""
    base = Path(name).name
    return base.rsplit(".", 1)[0].strip() if "." in base else base.strip()


def _record_signature(
    *,
    irs_object_id: str,
    xml_bytes: bytes,
    archive_checksum: str,
    source_year: str,
    source_archive_key: str,
) -> str:
    payload = "|".join(
        [
            irs_object_id,
            archive_checksum,
            source_year,
            source_archive_key,
            hashlib.sha256(xml_bytes).hexdigest(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _hash_local_xml_file(path: str) -> str:
    return hash_local_xml_file(path)


def _hash_xml_bytes(xml_bytes: bytes) -> str:
    return hashlib.sha256(xml_bytes).hexdigest()


def _resolve_form990_persist_batch_size(source_env: Mapping[str, str]) -> int:
    raw_value = source_env.get("FORM990_PERSIST_BATCH_SIZE")
    if raw_value is None or str(raw_value).strip() == "":
        return DEFAULT_FORM990_PERSIST_BATCH_SIZE
    try:
        return _clamp_persist_batch_size(int(str(raw_value).strip()))
    except (TypeError, ValueError):
        return DEFAULT_FORM990_PERSIST_BATCH_SIZE


def _clamp_persist_batch_size(value: int | None) -> int:
    if value is None:
        return DEFAULT_FORM990_PERSIST_BATCH_SIZE
    return max(1, min(MAX_FORM990_PERSIST_BATCH_SIZE, int(value)))


def _log_structured(event: str, **fields: Any) -> None:
    log_structured(LOGGER, event, **fields)


__all__ = [
    "DEFAULT_FORM990_PERSIST_BATCH_SIZE",
    "DEFAULT_MAX_XML_FILE_SIZE_BYTES",
    "LocalExtractedXmlMember",
    "MonthlyIngestMalformedArchiveError",
    "MonthlyIngestSourceObject",
    "MonthlyIngestSourceObjectNotFoundError",
    "MonthlyIngestTaskInputError",
    "build_local_index_records",
    "extract_zip_xml_members_to_workdir",
    "parse_form990_source_object",
    "process_form990_archive",
    "run_form990_monthly_processing_task",
]

