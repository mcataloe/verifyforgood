from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from charity_status.form990 import Form990IngestService
from charity_status.ops import S3RunStore

BUCKET = os.environ.get("BUCKET", "").strip()
RAW_PREFIX = os.environ.get("FORM990_RAW_PREFIX", "form990/raw/")
METADATA_PREFIX = os.environ.get("FORM990_METADATA_PREFIX", "form990/normalized/metadata/")
MANIFEST_PREFIX = os.environ.get("FORM990_MANIFEST_PREFIX", "form990/normalized/manifests/")
METRICS_PREFIX = os.environ.get("FORM990_METRICS_PREFIX", "form990/normalized/metrics/")
GOVERNANCE_PREFIX = os.environ.get("FORM990_GOVERNANCE_PREFIX", "form990/normalized/governance/")
QUALITY_PREFIX = os.environ.get("FORM990_QUALITY_PREFIX", "form990/normalized/quality/")
RELATIONSHIPS_PREFIX = os.environ.get("FORM990_RELATIONSHIPS_PREFIX", "form990/normalized/relationships/")
OPS_METADATA_BUCKET = os.environ.get("OPS_METADATA_BUCKET", "").strip()
OPS_METADATA_PREFIX = os.environ.get("OPS_METADATA_PREFIX", "ops").strip()


def handler(event, context):
    del context
    if not BUCKET:
        raise ValueError("BUCKET environment variable is required")
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
    started_at = datetime.now(timezone.utc).isoformat()
    chunk_payload = _get_json(s3, chunk_bucket, chunk_key)
    task_type = str(chunk_payload.get("task_type") or "filing_records").strip().lower()
    if task_type == "source_catalog":
        _process_source_catalog_chunk(
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
    try:
        result = service.ingest_index_payload(payload=records, download_raw=True)
        completed_at = datetime.now(timezone.utc).isoformat()
        result_payload = {
            "run_id": run_id,
            "chunk_id": chunk_id,
            "status": "succeeded",
            "attempt": attempt,
            "started_at": started_at,
            "completed_at": completed_at,
            "result": result,
        }
        s3.put_object(Bucket=chunk_bucket, Key=result_key, Body=json.dumps(result_payload, sort_keys=True).encode("utf-8"))
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
                    "attempt": attempt,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "error": str(exc),
                },
                sort_keys=True,
            ).encode("utf-8"),
        )
        _update_run_status(s3, run_id, "failed")
        _write_summary_snapshot(s3, run_id, chunk_bucket)
        raise


def _process_source_catalog_chunk(
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
        raise ValueError("source catalog chunk payload sources must be an array")

    _update_run_status(s3, run_id, "running")
    completed_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "run_id": run_id,
        "chunk_id": chunk_id,
        "status": "succeeded",
        "task_type": "source_catalog",
        "attempt": attempt,
        "started_at": started_at,
        "completed_at": completed_at,
        "result": {
            "stage": "source_catalog",
            "status": "deferred",
            "sources_recorded": len(sources),
            "next_stage": "source_artifact_fetch",
            "next_stage_implemented": False,
        },
    }
    s3.put_object(Bucket=chunk_bucket, Key=result_key, Body=json.dumps(payload, sort_keys=True).encode("utf-8"))
    _update_run_status(s3, run_id, "succeeded")
    _write_summary_snapshot(s3, run_id, chunk_bucket)


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
