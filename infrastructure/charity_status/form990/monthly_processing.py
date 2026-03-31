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
from typing import Any, Mapping

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

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

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


def run_form990_monthly_processing_task(
    *,
    env: Mapping[str, str] | None = None,
    s3_client: Any | None = None,
    now: datetime | None = None,
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
    job_prefix = workflow_job_prefix(input_payload.destination_prefix, input_payload.job_id)
    artifact_keys = {
        "manifest_s3_key": workflow_manifest_key(input_payload.destination_prefix, input_payload.job_id),
        "artifact_index_s3_key": workflow_artifact_index_key(input_payload.destination_prefix, input_payload.job_id),
        "summary_s3_key": workflow_summary_key(input_payload.destination_prefix, input_payload.job_id),
    }
    _log_structured(
        "monthly_ingest.worker.start",
        job_id=input_payload.job_id,
        correlation_id=input_payload.correlation_id,
        source_bucket=input_payload.source_bucket,
        source_key=input_payload.source_key,
        destination_bucket=input_payload.destination_bucket,
        destination_prefix=input_payload.destination_prefix,
    )

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

    try:
        with tempfile.TemporaryDirectory(prefix="monthly-ingest-xml-") as workdir:
            extracted_members = extract_zip_xml_members_to_workdir(
                archive_path=archive_path,
                workdir=workdir,
                max_xml_file_size_bytes=int(source.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES") or DEFAULT_MAX_XML_FILE_SIZE_BYTES),
            )
            if not extracted_members:
                raise MonthlyIngestMalformedArchiveError("zip archive did not contain any processable XML members")
            _log_structured(
                "monthly_ingest.worker.extracted",
                job_id=input_payload.job_id,
                extracted_member_count=len(extracted_members),
                archive_checksum=archive_checksum,
                archive_size_bytes=archive_size,
            )

            records, local_file_lookup = build_local_index_records(
                extracted_members=extracted_members,
                source_bucket=input_payload.source_bucket,
                source_key=input_payload.source_key,
                source_object=source_object,
                archive_checksum=archive_checksum,
            )
            ingest_result = ingest_form990_records(
                records=records,
                bucket=input_payload.destination_bucket,
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
                nonprofit_persistence_service=nonprofit_persistence_service,
            ).to_dict()
            completed_at = datetime.now(timezone.utc)
            artifacts_payload = {
                "job_id": input_payload.job_id,
                "correlation_id": input_payload.correlation_id,
                "archive_s3_bucket": input_payload.source_bucket,
                "archive_s3_key": input_payload.source_key,
                "archive_size_bytes": archive_size,
                "archive_checksum_sha256": archive_checksum,
                "extracted_member_count": len(extracted_members),
                "artifacts": {
                    **artifact_keys,
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
                "job_id": input_payload.job_id,
                "correlation_id": input_payload.correlation_id,
                "workflow_version": input_payload.workflow_version,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "input": input_payload.to_dict(),
                "source_object": {
                    "bucket": input_payload.source_bucket,
                    "key": input_payload.source_key,
                    "archive_size_bytes": archive_size,
                    "archive_checksum_sha256": archive_checksum,
                    "source_year": source_object.source_year,
                    "source_kind": source_object.source_kind,
                    "source_archive_key": source_object.source_archive_key,
                    "source_signature": source_object.source_signature,
                    "source_filename": source_object.source_filename,
                },
                "extraction": {
                    "extracted_member_count": len(extracted_members),
                    "members": [item.member_name for item in extracted_members[:25]],
                },
                "result": ingest_result,
                "artifacts": artifacts_payload["artifacts"],
            }
            summary_payload = {
                "status": str(ingest_result.get("status") or "failed"),
                "job_id": input_payload.job_id,
                "correlation_id": input_payload.correlation_id,
                "workflow_version": input_payload.workflow_version,
                "records_processed": int(ingest_result.get("records_processed") or 0),
                "parsed_count": int(ingest_result.get("parsed_count") or 0),
                "failed_count": int(ingest_result.get("failed_count") or 0),
                "archive_size_bytes": archive_size,
                "archive_checksum_sha256": archive_checksum,
                "extracted_member_count": len(extracted_members),
                "processing_manifest_s3_key": ingest_result.get("manifest_s3_key"),
                "artifact_index_s3_key": artifact_keys["artifact_index_s3_key"],
                "completed_at": completed_at.isoformat(),
            }
            _put_json_artifact(s3, input_payload.destination_bucket, artifact_keys["artifact_index_s3_key"], artifacts_payload)
            _put_json_artifact(s3, input_payload.destination_bucket, artifact_keys["manifest_s3_key"], manifest_payload)
            _put_json_artifact(s3, input_payload.destination_bucket, artifact_keys["summary_s3_key"], summary_payload)
            if str(ingest_result.get("status") or "").strip().lower() == "failed":
                raise RuntimeError(
                    f"monthly ingest processing failed with {int(ingest_result.get('failed_count') or 0)} failed record(s)"
                )
            result = {
                "status": str(ingest_result.get("status") or "failed"),
                "job_id": input_payload.job_id,
                "correlation_id": input_payload.correlation_id,
                "manifest_s3_key": artifact_keys["manifest_s3_key"],
                "artifact_index_s3_key": artifact_keys["artifact_index_s3_key"],
                "summary_s3_key": artifact_keys["summary_s3_key"],
                "processing_manifest_s3_key": ingest_result.get("manifest_s3_key"),
                "records_processed": int(ingest_result.get("records_processed") or 0),
                "parsed_count": int(ingest_result.get("parsed_count") or 0),
                "failed_count": int(ingest_result.get("failed_count") or 0),
            }
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
    try:
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
        xml_reference = f"s3://{source_bucket}/{source_key}#{member.member_name}"
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
    payload = {"event": event, **fields}
    try:
        LOGGER.info(json.dumps(payload, sort_keys=True))
    except Exception:
        LOGGER.info("%s %s", event, fields)


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
    "run_form990_monthly_processing_task",
]
