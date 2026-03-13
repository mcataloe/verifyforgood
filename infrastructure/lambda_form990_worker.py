from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from charity_status.form990 import Form990IngestService
from charity_status.form990.filing_reconciliation import update_filing_state_from_ingest_result
from charity_status.form990.hardening import classify_error, validate_runtime_config
from charity_status.form990.source_downloads import execute_source_download_batch, load_downloaded_source_state
from charity_status.form990.zip_selected_processing import ZipBackedXmlLoader, select_zip_sources_for_records
from charity_status.ops import S3RunStore

BUCKET = os.environ.get("BUCKET", "").strip()
RAW_PREFIX = os.environ.get("FORM990_RAW_PREFIX", "form990/raw/")
RAW_SOURCE_PREFIX = os.environ.get("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
METADATA_PREFIX = os.environ.get("FORM990_METADATA_PREFIX", "form990/normalized/metadata/")
MANIFEST_PREFIX = os.environ.get("FORM990_MANIFEST_PREFIX", "form990/normalized/manifests/")
METRICS_PREFIX = os.environ.get("FORM990_METRICS_PREFIX", "form990/normalized/metrics/")
GOVERNANCE_PREFIX = os.environ.get("FORM990_GOVERNANCE_PREFIX", "form990/normalized/governance/")
QUALITY_PREFIX = os.environ.get("FORM990_QUALITY_PREFIX", "form990/normalized/quality/")
RELATIONSHIPS_PREFIX = os.environ.get("FORM990_RELATIONSHIPS_PREFIX", "form990/normalized/relationships/")
FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS = int(os.environ.get("FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS", "300"))
FORM990_ZIP_FETCH_TIMEOUT_SECONDS = int(os.environ.get("FORM990_ZIP_FETCH_TIMEOUT_SECONDS", "120"))
FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES = int(os.environ.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES", str(20 * 1024 * 1024)))
FORM990_ZIP_URL_FALLBACK_ENABLED = os.environ.get("FORM990_ZIP_URL_FALLBACK_ENABLED", "true").lower() == "true"
OPS_METADATA_BUCKET = os.environ.get("OPS_METADATA_BUCKET", "").strip()
OPS_METADATA_PREFIX = os.environ.get("OPS_METADATA_PREFIX", "ops").strip()
LOGGER = logging.getLogger(__name__)


def handler(event, context):
    del context
    if not BUCKET:
        raise ValueError("BUCKET environment variable is required")
    config_errors = _validate_worker_config()
    if config_errors:
        raise ValueError("; ".join(config_errors))
    records = event.get("Records") or []
    for item in records:
        body = json.loads(str(item.get("body") or "{}"))
        _process_chunk(body)
    return {"status": "success", "processed_messages": len(records)}


def _process_chunk(message: dict[str, Any]) -> None:
    run_id = str(message.get("run_id") or "").strip()
    chunk_id = str(message.get("chunk_id") or "").strip()
    chunk_bucket = str(message.get("chunk_s3_bucket") or OPS_METADATA_BUCKET or BUCKET).strip()
    chunk_key = str(message.get("chunk_s3_key") or "").strip()
    attempt = int(message.get("attempt") or 1)
    if not run_id or not chunk_id or not chunk_key:
        raise ValueError("chunk message is missing required run_id/chunk_id/chunk_s3_key")

    s3 = boto3.client("s3")
    result_key = f"{OPS_METADATA_PREFIX.strip('/')}/form990-runs/{run_id}/results/{chunk_id}.json"
    existing = _load_existing_result(s3, chunk_bucket, result_key)
    if existing and str(existing.get("status") or "").strip().lower() == "succeeded":
        _log_structured(
            "form990.worker.chunk_already_succeeded",
            run_id=run_id,
            chunk_id=chunk_id,
            result_key=result_key,
        )
        return
    started_at = datetime.now(timezone.utc).isoformat()
    chunk_payload = _get_json(s3, chunk_bucket, chunk_key)
    task_type = str(chunk_payload.get("task_type") or "filing_records").strip().lower()
    if task_type in {"source_catalog", "source_download"}:
        _process_source_download_chunk(
            s3=s3,
            run_id=run_id,
            chunk_id=chunk_id,
            chunk_bucket=chunk_bucket,
            result_key=result_key,
            attempt=attempt,
            started_at=started_at,
            chunk_payload=chunk_payload,
        )
        return

    records = chunk_payload.get("records")
    if not isinstance(records, list):
        raise ValueError("chunk payload records must be an array")

    service = Form990IngestService(
        bucket=BUCKET,
        raw_prefix=RAW_PREFIX,
        metadata_prefix=METADATA_PREFIX,
        manifest_prefix=MANIFEST_PREFIX,
        metrics_prefix=METRICS_PREFIX,
        governance_prefix=GOVERNANCE_PREFIX,
        quality_prefix=QUALITY_PREFIX,
        relationships_prefix=RELATIONSHIPS_PREFIX,
        s3_client=s3,
    )
    _update_run_status(s3, run_id, "running")
    _log_structured("form990.worker.chunk_start", run_id=run_id, chunk_id=chunk_id, task_type=task_type, attempt=attempt)
    try:
        zip_sources = chunk_payload.get("zip_sources")
        if not isinstance(zip_sources, list):
            zip_sources = select_zip_sources_for_records(records, load_downloaded_source_state(s3, BUCKET, MANIFEST_PREFIX))
        loader = ZipBackedXmlLoader(
            s3_client=s3,
            bucket=BUCKET,
            zip_sources=zip_sources,
            allow_url_fallback=FORM990_ZIP_URL_FALLBACK_ENABLED,
            url_timeout_seconds=FORM990_ZIP_FETCH_TIMEOUT_SECONDS,
            max_xml_file_size_bytes=FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES,
        )
        result = service.ingest_index_payload(payload=records, download_raw=True, record_downloader=loader.load)
        result["zip_resolved_count"] = loader.zip_extracted_count
        result["zip_fallback_url_count"] = loader.url_fallback_count
        result["zip_unresolved_count"] = loader.unresolved_count
        update_filing_state_from_ingest_result(
            s3_client=s3,
            bucket=BUCKET,
            manifest_prefix=MANIFEST_PREFIX,
            input_records=records,
            ingest_result=result,
        )
        completed_at = datetime.now(timezone.utc).isoformat()
        result_payload = {
            "run_id": run_id,
            "chunk_id": chunk_id,
            "status": "succeeded",
            "task_type": task_type,
            "attempt": attempt,
            "started_at": started_at,
            "completed_at": completed_at,
            "result": result,
        }
        s3.put_object(Bucket=chunk_bucket, Key=result_key, Body=json.dumps(result_payload, sort_keys=True).encode("utf-8"))
        _update_run_status(s3, run_id, "succeeded")
        _write_summary_snapshot(s3, run_id, chunk_bucket)
        _log_structured(
            "form990.worker.chunk_success",
            run_id=run_id,
            chunk_id=chunk_id,
            processed_records=result.get("records_processed"),
            parsed_count=result.get("parsed_count"),
            failed_count=result.get("failed_count"),
            zip_resolved_count=result.get("zip_resolved_count"),
            zip_fallback_url_count=result.get("zip_fallback_url_count"),
        )
    except Exception as exc:
        completed_at = datetime.now(timezone.utc).isoformat()
        s3.put_object(
            Bucket=chunk_bucket,
            Key=result_key,
            Body=json.dumps(
                {
                    "run_id": run_id,
                    "chunk_id": chunk_id,
                    "status": "failed",
                    "task_type": task_type,
                    "attempt": attempt,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "error_type": classify_error(exc),
                    "error": str(exc),
                },
                sort_keys=True,
            ).encode("utf-8"),
        )
        _update_run_status(s3, run_id, "failed")
        _write_summary_snapshot(s3, run_id, chunk_bucket)
        _log_structured(
            "form990.worker.chunk_failed",
            run_id=run_id,
            chunk_id=chunk_id,
            task_type=task_type,
            error_type=classify_error(exc),
            error=str(exc),
        )
        raise


def _process_source_download_chunk(
    *,
    s3: Any,
    run_id: str,
    chunk_id: str,
    chunk_bucket: str,
    result_key: str,
    attempt: int,
    started_at: str,
    chunk_payload: dict[str, Any],
) -> None:
    sources = chunk_payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("source download chunk payload sources must be an array")

    _update_run_status(s3, run_id, "running")
    try:
        download_manifest = execute_source_download_batch(
            sources=sources,
            bucket=BUCKET,
            raw_source_prefix=RAW_SOURCE_PREFIX,
            manifest_prefix=MANIFEST_PREFIX,
            s3_client=s3,
            run_id=run_id,
            batch_index=int(chunk_payload.get("chunk_index") or 0),
            timeout_seconds=FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
        )
        completed_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "run_id": run_id,
            "chunk_id": chunk_id,
            "status": "succeeded",
            "task_type": "source_download",
            "attempt": attempt,
            "started_at": started_at,
            "completed_at": completed_at,
            "result": {
                "stage": "source_artifact_fetch",
                "status": "success",
                "downloaded_count": download_manifest.get("downloaded_count", 0),
                "source_download_manifest_key": download_manifest.get("manifest_key"),
                "next_stage": "csv_reconciliation",
                "next_stage_implemented": False,
            },
        }
        s3.put_object(Bucket=chunk_bucket, Key=result_key, Body=json.dumps(payload, sort_keys=True).encode("utf-8"))
        _update_run_status(s3, run_id, "succeeded")
        _write_summary_snapshot(s3, run_id, chunk_bucket)
    except Exception as exc:
        completed_at = datetime.now(timezone.utc).isoformat()
        s3.put_object(
            Bucket=chunk_bucket,
            Key=result_key,
            Body=json.dumps(
                {
                    "run_id": run_id,
                    "chunk_id": chunk_id,
                    "status": "failed",
                    "task_type": "source_download",
                    "attempt": attempt,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "error_type": classify_error(exc),
                    "error": str(exc),
                },
                sort_keys=True,
            ).encode("utf-8"),
        )
        _update_run_status(s3, run_id, "failed")
        _write_summary_snapshot(s3, run_id, chunk_bucket)
        raise


def _update_run_status(s3: Any, run_id: str, status: str) -> None:
    store = S3RunStore(bucket=OPS_METADATA_BUCKET or BUCKET, prefix=OPS_METADATA_PREFIX, s3_client=s3)
    run = store.get_run("ingest", run_id) or {"ingest_run_id": run_id, "chunk_status_counts": {"queued": 0, "running": 0, "succeeded": 0, "failed": 0, "dlq": 0}}
    counts = dict(run.get("chunk_status_counts") or {"queued": 0, "running": 0, "succeeded": 0, "failed": 0, "dlq": 0})
    if status == "running" and counts.get("queued", 0) > 0:
        counts["queued"] = max(0, int(counts.get("queued", 0)) - 1)
    if status in {"succeeded", "failed"} and counts.get("running", 0) > 0:
        counts["running"] = max(0, int(counts.get("running", 0)) - 1)
    counts[status] = int(counts.get(status, 0)) + 1
    run["chunk_status_counts"] = counts
    if counts.get("queued", 0) == 0 and counts.get("running", 0) == 0:
        run["status"] = "success" if counts.get("failed", 0) == 0 else "partial_success"
        run["completed_at"] = datetime.now(timezone.utc).isoformat()
    store.write_ingest_run(run_id, run)


def _write_summary_snapshot(s3: Any, run_id: str, bucket: str) -> None:
    store = S3RunStore(bucket=OPS_METADATA_BUCKET or BUCKET, prefix=OPS_METADATA_PREFIX, s3_client=s3)
    run = store.get_run("ingest", run_id) or {}
    key = f"{OPS_METADATA_PREFIX.strip('/')}/form990-runs/{run_id}/summary.json"
    payload = {
        "ingest_run_id": run_id,
        "status": run.get("status"),
        "chunk_status_counts": run.get("chunk_status_counts"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload, sort_keys=True).encode("utf-8"))


def _get_json(s3: Any, bucket: str, key: str) -> dict[str, Any]:
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("chunk payload must be a JSON object")
    return payload


def _load_existing_result(s3: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        payload = json.loads(body)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def _validate_worker_config() -> list[str]:
    return validate_runtime_config(
        required_text={
            "BUCKET": BUCKET,
            "FORM990_MANIFEST_PREFIX": MANIFEST_PREFIX,
            "FORM990_METADATA_PREFIX": METADATA_PREFIX,
            "FORM990_RAW_PREFIX": RAW_PREFIX,
            "FORM990_RAW_SOURCE_PREFIX": RAW_SOURCE_PREFIX,
            "OPS_METADATA_PREFIX": OPS_METADATA_PREFIX,
        },
        positive_ints={
            "FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS": FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
            "FORM990_ZIP_FETCH_TIMEOUT_SECONDS": FORM990_ZIP_FETCH_TIMEOUT_SECONDS,
            "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES": FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES,
        },
    )


def _log_structured(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    try:
        LOGGER.info(json.dumps(payload, sort_keys=True))
    except Exception:
        LOGGER.info("%s %s", event, fields)
