from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, as_completed, wait
import hashlib
import json
import logging
import os
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from verification.form990.canonical import hash_local_xml_file
from verification.form990.extractors.metadata import extract_metadata_fields
from verification.form990.hardening import classify_error, validate_runtime_config
from verification.form990.ingest import finalize_form990_filing_records, parse_form990_record_xml
from verification.form990.models import Form990IndexRecord, Form990MetadataRecord, Form990ParseStatus
from verification.form990.parser import XmlParseError, parse_xml
from verification.ingest import EcsTaskRuntimeContract, MonthlyIngestWorkflowInput
from verification.ops import ProgressField, ProgressReporter
from verification.runtime_logging import configure_runtime_logging, log_structured
LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)

DEFAULT_MAX_XML_FILE_SIZE_BYTES = 20 * 1024 * 1024


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
    local_path: str
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


@dataclass(frozen=True)
class _LocalXmlParseTask:
    member: LocalExtractedXmlMember
    record: Form990IndexRecord
    source_reference: str
    xml_content_hash: str | None = None


@dataclass(frozen=True)
class _ParsedXmlMemberResult:
    member: LocalExtractedXmlMember
    filing_record: dict[str, Any]
    relationship_records: tuple[dict[str, Any], ...] = ()
    canonical_raw_filing_record: dict[str, Any] | None = None


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

    unzip_duration_seconds = 0.0
    selection_duration_seconds = 0.0
    skipped_unchanged_members = 0
    extracted_members: list[LocalExtractedXmlMember] = []
    selected_members: list[LocalExtractedXmlMember] = []
    member_hashes: dict[str, str] = {}
    parser_workers = max(1, int(xml_parser_workers or 1))
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
    parse_futures: list[Future[_ParsedXmlMemberResult]] = []
    parse_tasks: list[_LocalXmlParseTask] = []
    max_pending_tasks = max(1, parser_workers * 2)
    try:
        with ThreadPoolExecutor(max_workers=parser_workers, thread_name_prefix="form990-xml") as executor:
            with zipfile.ZipFile(archive_path, mode="r") as archive:
                for index, member in processable_members:
                    extract_started_at = time.perf_counter()
                    extracted_member = _extract_zip_member_to_workdir(
                        archive=archive,
                        member=member,
                        member_index=index,
                        workdir=extracted_workdir,
                    )
                    unzip_duration_seconds += time.perf_counter() - extract_started_at
                    extracted_members.append(extracted_member)
                    selection_started_at = time.perf_counter()
                    content_hash = hash_local_xml_file(extracted_member.local_path)
                    member_hashes[extracted_member.member_name] = content_hash
                    if archive_metadata_service is not None and archive_record is not None:
                        existing = archive_metadata_service.get_extracted_file(
                            archive_record.archive_id,
                            extracted_member.member_name,
                        )
                        if existing is not None and str(existing.content_hash or "").strip() == content_hash:
                            skipped_unchanged_members += 1
                            _delete_local_xml_file(extracted_member.local_path)
                            if selection_progress_session is not None:
                                selection_progress_session.item_completed(
                                    {"skipped": 1},
                                    last_item=Path(extracted_member.member_name).name,
                                )
                            selection_duration_seconds += time.perf_counter() - selection_started_at
                            continue
                    selected_members.append(extracted_member)
                    if selection_progress_session is not None:
                        selection_progress_session.item_completed(
                            {"selected": 1},
                            last_item=Path(extracted_member.member_name).name,
                        )
                    parse_task = _build_local_xml_parse_task(
                        member=extracted_member,
                        archive_identity=context.archive_identity,
                        source_object=source_object,
                        xml_content_hash=content_hash,
                    )
                    if parse_task is None:
                        _delete_local_xml_file(extracted_member.local_path)
                        selection_duration_seconds += time.perf_counter() - selection_started_at
                        continue
                    parse_tasks.append(parse_task)
                    parse_futures.append(executor.submit(_parse_local_xml_parse_task, parse_task, xml_error_handler))
                    selection_duration_seconds += time.perf_counter() - selection_started_at
                    while len(parse_futures) - _count_completed_futures(parse_futures) >= max_pending_tasks:
                        wait(parse_futures, return_when=FIRST_COMPLETED)
    except zipfile.BadZipFile as exc:
        raise MonthlyIngestMalformedArchiveError(f"bad zip archive at {archive_path}") from exc
    finally:
        if selection_progress_session is not None:
            selection_progress_session.complete()
    unzip_elapsed_ms = int(unzip_duration_seconds * 1000)
    selection_elapsed_ms = int(selection_duration_seconds * 1000)
    _log_structured(
        "monthly_ingest.worker.extracted",
        job_id=context.job_id,
        extracted_member_count=len(extracted_members),
        selected_member_count=len(selected_members),
        skipped_unchanged_member_count=skipped_unchanged_members,
        archive_checksum=checksum,
        archive_size_bytes=size,
    )

    _log_structured(
        "monthly_ingest.worker.records_parse_about_to_start",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        record_count=len(parse_tasks),
        selected_member_count=len(selected_members),
    )
    parse_started_at = time.perf_counter()
    if parse_tasks:
        progress_session = (
            progress_reporter.start(
                total_items=len(parse_tasks),
                fields=[
                    ProgressField(key="parsed", label="parsed", color="green"),
                    ProgressField(key="failed", label="failed", color="red"),
                ],
                update_every=10,
            )
            if progress_reporter is not None
            else None
        )
        try:
            parsed_results = _collect_parse_results(parse_futures=parse_futures, progress_session=progress_session)
        finally:
            if progress_session is not None:
                progress_session.complete()
        parse_elapsed_ms = _elapsed_ms(parse_started_at)
        nonprofit_persistence_started_at = time.perf_counter()
        filing_records = [result.filing_record for result in parsed_results]
        canonical_raw_filing_records = [
            result.canonical_raw_filing_record
            for result in parsed_results
            if result.canonical_raw_filing_record is not None
        ]
        ingest_result = finalize_form990_filing_records(
            filing_records,
            started=started,
            nonprofit_persistence_service=nonprofit_persistence_service,
            canonical_raw_filing_records=canonical_raw_filing_records,
        ).to_dict()
        nonprofit_persistence_elapsed_ms = _elapsed_ms(nonprofit_persistence_started_at)
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

    _log_structured(
        "monthly_ingest.worker.records_parse_completed",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        parsed_count=int(ingest_result.get("parsed_count") or 0),
        failed_count=int(ingest_result.get("failed_count") or 0),
        records_processed=int(ingest_result.get("records_processed") or 0),
    )

    if archive_metadata_service is not None and archive_record is not None:
        extracted_file_persistence_started_at = time.perf_counter()
        _persist_extracted_file_results(
            archive_metadata_service=archive_metadata_service,
            archive_id=archive_record.archive_id,
            selected_members=selected_members,
            member_hashes=member_hashes,
            ingest_result=ingest_result,
        )
        extracted_file_metadata_elapsed_ms = _elapsed_ms(extracted_file_persistence_started_at)
    else:
        extracted_file_metadata_elapsed_ms = 0

    completed_at = datetime.now(timezone.utc)
    total_elapsed_ms = _elapsed_ms(total_started_at)
    persistence_elapsed_ms = nonprofit_persistence_elapsed_ms + extracted_file_metadata_elapsed_ms
    parse_files_per_second = _items_per_second(int(ingest_result.get("parsed_count") or 0), parse_elapsed_ms)
    persist_records_per_second = _items_per_second(int(ingest_result.get("records_processed") or 0), persistence_elapsed_ms)
    _log_structured(
        "monthly_ingest.worker.stage_timings",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        unzip_duration_ms=unzip_elapsed_ms,
        selection_duration_ms=selection_elapsed_ms,
        parse_duration_ms=parse_elapsed_ms,
        nonprofit_persistence_duration_ms=nonprofit_persistence_elapsed_ms,
        extracted_file_metadata_duration_ms=extracted_file_metadata_elapsed_ms,
        persistence_duration_ms=persistence_elapsed_ms,
        total_duration_ms=total_elapsed_ms,
        extracted_member_count=len(extracted_members),
        selected_member_count=len(selected_members),
        parsed_count=int(ingest_result.get("parsed_count") or 0),
        failed_count=int(ingest_result.get("failed_count") or 0),
        skipped_unchanged_member_count=skipped_unchanged_members,
        parse_files_per_second=parse_files_per_second,
        persist_records_per_second=persist_records_per_second,
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
        "skipped_unchanged_member_count": skipped_unchanged_members,
        "archive_size_bytes": size,
        "archive_checksum_sha256": checksum,
        "selected_member_count": len(selected_members),
        "extracted_member_count": len(extracted_members),
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


def _build_local_xml_parse_task(
    *,
    member: LocalExtractedXmlMember,
    archive_identity: str,
    source_object: MonthlyIngestSourceObject,
    xml_content_hash: str | None = None,
) -> _LocalXmlParseTask | None:
    irs_object_id = _object_id_from_member_name(member.member_name)
    if not irs_object_id:
        return None
    xml_reference = _xml_reference(archive_identity=archive_identity, member_name=member.member_name)
    return _LocalXmlParseTask(
        member=member,
        source_reference=xml_reference,
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


def _parse_local_xml_parse_task(
    task: _LocalXmlParseTask,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None,
) -> _ParsedXmlMemberResult:
    try:
        record_error_handler = (
            (lambda record, exc, status: _notify_xml_error(record=record, exc=exc, status=status, handler=xml_error_handler))
            if xml_error_handler is not None
            else None
        )
        try:
            xml_bytes = Path(task.member.local_path).read_bytes()
            parsed_record = parse_form990_record_xml(
                task.record,
                xml_bytes=xml_bytes,
                source_reference=task.source_reference,
                xml_content_hash=task.xml_content_hash,
                record_error_handler=record_error_handler,
            )
            return _ParsedXmlMemberResult(
                member=task.member,
                filing_record=parsed_record.filing_record,
                relationship_records=parsed_record.relationship_records,
                canonical_raw_filing_record=parsed_record.canonical_raw_filing_record,
            )
        except Exception as exc:
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
            )
    finally:
        _delete_local_xml_file(task.member.local_path)
        # _log_structured(
        #     "form990.ingest.xml_file_deleted",
        #     level=logging.DEBUG,
        #     file_name=Path(task.member.local_path).name,
        #     xml_source_reference=task.source_reference,
        # )


def _collect_parse_results(
    *,
    parse_futures: list[Future[_ParsedXmlMemberResult]],
    progress_session: Any | None,
) -> list[_ParsedXmlMemberResult]:
    parsed_results: list[_ParsedXmlMemberResult] = []
    for future in as_completed(parse_futures):
        result = future.result()
        parsed_results.append(result)
        if progress_session is not None:
            progress_session.item_completed(
                _progress_increments_for_filing(result.filing_record),
                last_item=Path(result.member.member_name).name,
            )
    return parsed_results


def _count_completed_futures(futures: list[Future[Any]]) -> int:
    return sum(1 for future in futures if future.done())


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


def _persist_extracted_file_results(
    *,
    archive_metadata_service: Any,
    archive_id: int,
    selected_members: list[LocalExtractedXmlMember],
    member_hashes: Mapping[str, str],
    ingest_result: Mapping[str, Any],
) -> None:
    result_lookup: dict[str, dict[str, Any]] = {}
    for item in ingest_result.get("records", []):
        if not isinstance(item, dict):
            continue
        reference = str(item.get("xml_source_reference") or "").strip()
        member_name = reference.split("#", 1)[1] if "#" in reference else ""
        if member_name:
            result_lookup[member_name] = item
    now = datetime.now(timezone.utc)
    for member in selected_members:
        filing = result_lookup.get(member.member_name, {})
        parse_status = str(filing.get("parse_status") or "parsed").strip() or "parsed"
        error_message = _as_text(filing.get("parse_error"))
        archive_metadata_service.upsert_extracted_file(
            archive_id=archive_id,
            filename=member.member_name,
            content_hash=member_hashes.get(member.member_name),
            parse_status=parse_status,
            parsed_at=now,
            error_message=error_message,
        )


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


def _log_structured(event: str, **fields: Any) -> None:
    log_structured(LOGGER, event, **fields)


__all__ = [
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

