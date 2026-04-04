from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import boto3
from botocore.exceptions import ClientError

from charity_status.form990.extractors.metadata import extract_metadata_fields
from charity_status.form990.hardening import classify_error, validate_runtime_config
from charity_status.form990.ingest import ingest_form990_records
from charity_status.form990.models import Form990IndexRecord
from charity_status.form990.parser import XmlParseError, parse_xml
from charity_status.ingest import EcsTaskRuntimeContract, MonthlyIngestWorkflowInput
from charity_status.ingest.workflow import (
    workflow_artifact_index_key,
    workflow_job_prefix,
    workflow_manifest_key,
    workflow_summary_key,
)
from charity_status.runtime_logging import configure_runtime_logging, log_structured
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
    source_bucket: str
    source_key: str
    destination_bucket: str
    destination_prefix: str
    job_id: str
    correlation_id: str
    workflow_version: str
    source_url: str | None = None


def run_form990_monthly_processing_task(
    *,
    env: Mapping[str, str] | None = None,
    s3_client: Any | None = None,
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
    source_object = parse_form990_source_object(input_payload.source_key)
    s3 = s3_client or boto3.client("s3")
    artifact_keys = {
        "manifest_s3_key": workflow_manifest_key(input_payload.destination_prefix, input_payload.job_id),
        "artifact_index_s3_key": workflow_artifact_index_key(input_payload.destination_prefix, input_payload.job_id),
        "summary_s3_key": workflow_summary_key(input_payload.destination_prefix, input_payload.job_id),
    }
    processing_context = _ArchiveProcessingContext(
        source_bucket=input_payload.source_bucket,
        source_key=input_payload.source_key,
        destination_bucket=input_payload.destination_bucket,
        destination_prefix=input_payload.destination_prefix,
        job_id=input_payload.job_id,
        correlation_id=input_payload.correlation_id,
        workflow_version=input_payload.workflow_version,
    )
    _log_structured(
        "monthly_ingest.worker.start",
        job_id=input_payload.job_id,
        correlation_id=input_payload.correlation_id,
        source_bucket=input_payload.source_bucket,
        source_key=input_payload.source_key,
        destination_bucket=input_payload.destination_bucket,
        destination_prefix=input_payload.destination_prefix,
    )
    archive_source_url = _resolve_archive_source_url(input_payload)
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
            skipped_result = _write_skipped_artifacts(
                s3_client=s3,
                workflow_input=input_payload,
                artifact_keys=artifact_keys,
                started_at=started_at,
                source_object=source_object,
                archive_reason=archive_probe_outcome.reason,
            )
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
            s3_client=s3,
            bucket=input_payload.source_bucket,
            key=input_payload.source_key,
        )
    except Exception as exc:
        _write_failure_artifacts(
            s3_client=s3,
            workflow_input=input_payload,
            artifact_keys=artifact_keys,
            started_at=started_at,
            exc=exc,
        )
        raise

    if archive_metadata_service is not None and archive_record is None:
        archive_record = archive_metadata_service.ensure_archive_record(
            source_url=archive_source_url or f"s3://{input_payload.source_bucket}/{input_payload.source_key}",
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
                artifact_keys=artifact_keys,
                started_at=started_at,
                s3_client=s3,
                archive_metadata_service=archive_metadata_service,
                archive_record=archive_record,
                nonprofit_persistence_service=nonprofit_persistence_service,
                max_xml_file_size_bytes=int(source.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES") or DEFAULT_MAX_XML_FILE_SIZE_BYTES),
            )
            if str(result.get("status") or "").strip().lower() == "failed":
                raise RuntimeError(f"monthly ingest processing failed with {int(result.get('failed_count') or 0)} failed record(s)")
            if archive_metadata_service is not None and archive_record is not None:
                archive_metadata_service.mark_archive_processed(
                    archive_record.archive_id,
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
                manifest_s3_key=result["manifest_s3_key"],
            )
            return result
    except Exception as exc:
        _write_failure_artifacts(
            s3_client=s3,
            workflow_input=input_payload,
            artifact_keys=artifact_keys,
            started_at=started_at,
            exc=exc,
            source_object=source_object,
        )
        _log_structured(
            "monthly_ingest.worker.failed",
            job_id=input_payload.job_id,
            correlation_id=input_payload.correlation_id,
            error_type=classify_error(exc),
            error=str(exc),
        )
        if archive_metadata_service is not None and archive_record is not None:
            archive_metadata_service.mark_archive_processed(archive_record.archive_id, processed_at=datetime.now(timezone.utc), status="failed")
        raise
    finally:
        try:
            os.unlink(archive_path)
        except OSError:
            pass


def parse_form990_source_object(source_key: str) -> MonthlyIngestSourceObject:
    parts = [part for part in str(source_key or "").strip("/").split("/") if part]
    if len(parts) < 5:
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_SOURCE_KEY must use the raw source contract")
    source_year, source_kind, source_archive_key, source_signature, source_filename = parts[-5:]
    if source_kind != "zip_archive":
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_SOURCE_KEY must reference a zip_archive source object")
    if not source_filename.lower().endswith(".zip"):
        raise MonthlyIngestTaskInputError("MONTHLY_INGEST_SOURCE_KEY must reference a .zip object")
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
    source_bucket: str,
    source_key: str,
    source_object: MonthlyIngestSourceObject,
    archive_checksum: str,
) -> tuple[list[Form990IndexRecord], dict[str, str]]:
    records: list[Form990IndexRecord] = []
    local_file_lookup: dict[str, str] = {}
    for member in extracted_members:
        xml_bytes = Path(member.local_path).read_bytes()
        xml_reference = _xml_reference(source_bucket=source_bucket, source_key=source_key, member_name=member.member_name)
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
    artifact_keys: Mapping[str, str] | None = None,
    archive_checksum: str | None = None,
    archive_size: int | None = None,
    started_at: datetime | None = None,
    s3_client: Any | None = None,
    archive_metadata_service: Any | None = None,
    archive_record: Any | None = None,
    nonprofit_persistence_service: Any | None = None,
    max_xml_file_size_bytes: int = DEFAULT_MAX_XML_FILE_SIZE_BYTES,
    xml_error_handler: Callable[[str | None, Exception, str], None] | None = None,
) -> dict[str, Any]:
    if isinstance(processing_context, _ArchiveProcessingContext):
        context = processing_context
    else:
        context = _ArchiveProcessingContext(
            source_bucket=str(processing_context.get("source_bucket") or "").strip(),
            source_key=str(processing_context.get("source_key") or "").strip(),
            destination_bucket=str(processing_context.get("destination_bucket") or "").strip(),
            destination_prefix=str(processing_context.get("destination_prefix") or "").strip(),
            job_id=str(processing_context.get("job_id") or "").strip(),
            correlation_id=str(processing_context.get("correlation_id") or "").strip(),
            workflow_version=str(processing_context.get("workflow_version") or "").strip(),
            source_url=_as_text(processing_context.get("source_url")),
        )
    started = started_at or datetime.now(timezone.utc)
    persist_runtime_artifacts = bool(
        artifact_keys
        and context.destination_bucket
        and artifact_keys.get("manifest_s3_key")
        and artifact_keys.get("artifact_index_s3_key")
        and artifact_keys.get("summary_s3_key")
    )
    s3 = (s3_client or boto3.client("s3")) if persist_runtime_artifacts else None
    checksum = archive_checksum or _hash_file(archive_path)
    size = int(archive_size) if archive_size is not None else Path(archive_path).stat().st_size
    if archive_metadata_service is not None and archive_record is None:
        archive_record = archive_metadata_service.ensure_archive_record(
            source_url=context.source_url or f"s3://{context.source_bucket}/{context.source_key}",
            filename=source_object.source_filename,
            checked_at=started,
        )
        _log_structured(
            "monthly_ingest.worker.archive_metadata_recorded",
            level=logging.DEBUG,
            job_id=context.job_id,
            archive_id=getattr(archive_record, "archive_id", None),
            source_url=context.source_url or f"s3://{context.source_bucket}/{context.source_key}",
            filename=source_object.source_filename,
        )

    _log_structured(
        "monthly_ingest.worker.unzip_about_to_start",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        extracted_workdir=extracted_workdir,
    )
    extracted_members = extract_zip_xml_members_to_workdir(
        archive_path=archive_path,
        workdir=extracted_workdir,
        max_xml_file_size_bytes=max_xml_file_size_bytes,
    )
    if not extracted_members:
        raise MonthlyIngestMalformedArchiveError("zip archive did not contain any processable XML members")

    selected_members = extracted_members
    skipped_unchanged_members = 0
    member_hashes: dict[str, str] = {}
    if archive_metadata_service is not None and archive_record is not None:
        selected_members = []
        for member in extracted_members:
            content_hash = _hash_local_xml_file(member.local_path)
            member_hashes[member.member_name] = content_hash
            existing = archive_metadata_service.get_extracted_file(archive_record.archive_id, member.member_name)
            if existing is not None and str(existing.content_hash or "").strip() == content_hash:
                skipped_unchanged_members += 1
                _delete_local_xml_file(member.local_path)
                continue
            selected_members.append(member)
    _log_structured(
        "monthly_ingest.worker.extracted",
        job_id=context.job_id,
        extracted_member_count=len(extracted_members),
        selected_member_count=len(selected_members),
        skipped_unchanged_member_count=skipped_unchanged_members,
        archive_checksum=checksum,
        archive_size_bytes=size,
    )

    records, local_file_lookup = build_local_index_records(
        extracted_members=selected_members,
        source_bucket=context.source_bucket,
        source_key=context.source_key,
        source_object=source_object,
        archive_checksum=checksum,
    )
    _log_structured(
        "monthly_ingest.worker.records_parse_about_to_start",
        level=logging.DEBUG,
        job_id=context.job_id,
        archive_path=archive_path,
        record_count=len(records),
        selected_member_count=len(selected_members),
    )
    job_prefix = workflow_job_prefix(context.destination_prefix, context.job_id)
    if records:
        try:
            ingest_result = ingest_form990_records(
                records=records,
                bucket=context.destination_bucket or None,
                raw_prefix=f"{job_prefix}/raw-xml/",
                metadata_prefix=f"{job_prefix}/datasets/metadata/",
                manifest_prefix=f"{job_prefix}/processing/",
                metrics_prefix=f"{job_prefix}/datasets/metrics/",
                governance_prefix=f"{job_prefix}/datasets/governance/",
                quality_prefix=f"{job_prefix}/datasets/quality/",
                relationships_prefix=f"{job_prefix}/datasets/relationships/",
                s3_client=s3,
                download_raw=True,
                record_downloader=lambda record: _load_local_xml(record, local_file_lookup),
                record_cleanup_handler=lambda record: _delete_local_xml_for_record(record, local_file_lookup),
                nonprofit_persistence_service=nonprofit_persistence_service,
                record_error_handler=(
                    (lambda record, exc, status: _notify_xml_error(record=record, exc=exc, status=status, handler=xml_error_handler))
                    if xml_error_handler is not None
                    else None
                ),
                persist_artifacts=persist_runtime_artifacts,
            ).to_dict()
        finally:
            _cleanup_remaining_local_xml(local_file_lookup)
    else:
        ingest_result = {
            "status": "success",
            "records_processed": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "records": [],
            "manifest_s3_key": None,
            "filing_records_s3_key": None,
            "metrics_s3_key": None,
            "governance_s3_key": None,
            "quality_s3_key": None,
            "relationships_s3_key": None,
            "nonprofit_persistence": None,
        }
        _cleanup_remaining_local_xml(local_file_lookup)

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
        _persist_extracted_file_results(
            archive_metadata_service=archive_metadata_service,
            archive_id=archive_record.archive_id,
            selected_members=selected_members,
            member_hashes=member_hashes,
            ingest_result=ingest_result,
        )

    completed_at = datetime.now(timezone.utc)
    artifacts_payload = {
        "job_id": context.job_id,
        "correlation_id": context.correlation_id,
        "archive_source_bucket": context.source_bucket,
        "archive_source_key": context.source_key,
        "archive_size_bytes": size,
        "archive_checksum_sha256": checksum,
        "extracted_member_count": len(extracted_members),
        "selected_member_count": len(selected_members),
        "skipped_unchanged_member_count": skipped_unchanged_members,
        "artifacts": {
            **(dict(artifact_keys or {})),
            "raw_xml_prefix": f"{job_prefix}/raw-xml/",
            "filing_records_s3_key": ingest_result.get("filing_records_s3_key"),
            "metrics_s3_key": ingest_result.get("metrics_s3_key"),
            "governance_s3_key": ingest_result.get("governance_s3_key"),
            "quality_s3_key": ingest_result.get("quality_s3_key"),
            "relationships_s3_key": ingest_result.get("relationships_s3_key"),
            "processing_manifest_s3_key": ingest_result.get("manifest_s3_key"),
        },
    }
    manifest_payload = {
        "status": str(ingest_result.get("status") or "failed"),
        "job_id": context.job_id,
        "correlation_id": context.correlation_id,
        "workflow_version": context.workflow_version,
        "started_at": started.isoformat(),
        "completed_at": completed_at.isoformat(),
        "input": dict(processing_context) if not isinstance(processing_context, _ArchiveProcessingContext) else vars(context),
        "source_object": {
            "bucket": context.source_bucket,
            "key": context.source_key,
            "source_url": context.source_url,
            "archive_size_bytes": size,
            "archive_checksum_sha256": checksum,
            "source_year": source_object.source_year,
            "source_kind": source_object.source_kind,
            "source_archive_key": source_object.source_archive_key,
            "source_signature": source_object.source_signature,
            "source_filename": source_object.source_filename,
        },
        "extraction": {
            "extracted_member_count": len(extracted_members),
            "selected_member_count": len(selected_members),
            "skipped_unchanged_member_count": skipped_unchanged_members,
            "members": [item.member_name for item in extracted_members[:25]],
        },
        "result": ingest_result,
        "artifacts": artifacts_payload["artifacts"],
    }
    summary_payload = {
        "status": str(ingest_result.get("status") or "failed"),
        "job_id": context.job_id,
        "correlation_id": context.correlation_id,
        "workflow_version": context.workflow_version,
        "records_processed": int(ingest_result.get("records_processed") or 0),
        "parsed_count": int(ingest_result.get("parsed_count") or 0),
        "failed_count": int(ingest_result.get("failed_count") or 0),
        "archive_size_bytes": size,
        "archive_checksum_sha256": checksum,
        "extracted_member_count": len(extracted_members),
        "selected_member_count": len(selected_members),
        "skipped_unchanged_member_count": skipped_unchanged_members,
        "processing_manifest_s3_key": ingest_result.get("manifest_s3_key"),
        "artifact_index_s3_key": (artifact_keys or {}).get("artifact_index_s3_key"),
        "completed_at": completed_at.isoformat(),
    }
    if persist_runtime_artifacts and s3 is not None and artifact_keys is not None:
        _put_json_artifact(s3, context.destination_bucket, artifact_keys["artifact_index_s3_key"], artifacts_payload)
        _put_json_artifact(s3, context.destination_bucket, artifact_keys["manifest_s3_key"], manifest_payload)
        _put_json_artifact(s3, context.destination_bucket, artifact_keys["summary_s3_key"], summary_payload)
    return {
        "status": str(ingest_result.get("status") or "failed"),
        "job_id": context.job_id,
        "correlation_id": context.correlation_id,
        "manifest_s3_key": (artifact_keys or {}).get("manifest_s3_key"),
        "artifact_index_s3_key": (artifact_keys or {}).get("artifact_index_s3_key"),
        "summary_s3_key": (artifact_keys or {}).get("summary_s3_key"),
        "processing_manifest_s3_key": ingest_result.get("manifest_s3_key"),
        "records_processed": int(ingest_result.get("records_processed") or 0),
        "parsed_count": int(ingest_result.get("parsed_count") or 0),
        "failed_count": int(ingest_result.get("failed_count") or 0),
        "skipped_unchanged_member_count": skipped_unchanged_members,
        "completed_at": completed_at.isoformat(),
    }


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
            "MONTHLY_INGEST_SOURCE_BUCKET": source.get("MONTHLY_INGEST_SOURCE_BUCKET"),
            "MONTHLY_INGEST_SOURCE_KEY": source.get("MONTHLY_INGEST_SOURCE_KEY"),
            "MONTHLY_INGEST_DESTINATION_BUCKET": source.get("MONTHLY_INGEST_DESTINATION_BUCKET"),
            "MONTHLY_INGEST_DESTINATION_PREFIX": source.get("MONTHLY_INGEST_DESTINATION_PREFIX"),
        },
        positive_ints={
            "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES": int(source.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES") or DEFAULT_MAX_XML_FILE_SIZE_BYTES),
        },
    )


def _download_source_archive(*, s3_client: Any, bucket: str, key: str) -> tuple[str, str, int]:
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code") or "")
        if error_code in {"NoSuchKey", "404", "NotFound"}:
            raise MonthlyIngestSourceObjectNotFoundError(f"source object not found at s3://{bucket}/{key}") from exc
        raise
    except KeyError as exc:
        raise MonthlyIngestSourceObjectNotFoundError(f"source object not found at s3://{bucket}/{key}") from exc

    digest = hashlib.sha256()
    file_handle = tempfile.NamedTemporaryFile(prefix="monthly-ingest-archive-", suffix=".zip", delete=False)
    total_bytes = 0
    body = response["Body"]
    try:
        while True:
            chunk = body.read(64 * 1024)
            if not chunk:
                break
            file_handle.write(chunk)
            digest.update(chunk)
            total_bytes += len(chunk)
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


def _xml_reference(*, source_bucket: str, source_key: str, member_name: str) -> str:
    if source_bucket:
        return f"s3://{source_bucket}/{source_key}#{member_name}"
    return f"local://{source_key}#{member_name}"


def _resolve_archive_source_url(workflow_input: MonthlyIngestWorkflowInput) -> str | None:
    schedule_context = workflow_input.schedule_context
    if isinstance(schedule_context, Mapping):
        value = str(schedule_context.get("source_url") or "").strip()
        if value:
            return value
    return f"s3://{workflow_input.source_bucket}/{workflow_input.source_key}"


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


def _hash_local_xml_file(path: str) -> str:
    import hashlib

    digest = hashlib.sha256()
    pending = b""
    first_chunk = True
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            if first_chunk:
                first_chunk = False
                if chunk.startswith(b"\xef\xbb\xbf"):
                    chunk = chunk[3:]
            pending += chunk
            pending = pending.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            lines = pending.split(b"\n")
            pending = lines.pop()
            for line in lines:
                digest.update(line.rstrip(b" \t\r\n\f\v"))
                digest.update(b"\n")
    if pending:
        digest.update(pending.rstrip(b" \t\r\n\f\v"))
    return digest.hexdigest()


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
    archive_id: str,
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


def _write_skipped_artifacts(
    *,
    s3_client: Any,
    workflow_input: MonthlyIngestWorkflowInput,
    artifact_keys: Mapping[str, str],
    started_at: datetime,
    source_object: MonthlyIngestSourceObject,
    archive_reason: str,
) -> dict[str, Any]:
    completed_at = datetime.now(timezone.utc)
    payload = {
        "status": "success",
        "job_id": workflow_input.job_id,
        "correlation_id": workflow_input.correlation_id,
        "workflow_version": workflow_input.workflow_version,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "input": workflow_input.to_dict(),
        "source_object": {
            "source_year": source_object.source_year,
            "source_kind": source_object.source_kind,
            "source_archive_key": source_object.source_archive_key,
            "source_signature": source_object.source_signature,
            "source_filename": source_object.source_filename,
        },
        "result": {
            "status": "success",
            "records_processed": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "skipped_archive": True,
            "skip_reason": archive_reason,
        },
    }
    summary = {
        "status": "success",
        "job_id": workflow_input.job_id,
        "correlation_id": workflow_input.correlation_id,
        "workflow_version": workflow_input.workflow_version,
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "skipped_archive": True,
        "skip_reason": archive_reason,
        "completed_at": completed_at.isoformat(),
    }
    artifacts = {
        "job_id": workflow_input.job_id,
        "correlation_id": workflow_input.correlation_id,
        "artifacts": {
            **artifact_keys,
        },
        "skipped_archive": True,
        "skip_reason": archive_reason,
    }
    _put_json_artifact(s3_client, workflow_input.destination_bucket, artifact_keys["artifact_index_s3_key"], artifacts)
    _put_json_artifact(s3_client, workflow_input.destination_bucket, artifact_keys["manifest_s3_key"], payload)
    _put_json_artifact(s3_client, workflow_input.destination_bucket, artifact_keys["summary_s3_key"], summary)
    return {
        "status": "success",
        "job_id": workflow_input.job_id,
        "correlation_id": workflow_input.correlation_id,
        "manifest_s3_key": artifact_keys["manifest_s3_key"],
        "artifact_index_s3_key": artifact_keys["artifact_index_s3_key"],
        "summary_s3_key": artifact_keys["summary_s3_key"],
        "processing_manifest_s3_key": None,
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "skipped_archive": True,
        "skip_reason": archive_reason,
    }


def _write_failure_artifacts(
    *,
    s3_client: Any,
    workflow_input: MonthlyIngestWorkflowInput,
    artifact_keys: Mapping[str, str],
    started_at: datetime,
    exc: Exception,
    source_object: MonthlyIngestSourceObject | None = None,
) -> None:
    payload = {
        "status": "failed",
        "job_id": workflow_input.job_id,
        "correlation_id": workflow_input.correlation_id,
        "workflow_version": workflow_input.workflow_version,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "input": workflow_input.to_dict(),
        "error_type": classify_error(exc),
        "error": str(exc),
    }
    if source_object is not None:
        payload["source_object"] = {
            "source_year": source_object.source_year,
            "source_kind": source_object.source_kind,
            "source_archive_key": source_object.source_archive_key,
            "source_signature": source_object.source_signature,
            "source_filename": source_object.source_filename,
        }
    try:
        _put_json_artifact(s3_client, workflow_input.destination_bucket, artifact_keys["manifest_s3_key"], payload)
        _put_json_artifact(s3_client, workflow_input.destination_bucket, artifact_keys["summary_s3_key"], payload)
    except Exception as write_exc:
        _log_structured(
            "monthly_ingest.worker.failure_artifact_write_failed",
            job_id=workflow_input.job_id,
            correlation_id=workflow_input.correlation_id,
            error=str(write_exc),
        )


def _put_json_artifact(s3_client: Any, bucket: str, key: str, payload: Mapping[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(dict(payload), sort_keys=True).encode("utf-8"),
        ContentType="application/json",
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
