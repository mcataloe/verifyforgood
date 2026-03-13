from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from charity_status.api import error_response, json_response
from charity_status.form990 import Form990IngestService
from charity_status.form990.discovery import fetch_index_records
from charity_status.form990.filing_reconciliation import reconcile_filing_catalog, update_filing_state_from_ingest_result
from charity_status.form990.irs_page_discovery import (
    IrsYearSource,
    discover_irs_form990_sources,
    discovery_state_payload,
    diff_source_catalog,
)
from charity_status.form990.source_downloads import execute_source_download_batch, load_downloaded_source_state, plan_source_downloads
from charity_status.form990.policy import IngestPolicyConfig, select_target_years
from charity_status.form990.source_catalog import normalize_configured_sources, select_sources_by_years, source_years
from charity_status.form990.zip_selected_processing import ZipBackedXmlLoader, select_zip_sources_for_records
from charity_status.ops import S3RunStore
from charity_status.form990.storage import checkpoint_key, discovery_diff_key, discovery_manifest_key, discovery_state_key, source_download_state_prefix, state_manifest_key

BUCKET = os.environ.get("BUCKET")
RAW_PREFIX = os.environ.get("FORM990_RAW_PREFIX", "form990/raw/")
RAW_SOURCE_PREFIX = os.environ.get("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
METADATA_PREFIX = os.environ.get("FORM990_METADATA_PREFIX", "form990/normalized/metadata/")
MANIFEST_PREFIX = os.environ.get("FORM990_MANIFEST_PREFIX", "form990/normalized/manifests/")
METRICS_PREFIX = os.environ.get("FORM990_METRICS_PREFIX", "form990/normalized/metrics/")
GOVERNANCE_PREFIX = os.environ.get("FORM990_GOVERNANCE_PREFIX", "form990/normalized/governance/")
QUALITY_PREFIX = os.environ.get("FORM990_QUALITY_PREFIX", "form990/normalized/quality/")
RELATIONSHIPS_PREFIX = os.environ.get("FORM990_RELATIONSHIPS_PREFIX", "form990/normalized/relationships/")
INDEX_URL = os.environ.get("FORM990_INDEX_URL", "").strip()
INDEX_URLS = os.environ.get("FORM990_INDEX_URLS", "").strip()
INDEX_FETCH_TIMEOUT_SECONDS = int(os.environ.get("FORM990_INDEX_FETCH_TIMEOUT_SECONDS", "60"))
DEFAULT_DOWNLOAD_RAW = os.environ.get("FORM990_DEFAULT_DOWNLOAD_RAW", "true").lower() == "true"
FORM990_RUN_MODE = os.environ.get("FORM990_RUN_MODE", "incremental").strip().lower()
FORM990_BATCH_SIZE = int(os.environ.get("FORM990_BATCH_SIZE", "100"))
FORM990_RETRY_COUNT = int(os.environ.get("FORM990_RETRY_COUNT", "2"))
FORM990_SOURCE_CATALOG_JSON = os.environ.get("FORM990_SOURCE_CATALOG_JSON", "").strip()
FORM990_INCREMENTAL_YEAR_WINDOW = int(os.environ.get("FORM990_INCREMENTAL_YEAR_WINDOW", "2"))
FORM990_RECONCILIATION_ENABLED = os.environ.get("FORM990_RECONCILIATION_ENABLED", "true").lower() == "true"
FORM990_RECONCILIATION_CADENCE_DAYS = int(os.environ.get("FORM990_RECONCILIATION_CADENCE_DAYS", "30"))
FORM990_TARGET_YEARS = os.environ.get("FORM990_TARGET_YEARS", "").strip()
FORM990_LAST_RECONCILIATION_AT = os.environ.get("FORM990_LAST_RECONCILIATION_AT", "").strip()
FORM990_SOURCE_MODE = os.environ.get("FORM990_SOURCE_MODE", "configured").strip().lower()
FORM990_IRS_DOWNLOADS_PAGE_URL = os.environ.get(
    "FORM990_IRS_DOWNLOADS_PAGE_URL",
    "https://www.irs.gov/charities-non-profits/form-990-series-downloads",
).strip()
FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS = int(os.environ.get("FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS", "300"))
FORM990_ZIP_FETCH_TIMEOUT_SECONDS = int(os.environ.get("FORM990_ZIP_FETCH_TIMEOUT_SECONDS", "120"))
FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES = int(os.environ.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES", str(20 * 1024 * 1024)))
FORM990_ZIP_URL_FALLBACK_ENABLED = os.environ.get("FORM990_ZIP_URL_FALLBACK_ENABLED", "true").lower() == "true"
FORM990_EXECUTION_MODE = os.environ.get("FORM990_EXECUTION_MODE", "inline").strip().lower()
FORM990_CHUNK_SIZE = int(os.environ.get("FORM990_CHUNK_SIZE", "250"))
FORM990_WORK_QUEUE_URL = os.environ.get("FORM990_WORK_QUEUE_URL", "").strip()
OPS_METADATA_BUCKET = os.environ.get("OPS_METADATA_BUCKET", "").strip()
OPS_METADATA_PREFIX = os.environ.get("OPS_METADATA_PREFIX", "ops").strip()
LOGGER = logging.getLogger(__name__)


def handler(event, context):
    del context
    if not BUCKET:
        return error_response(500, "BUCKET environment variable is required")

    try:
        payload = _parse_event_payload(event)
    except ValueError as exc:
        return error_response(400, str(exc))
    service = Form990IngestService(
        bucket=BUCKET,
        raw_prefix=RAW_PREFIX,
        metadata_prefix=METADATA_PREFIX,
        manifest_prefix=MANIFEST_PREFIX,
        metrics_prefix=METRICS_PREFIX,
        governance_prefix=GOVERNANCE_PREFIX,
        quality_prefix=QUALITY_PREFIX,
        relationships_prefix=RELATIONSHIPS_PREFIX,
    )

    explicit_records = payload.get("records")
    if explicit_records is not None:
        if not isinstance(explicit_records, list):
            return error_response(400, "records must be an array")
        result = service.ingest_index_payload(payload=explicit_records, download_raw=bool(payload.get("download_raw", DEFAULT_DOWNLOAD_RAW)))
        update_filing_state_from_ingest_result(
            s3_client=service.s3,
            bucket=BUCKET or "",
            manifest_prefix=MANIFEST_PREFIX,
            input_records=explicit_records,
            ingest_result=result,
        )
        result["filing_state_key"] = state_manifest_key(MANIFEST_PREFIX)
        return json_response(200, result)

    # Backward-compatible path: when callers provide index_url(s) without orchestration mode,
    # ingest directly and return legacy ingest payload shape.
    if "mode" not in payload and "source_catalog" not in payload:
        legacy_records = _load_legacy_index_records(payload)
        if legacy_records:
            result = service.ingest_index_payload(payload=legacy_records, download_raw=bool(payload.get("download_raw", DEFAULT_DOWNLOAD_RAW)))
            update_filing_state_from_ingest_result(
                s3_client=service.s3,
                bucket=BUCKET or "",
                manifest_prefix=MANIFEST_PREFIX,
                input_records=legacy_records,
                ingest_result=result,
            )
            result["filing_state_key"] = state_manifest_key(MANIFEST_PREFIX)
            return json_response(200, result)

    try:
        execution_mode = _resolve_execution_mode(payload)
        if execution_mode == "orchestrated":
            result = _run_discovery_orchestrated(service, payload)
        else:
            result = _run_discovery_ingestion(service, payload)
        return json_response(200, result)
    except ValueError as exc:
        return error_response(400, str(exc))


def _run_discovery_ingestion(service: Form990IngestService, payload: dict[str, Any]) -> dict[str, Any]:
    prepared = _prepare_discovery_run(service, payload)
    download_manifest = _download_selected_sources(service, prepared)
    downloaded_state = load_downloaded_source_state(service.s3, BUCKET or "", MANIFEST_PREFIX)
    csv_sources = _resolve_selected_csv_sources(
        selected_sources=prepared["selected_sources"],
        downloaded_state=downloaded_state,
    )
    reconciliation = reconcile_filing_catalog(
        s3_client=service.s3,
        bucket=BUCKET or "",
        manifest_prefix=MANIFEST_PREFIX,
        run_id=prepared["run_id"],
        csv_sources=csv_sources,
    )
    selected_records = [_record_to_dict(item) for item in reconciliation.selected_records]
    zip_loader: ZipBackedXmlLoader | None = None
    if selected_records:
        zip_loader = _build_zip_loader(service.s3, selected_records, downloaded_state)
        ingest_result = service.ingest_index_payload(
            payload=selected_records,
            download_raw=bool(payload.get("download_raw", DEFAULT_DOWNLOAD_RAW)),
            record_downloader=zip_loader.load if zip_loader else None,
        )
        update_filing_state_from_ingest_result(
            s3_client=service.s3,
            bucket=BUCKET or "",
            manifest_prefix=MANIFEST_PREFIX,
            input_records=selected_records,
            ingest_result=ingest_result,
        )
    else:
        ingest_result = {
            "status": "success",
            "records_processed": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "manifest_s3_key": None,
            "filing_records_s3_key": None,
            "metrics_s3_key": None,
            "governance_s3_key": None,
            "quality_s3_key": None,
            "relationships_s3_key": None,
            "records": [],
        }
    response = {
        "status": str(ingest_result.get("status") or "success"),
        "stage": "csv_reconciliation",
        "execution_mode": "inline",
        "mode": prepared["mode"],
        "run_id": prepared["run_id"],
        "source_mode": prepared["source_mode"],
        "source_catalog_count": prepared["source_catalog_count"],
        "sources_discovered": prepared["source_catalog_count"],
        "source_years": prepared["source_years"],
        "new_sources": prepared["new_sources"],
        "removed_sources": prepared["removed_sources"],
        "changed_sources": prepared["changed_sources"],
        "unchanged_sources": prepared["unchanged_sources"],
        "selected_source_count": prepared["selected_source_count"],
        "scheduled_source_count": prepared["scheduled_source_count"],
        "scheduled_sources": prepared["scheduled_sources"][:10],
        "skipped_source_count": prepared["skipped_source_count"],
        "downloaded_source_count": download_manifest.get("downloaded_count", 0),
        "discovery_state_key": discovery_state_key(MANIFEST_PREFIX),
        "discovery_manifest_key": prepared["discovery_manifest_key"],
        "discovery_diff_key": prepared["discovery_diff_key"],
        "source_download_manifest_key": download_manifest.get("manifest_key"),
        "source_download_state_prefix": source_download_state_prefix(MANIFEST_PREFIX),
        "filing_catalog_key": reconciliation.catalog_key,
        "filing_diff_key": reconciliation.diff_key,
        "filing_state_key": reconciliation.state_key,
        "filings_discovered": len(reconciliation.current_records),
        "filings_new": reconciliation.new_count,
        "filings_changed": reconciliation.changed_count,
        "filings_incomplete": reconciliation.incomplete_count,
        "filings_skipped": reconciliation.unchanged_count,
        "policy": prepared["policy"],
        "next_stage": "zip_extraction",
        "next_stage_implemented": False,
        "selected_records": len(selected_records),
        "selected_filings": selected_records[:10],
        "processed_records": int(ingest_result.get("records_processed") or 0),
        "parsed_count": int(ingest_result.get("parsed_count") or 0),
        "failed_count": int(ingest_result.get("failed_count") or 0),
        "zip_resolved_count": int(zip_loader.zip_extracted_count) if zip_loader else 0,
        "zip_fallback_url_count": int(zip_loader.url_fallback_count) if zip_loader else 0,
        "zip_unresolved_count": int(zip_loader.unresolved_count) if zip_loader else 0,
        "batch_count": 1 if selected_records else 0,
        "checkpoint_key": checkpoint_key(MANIFEST_PREFIX),
        "manifest_s3_key": ingest_result.get("manifest_s3_key"),
    }
    _log_structured(
        "form990.discovery.run.complete",
        run_id=prepared["run_id"],
        source_mode=prepared["source_mode"],
        source_catalog_count=prepared["source_catalog_count"],
        new_sources=prepared["new_sources"],
        changed_sources=prepared["changed_sources"],
        removed_sources=prepared["removed_sources"],
        scheduled_source_count=prepared["scheduled_source_count"],
        skipped_source_count=prepared["skipped_source_count"],
        downloaded_source_count=download_manifest.get("downloaded_count", 0),
        filings_discovered=len(reconciliation.current_records),
        selected_records=len(selected_records),
        parsed_count=int(ingest_result.get("parsed_count") or 0),
        zip_resolved_count=int(zip_loader.zip_extracted_count) if zip_loader else 0,
        zip_fallback_url_count=int(zip_loader.url_fallback_count) if zip_loader else 0,
    )
    _persist_ingest_ops_run(service, response, selected_records)
    return response


def _run_discovery_orchestrated(service: Form990IngestService, payload: dict[str, Any]) -> dict[str, Any]:
    if not FORM990_WORK_QUEUE_URL:
        raise ValueError("FORM990_WORK_QUEUE_URL is required for orchestrated execution mode")

    prepared = _prepare_discovery_run(service, payload)
    run_id = prepared["run_id"]
    download_manifest = _download_selected_sources(service, prepared)
    downloaded_state = load_downloaded_source_state(service.s3, BUCKET or "", MANIFEST_PREFIX)
    csv_sources = _resolve_selected_csv_sources(
        selected_sources=prepared["selected_sources"],
        downloaded_state=downloaded_state,
    )
    reconciliation = reconcile_filing_catalog(
        s3_client=service.s3,
        bucket=BUCKET or "",
        manifest_prefix=MANIFEST_PREFIX,
        run_id=prepared["run_id"],
        csv_sources=csv_sources,
    )
    selected = [_record_to_dict(item) for item in reconciliation.selected_records]
    zip_sources = select_zip_sources_for_records(selected, downloaded_state)
    chunk_size = int(payload.get("chunk_size") or FORM990_CHUNK_SIZE)
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    queue = boto3.client("sqs")
    bucket = OPS_METADATA_BUCKET or BUCKET or ""
    prefix = OPS_METADATA_PREFIX.strip("/") or "ops"
    chunks = []
    for idx in range(0, len(selected), chunk_size):
        chunk = selected[idx : idx + chunk_size]
        if not chunk:
            continue
        chunk_index = idx // chunk_size
        chunk_id = f"{run_id}-{chunk_index:05d}"
        chunk_key = f"{prefix}/form990-runs/{run_id}/chunks/{chunk_id}.json"
        chunk_payload = {
            "run_id": run_id,
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "task_type": "filing_records",
            "stage": "zip_extraction",
            "records": chunk,
            "zip_sources": zip_sources,
            "mode": prepared["mode"],
            "source_mode": prepared["source_mode"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        service.s3.put_object(Bucket=bucket, Key=chunk_key, Body=json.dumps(chunk_payload, sort_keys=True).encode("utf-8"))
        queue.send_message(
            QueueUrl=FORM990_WORK_QUEUE_URL,
            MessageBody=json.dumps(
                {
                    "run_id": run_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "chunk_s3_bucket": bucket,
                    "chunk_s3_key": chunk_key,
                    "attempt": 1,
                },
                sort_keys=True,
            ),
        )
        chunks.append({"chunk_id": chunk_id, "chunk_index": chunk_index, "record_count": len(chunk), "chunk_s3_key": chunk_key})

    run_store = S3RunStore(bucket=bucket, prefix=prefix, s3_client=service.s3)
    run_summary = {
        "ingest_run_id": run_id,
        "mode": prepared["mode"],
        "execution_mode": "orchestrated",
        "stage": "csv_reconciliation",
        "status": "queued" if chunks else "success",
        "source_mode": prepared["source_mode"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_catalog_count": prepared["source_catalog_count"],
        "sources_discovered": prepared["source_catalog_count"],
        "source_years": prepared["source_years"],
        "sources_new": prepared["new_sources"],
        "sources_removed": prepared["removed_sources"],
        "sources_changed": prepared["changed_sources"],
        "sources_unchanged": prepared["unchanged_sources"],
        "selected_source_count": prepared["selected_source_count"],
        "skipped_source_count": prepared["skipped_source_count"],
        "scheduled_source_count": prepared["scheduled_source_count"],
        "downloaded_source_count": download_manifest.get("downloaded_count", 0),
        "filings_discovered": len(reconciliation.current_records),
        "filings_new": reconciliation.new_count,
        "filings_changed": reconciliation.changed_count,
        "filings_incomplete": reconciliation.incomplete_count,
        "filings_skipped": reconciliation.unchanged_count,
        "selected_records": len(selected),
        "zip_source_count": len(zip_sources),
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "chunk_status_counts": {"queued": len(chunks), "running": 0, "succeeded": 0, "failed": 0, "dlq": 0},
        "policy": prepared["policy"],
        "discovery_state_key": discovery_state_key(MANIFEST_PREFIX),
        "discovery_manifest_key": prepared["discovery_manifest_key"],
        "discovery_diff_key": prepared["discovery_diff_key"],
        "source_download_manifest_key": download_manifest.get("manifest_key"),
        "source_download_state_prefix": source_download_state_prefix(MANIFEST_PREFIX),
        "filing_catalog_key": reconciliation.catalog_key,
        "filing_diff_key": reconciliation.diff_key,
        "filing_state_key": reconciliation.state_key,
    }
    run_store.write_ingest_run(run_id, run_summary)

    ops_run_key = f"{prefix}/form990-runs/{run_id}/run.json"
    service.s3.put_object(Bucket=bucket, Key=ops_run_key, Body=json.dumps(run_summary, sort_keys=True).encode("utf-8"))
    service.s3.put_object(
        Bucket=bucket,
        Key=f"{prefix}/form990-runs/{run_id}/summary.json",
        Body=json.dumps({"ingest_run_id": run_id, "chunk_count": len(chunks), "status": "queued"}, sort_keys=True).encode("utf-8"),
    )

    return {
        "status": "queued" if chunks else "success",
        "stage": "zip_extraction",
        "mode": prepared["mode"],
        "execution_mode": "orchestrated",
        "run_id": run_id,
        "source_mode": prepared["source_mode"],
        "source_catalog_count": prepared["source_catalog_count"],
        "sources_discovered": prepared["source_catalog_count"],
        "source_years": prepared["source_years"],
        "new_sources": prepared["new_sources"],
        "removed_sources": prepared["removed_sources"],
        "changed_sources": prepared["changed_sources"],
        "unchanged_sources": prepared["unchanged_sources"],
        "selected_source_count": prepared["selected_source_count"],
        "skipped_source_count": prepared["skipped_source_count"],
        "scheduled_source_count": prepared["scheduled_source_count"],
        "downloaded_source_count": download_manifest.get("downloaded_count", 0),
        "filings_discovered": len(reconciliation.current_records),
        "filings_new": reconciliation.new_count,
        "filings_changed": reconciliation.changed_count,
        "filings_incomplete": reconciliation.incomplete_count,
        "filings_skipped": reconciliation.unchanged_count,
        "selected_records": len(selected),
        "zip_source_count": len(zip_sources),
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "discovery_state_key": discovery_state_key(MANIFEST_PREFIX),
        "discovery_manifest_key": prepared["discovery_manifest_key"],
        "discovery_diff_key": prepared["discovery_diff_key"],
        "source_download_manifest_key": download_manifest.get("manifest_key"),
        "source_download_state_prefix": source_download_state_prefix(MANIFEST_PREFIX),
        "filing_catalog_key": reconciliation.catalog_key,
        "filing_diff_key": reconciliation.diff_key,
        "filing_state_key": reconciliation.state_key,
        "run_s3_key": ops_run_key,
        "chunks": chunks[:10],
        "next_stage": "normalized_parsing",
        "next_stage_implemented": True,
    }


def _resolve_source_catalog(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("source_catalog"), list):
        return [item for item in payload["source_catalog"] if isinstance(item, dict)]

    if FORM990_SOURCE_CATALOG_JSON:
        try:
            parsed = json.loads(FORM990_SOURCE_CATALOG_JSON)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass

    urls = _extract_index_urls(payload)
    return [{"index_url": url} for url in urls]


def _resolve_source_mode(payload: dict[str, Any]) -> str:
    mode = str(payload.get("source_mode") or FORM990_SOURCE_MODE or "configured").strip().lower()
    if mode in {"configured", "irs_page"}:
        return mode
    return "configured"


def _resolve_execution_mode(payload: dict[str, Any]) -> str:
    mode = str(payload.get("execution_mode") or FORM990_EXECUTION_MODE or "inline").strip().lower()
    if mode in {"inline", "orchestrated"}:
        return mode
    return "inline"


def _discover_sources(payload: dict[str, Any], source_mode: str, now: datetime) -> list[IrsYearSource]:
    if source_mode == "irs_page":
        page_url = str(payload.get("irs_downloads_page_url") or FORM990_IRS_DOWNLOADS_PAGE_URL or "").strip()
        if not page_url:
            raise ValueError("irs_page source_mode requires irs_downloads_page_url or FORM990_IRS_DOWNLOADS_PAGE_URL")
        return discover_irs_form990_sources(page_url=page_url, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS, now=now)
    return normalize_configured_sources(_resolve_source_catalog(payload), now=now)


def _persist_discovery_state(
    s3_client: Any,
    *,
    run_id: str,
    discovered_sources: list[IrsYearSource],
    diff_payload: dict[str, Any],
    now: datetime,
) -> dict[str, str]:
    state_payload = discovery_state_payload(discovered_sources, now=now)
    manifest_key = discovery_manifest_key(MANIFEST_PREFIX, run_id=run_id)
    diff_key = discovery_diff_key(MANIFEST_PREFIX, run_id=run_id)
    s3_client.put_object(Bucket=BUCKET, Key=discovery_state_key(MANIFEST_PREFIX), Body=json.dumps(state_payload, sort_keys=True).encode("utf-8"))
    s3_client.put_object(Bucket=BUCKET, Key=manifest_key, Body=json.dumps(state_payload, sort_keys=True).encode("utf-8"))
    s3_client.put_object(Bucket=BUCKET, Key=diff_key, Body=json.dumps(diff_payload, sort_keys=True).encode("utf-8"))
    _log_structured(
        "form990.discovery.state_persisted",
        discovery_sources=len(discovered_sources),
        state_key=discovery_state_key(MANIFEST_PREFIX),
        manifest_key=manifest_key,
        diff_key=diff_key,
    )
    return {"discovery_manifest_key": manifest_key, "discovery_diff_key": diff_key}


def _prepare_discovery_run(service: Form990IngestService, payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or FORM990_RUN_MODE or "incremental").strip().lower()
    if mode not in {"bootstrap", "incremental"}:
        raise ValueError("mode must be bootstrap or incremental")

    run_id = str(payload.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    source_mode = _resolve_source_mode(payload)
    now_dt = _resolve_now(payload)
    discovered_sources = _discover_sources(payload, source_mode=source_mode, now=now_dt)
    discovered_years = source_years(discovered_sources)
    policy = _build_policy_config(payload, mode=mode)
    selected_years, policy_metadata = select_target_years(discovered_years, policy, now=now_dt)
    if bool(payload.get("reconciliation_all_years", False)):
        policy_metadata["effective_mode"] = "reconciliation"
        policy_metadata["reconciliation_due"] = True

    previous_sources = _load_previous_discovery_state(service.s3)
    diff = diff_source_catalog(discovered_sources, previous_sources)
    diff_payload = {
        "generated_at": now_dt.isoformat(),
        "run_id": run_id,
        **diff.to_dict(),
    }
    persisted_keys = _persist_discovery_state(
        service.s3,
        run_id=run_id,
        discovered_sources=discovered_sources,
        diff_payload=diff_payload,
        now=now_dt,
    )
    selected_sources = select_sources_by_years(discovered_sources, set(selected_years))
    selected_source_dicts = [item.to_dict() for item in selected_sources]
    downloaded_state = load_downloaded_source_state(service.s3, BUCKET or "", MANIFEST_PREFIX)
    download_plan = plan_source_downloads(selected_source_dicts, downloaded_state)
    actionable_sources = download_plan["to_download"]
    return {
        "run_id": run_id,
        "mode": mode,
        "source_mode": source_mode,
        "source_catalog_count": len(discovered_sources),
        "source_years": discovered_years,
        "new_sources": len(diff.new_sources),
        "removed_sources": len(diff.removed_sources),
        "changed_sources": len(diff.changed_sources),
        "unchanged_sources": diff.unchanged_sources,
        "selected_source_count": len(selected_sources),
        "selected_sources": selected_source_dicts,
        "skipped_source_count": len(download_plan["skipped"]),
        "scheduled_source_count": len(actionable_sources),
        "scheduled_sources": actionable_sources,
        "skipped_sources": download_plan["skipped"],
        "policy": {
            "mode_requested": mode,
            "effective_mode": policy_metadata.get("effective_mode"),
            "target_years": selected_years,
            "incremental_year_window": policy.incremental_year_window,
            "reconciliation_enabled": policy.reconciliation_enabled,
            "reconciliation_cadence_days": policy.reconciliation_cadence_days,
            "reconciliation_due": policy_metadata.get("reconciliation_due"),
            "fallback_used": policy_metadata.get("fallback_used"),
            "resume": False,
            "batch_size": 0,
            "retry_count": FORM990_RETRY_COUNT,
        },
        **persisted_keys,
    }


def _build_policy_config(payload: dict[str, Any], mode: str) -> IngestPolicyConfig:
    target_years = payload.get("target_years")
    years: list[str] = []
    if isinstance(target_years, list):
        years = [str(item).strip() for item in target_years if str(item).strip()]
    elif FORM990_TARGET_YEARS:
        years = [part.strip() for part in FORM990_TARGET_YEARS.split(",") if part.strip()]
    return IngestPolicyConfig(
        mode=mode,
        incremental_year_window=int(payload.get("incremental_year_window") or FORM990_INCREMENTAL_YEAR_WINDOW),
        target_years=tuple(years),
        reconciliation_enabled=bool(payload.get("reconciliation_enabled", FORM990_RECONCILIATION_ENABLED)),
        reconciliation_cadence_days=int(payload.get("reconciliation_cadence_days") or FORM990_RECONCILIATION_CADENCE_DAYS),
        last_reconciliation_at=str(payload.get("last_reconciliation_at") or FORM990_LAST_RECONCILIATION_AT or "") or None,
        force_reconciliation=bool(payload.get("force_reconciliation", False)),
    )


def _download_selected_sources(service: Form990IngestService, prepared: dict[str, Any]) -> dict[str, Any]:
    if not prepared["scheduled_sources"]:
        return {"manifest_key": None, "downloaded_count": 0, "downloads": []}
    return execute_source_download_batch(
        sources=prepared["scheduled_sources"],
        bucket=BUCKET or "",
        raw_source_prefix=RAW_SOURCE_PREFIX,
        manifest_prefix=MANIFEST_PREFIX,
        s3_client=service.s3,
        run_id=prepared["run_id"],
        batch_index=0,
        timeout_seconds=FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
    )


def _resolve_selected_csv_sources(selected_sources: list[dict[str, Any]], downloaded_state: list[dict[str, Any]]) -> list[dict[str, Any]]:
    downloaded_by_identity = {
        (
            str(item.get("source_year") or "").strip(),
            str(item.get("source_kind") or "").strip(),
            str(item.get("source_archive_key") or "").strip(),
        ): item
        for item in downloaded_state
        if isinstance(item, dict)
    }
    resolved: list[dict[str, Any]] = []
    for source in selected_sources:
        if not isinstance(source, dict) or str(source.get("source_kind") or "").strip() != "csv_index":
            continue
        identity = (
            str(source.get("source_year") or "").strip(),
            str(source.get("source_kind") or "").strip(),
            str(source.get("source_archive_key") or "").strip(),
        )
        downloaded = downloaded_by_identity.get(identity)
        if not downloaded or not downloaded.get("raw_source_s3_key"):
            continue
        resolved.append({**source, **downloaded})
    return resolved


def _build_zip_loader(s3_client: Any, selected_records: list[dict[str, Any]], downloaded_state: list[dict[str, Any]]) -> ZipBackedXmlLoader | None:
    zip_sources = select_zip_sources_for_records(selected_records, downloaded_state)
    if not zip_sources:
        return None
    return ZipBackedXmlLoader(
        s3_client=s3_client,
        bucket=BUCKET or "",
        zip_sources=zip_sources,
        allow_url_fallback=FORM990_ZIP_URL_FALLBACK_ENABLED,
        url_timeout_seconds=FORM990_ZIP_FETCH_TIMEOUT_SECONDS,
        max_xml_file_size_bytes=FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES,
    )


def _resolve_now(payload: dict[str, Any]) -> datetime:
    raw = payload.get("now")
    if isinstance(raw, str) and raw.strip():
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _load_legacy_index_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for url in _extract_index_urls(payload):
        year = _year_from_url(url)
        archive = url.rstrip("/").split("/")[-1] or "index"
        for item in fetch_index_records(index_url=url, source_year=year, source_archive=archive, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS):
            records.append(_record_to_dict(item))
    return _apply_index_filters(records, payload)


def _parse_event_payload(event: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(event, dict):
        return {}
    payload = dict(event)
    if event.get("body"):
        try:
            body = json.loads(str(event.get("body")))
            if isinstance(body, dict):
                payload.update(body)
        except json.JSONDecodeError:
            raise ValueError("Request body must be valid JSON")
    return payload


def _extract_index_urls(event: dict | None) -> list[str]:
    urls: list[str] = []
    if isinstance(event, dict):
        raw = event.get("index_urls")
        if isinstance(raw, list):
            urls.extend([str(item).strip() for item in raw if str(item).strip()])
        single = event.get("index_url")
        if isinstance(single, str) and single.strip():
            urls.append(single.strip())
    if INDEX_URLS:
        urls.extend([part.strip() for part in INDEX_URLS.split(",") if part.strip()])
    if INDEX_URL:
        urls.append(INDEX_URL)

    deduped: list[str] = []
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _year_from_url(url: str) -> str:
    for token in url.replace("-", "_").split("_"):
        if token.isdigit() and len(token) == 4 and token.startswith("20"):
            return token
    return str(datetime.now(timezone.utc).year)


def _apply_index_filters(payload: list[dict], event: dict) -> list[dict]:
    tax_year = str(event.get("tax_year") or "").strip() or None
    limit_value = event.get("limit")
    limit: int | None
    if limit_value is None:
        limit = None
    else:
        try:
            limit = int(limit_value)
        except (TypeError, ValueError):
            limit = None
    eins = _extract_ein_filter(event)

    filtered = payload
    if tax_year:
        filtered = [item for item in filtered if str(item.get("tax_year") or item.get("TaxYr") or "").strip() == tax_year]
    if eins:
        filtered = [item for item in filtered if str(item.get("ein") or item.get("EIN") or "").strip() in eins]
    if limit is not None and limit >= 0:
        filtered = filtered[:limit]
    return filtered


def _extract_ein_filter(event: dict) -> set[str]:
    filter_values: list[str] = []
    single = event.get("ein")
    if isinstance(single, str) and single.strip():
        filter_values.append(single.strip())
    many = event.get("eins")
    if isinstance(many, list):
        filter_values.extend([str(item).strip() for item in many if str(item).strip()])
    return set(filter_values)


def _record_to_dict(record: Any) -> dict[str, Any]:
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


def _persist_ingest_ops_run(service: Form990IngestService, response: dict[str, Any], selected_records: list[dict[str, Any]]) -> None:
    bucket = OPS_METADATA_BUCKET or BUCKET or ""
    if not bucket:
        return
    run_id = str(response.get("run_id") or "")
    if not run_id:
        return
    store = S3RunStore(bucket=bucket, prefix=OPS_METADATA_PREFIX, s3_client=service.s3)
    years_checked = [str(year).strip() for year in response.get("source_years", []) if str(year).strip()]
    summary = {
        "ingest_run_id": run_id,
        "mode": response.get("mode"),
        "stage": response.get("stage"),
        "started_at": None,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": response.get("status"),
        "years_checked": years_checked,
        "source_catalog_count": response.get("source_catalog_count"),
        "sources_discovered": response.get("sources_discovered"),
        "sources_new": response.get("new_sources"),
        "sources_removed": response.get("removed_sources"),
        "sources_changed": response.get("changed_sources"),
        "sources_unchanged": response.get("unchanged_sources"),
        "scheduled_source_count": response.get("scheduled_source_count"),
        "skipped_source_count": response.get("skipped_source_count"),
        "downloaded_source_count": response.get("downloaded_source_count"),
        "filings_discovered": response.get("filings_discovered"),
        "filings_new": response.get("filings_new"),
        "filings_changed": response.get("filings_changed"),
        "filings_incomplete": response.get("filings_incomplete"),
        "filings_skipped": response.get("filings_skipped"),
        "filings_failed": response.get("failed_count"),
        "discovery_state_key": response.get("discovery_state_key"),
        "discovery_manifest_key": response.get("discovery_manifest_key"),
        "discovery_diff_key": response.get("discovery_diff_key"),
        "source_download_manifest_key": response.get("source_download_manifest_key"),
        "source_download_state_prefix": response.get("source_download_state_prefix"),
        "filing_catalog_key": response.get("filing_catalog_key"),
        "filing_diff_key": response.get("filing_diff_key"),
        "filing_state_key": response.get("filing_state_key"),
        "checkpoint_key": response.get("checkpoint_key"),
        "resume_supported": False,
        "safe_error_summary": {"count": int(response.get("failed_count") or 0), "samples": []},
        "policy": response.get("policy"),
    }
    store.write_ingest_run(run_id, summary)
    if selected_records:
        store.write_ingest_filings(run_id, selected_records)

def _load_previous_discovery_state(s3_client: Any) -> list[dict[str, Any]]:
    try:
        response = s3_client.get_object(Bucket=BUCKET, Key=discovery_state_key(MANIFEST_PREFIX))
        body = response["Body"].read().decode("utf-8")
        payload = json.loads(body)
        sources = payload.get("sources")
        if isinstance(sources, list):
            return [item for item in sources if isinstance(item, dict)]
    except Exception:
        return []
    return []


def _log_structured(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    try:
        LOGGER.info(json.dumps(payload, sort_keys=True))
    except Exception:
        LOGGER.info("%s %s", event, fields)
