from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from charity_status.form990.filing_reconciliation import update_filing_state_from_ingest_result
from charity_status.form990.ingest import Form990IngestService
from charity_status.form990.models import Form990IndexRecord
from charity_status.form990.teos_manifest import TeosZipManifestRecord, TeosZipManifestRepository

PROCESSING_STATUS_PENDING = "pending"
PROCESSING_STATUS_RUNNING = "processing"
PROCESSING_STATUS_SUCCEEDED = "success"
PROCESSING_STATUS_PARTIAL = "partial_success"
PROCESSING_STATUS_FAILED = "failed"
PROCESSING_TERMINAL_STATUSES = {
    PROCESSING_STATUS_SUCCEEDED,
}


@dataclass(frozen=True)
class TeosBatchProcessingResult:
    manifest_record: TeosZipManifestRecord
    source_object_keys: tuple[str, ...]
    ingest_result: dict[str, Any]
    skipped: bool = False


def should_process_teos_batch(record: TeosZipManifestRecord) -> bool:
    return (
        str(record.extraction_status or "").strip().lower() == "extracted"
        and str(record.processing_status or "").strip().lower()
        not in PROCESSING_TERMINAL_STATUSES
    )


def list_teos_raw_xml_keys(
    *,
    s3_client: Any,
    bucket: str,
    destination_raw_s3_prefix: str,
) -> list[str]:
    prefix = destination_raw_s3_prefix.strip("/")
    if prefix:
        prefix = f"{prefix}/"
    keys: list[str] = []
    continuation_token: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": prefix,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        response = s3_client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            key = str(item.get("Key") or "").strip()
            if not key or key.endswith("/") or not key.lower().endswith(".xml"):
                continue
            keys.append(key)
        if not response.get("IsTruncated"):
            break
        continuation_token = str(response.get("NextContinuationToken") or "").strip() or None
        if not continuation_token:
            break
    return sorted(set(keys))


def build_teos_batch_index_records(
    *,
    bucket: str,
    manifest_record: TeosZipManifestRecord,
    source_object_keys: list[str],
) -> list[Form990IndexRecord]:
    records: list[Form990IndexRecord] = []
    for key in source_object_keys:
        member_name = key.rsplit("/", 1)[-1]
        irs_object_id = _object_id_from_member_name(member_name)
        if not irs_object_id:
            continue
        records.append(
            Form990IndexRecord(
                ein=None,
                tax_year=manifest_record.tax_year,
                filing_date=None,
                return_type="990",
                irs_object_id=irs_object_id,
                xml_url=f"s3://{bucket}/{key}",
                source_year=manifest_record.tax_year,
                source_archive=manifest_record.zip_basename,
                source_signature=_record_signature(manifest_record, key),
            )
        )
    return records


def process_teos_manifest_batch(
    *,
    service: Form990IngestService,
    repository: TeosZipManifestRepository,
    manifest_record: TeosZipManifestRecord,
    bucket: str,
    manifest_prefix: str,
) -> TeosBatchProcessingResult:
    current_record = repository.load_record(manifest_record.tax_year, manifest_record.zip_basename) or manifest_record
    source_object_keys = list_teos_raw_xml_keys(
        s3_client=service.s3,
        bucket=bucket,
        destination_raw_s3_prefix=current_record.destination_raw_s3_prefix,
    )
    if not should_process_teos_batch(current_record):
        return TeosBatchProcessingResult(
            manifest_record=current_record,
            source_object_keys=tuple(source_object_keys),
            ingest_result={
                "status": "skipped",
                "records_processed": 0,
                "parsed_count": 0,
                "failed_count": 0,
                "records": [],
            },
            skipped=True,
        )

    attempted_at = datetime.now(timezone.utc).isoformat()
    repository.save_record(
        replace(
            current_record,
            processing_status=PROCESSING_STATUS_RUNNING,
            processing_attempted_at=attempted_at,
            last_error=None,
            updated_at=attempted_at,
        )
    )

    try:
        records = build_teos_batch_index_records(
            bucket=bucket,
            manifest_record=current_record,
            source_object_keys=source_object_keys,
        )
        ingest_result = service.ingest_index_payload(
            payload=[_record_to_dict(item) for item in records],
            download_raw=True,
            record_downloader=lambda record: _load_teos_raw_xml(
                s3_client=service.s3,
                bucket=bucket,
                record=record,
            ),
        )
        update_filing_state_from_ingest_result(
            s3_client=service.s3,
            bucket=bucket,
            manifest_prefix=manifest_prefix,
            input_records=[_record_to_dict(item) for item in records],
            ingest_result=ingest_result,
        )
        finalized_record = replace(
            current_record,
            processing_status=_processing_status_from_ingest(ingest_result),
            processing_attempted_at=attempted_at,
            last_error=_summarize_processing_error(ingest_result),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        repository.save_record(finalized_record)
        return TeosBatchProcessingResult(
            manifest_record=finalized_record,
            source_object_keys=tuple(source_object_keys),
            ingest_result=ingest_result,
        )
    except Exception as exc:
        failed_record = replace(
            current_record,
            processing_status=PROCESSING_STATUS_FAILED,
            processing_attempted_at=attempted_at,
            last_error=str(exc),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        repository.save_record(failed_record)
        raise


def _load_teos_raw_xml(*, s3_client: Any, bucket: str, record: Form990IndexRecord) -> tuple[bytes, str]:
    xml_reference = str(record.xml_url or "").strip()
    target_bucket, key = _parse_s3_reference(xml_reference, default_bucket=bucket)
    body = s3_client.get_object(Bucket=target_bucket, Key=key)["Body"].read()
    return body, (xml_reference or f"s3://{target_bucket}/{key}")


def _parse_s3_reference(reference: str, *, default_bucket: str) -> tuple[str, str]:
    if reference.startswith("s3://"):
        path = reference[5:]
        bucket, _sep, key = path.partition("/")
        if bucket and key:
            return bucket, key
    key = reference.lstrip("/")
    if key:
        return default_bucket, key
    raise ValueError("record xml_url must point to an S3 object")


def _processing_status_from_ingest(ingest_result: dict[str, Any]) -> str:
    status = str(ingest_result.get("status") or "").strip().lower()
    if status in {
        PROCESSING_STATUS_SUCCEEDED,
        PROCESSING_STATUS_PARTIAL,
        PROCESSING_STATUS_FAILED,
    }:
        return status
    return PROCESSING_STATUS_FAILED


def _summarize_processing_error(ingest_result: dict[str, Any]) -> str | None:
    status = str(ingest_result.get("status") or "").strip().lower()
    if status == PROCESSING_STATUS_SUCCEEDED:
        return None
    records = ingest_result.get("records")
    if isinstance(records, list):
        for item in records:
            if not isinstance(item, dict):
                continue
            error = str(item.get("parse_error") or "").strip()
            if error:
                return error
    failed_count = int(ingest_result.get("failed_count") or 0)
    if failed_count > 0:
        return f"{failed_count} filing(s) failed during source-batch processing"
    return f"source-batch processing ended with status {status or 'failed'}"


def _record_to_dict(record: Form990IndexRecord) -> dict[str, Any]:
    return {
        "ein": record.ein,
        "tax_year": record.tax_year,
        "filing_date": record.filing_date,
        "return_type": record.return_type,
        "irs_object_id": record.irs_object_id,
        "xml_url": record.xml_url,
        "source_year": record.source_year,
        "source_archive": record.source_archive,
        "source_signature": record.source_signature,
    }


def _object_id_from_member_name(member_name: str) -> str:
    name = str(member_name or "").strip()
    if not name:
        return ""
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name.strip()


def _record_signature(record: TeosZipManifestRecord, key: str) -> str | None:
    parts = [
        str(record.tax_year or "").strip(),
        str(record.zip_basename or "").strip(),
        str(record.etag or "").strip(),
        str(record.last_modified or "").strip(),
        str(record.content_length or ""),
        str(key or "").strip(),
    ]
    text = "|".join(part for part in parts if part)
    return text or None


__all__ = [
    "PROCESSING_STATUS_FAILED",
    "PROCESSING_STATUS_PARTIAL",
    "PROCESSING_STATUS_PENDING",
    "PROCESSING_STATUS_RUNNING",
    "PROCESSING_STATUS_SUCCEEDED",
    "TeosBatchProcessingResult",
    "build_teos_batch_index_records",
    "list_teos_raw_xml_keys",
    "process_teos_manifest_batch",
    "should_process_teos_batch",
]
