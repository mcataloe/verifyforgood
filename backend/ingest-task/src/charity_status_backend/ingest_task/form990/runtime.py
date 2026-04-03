"""Backend-owned Form 990 discovery and orchestration runtime."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import boto3
from charity_status.api import build_response_context, error_response, json_response
from charity_status.form990 import Form990IngestService
from charity_status.form990.discovery import fetch_index_records
from charity_status.form990.filing_reconciliation import reconcile_filing_catalog, update_filing_state_from_ingest_result
from charity_status.form990.hardening import classify_error, validate_runtime_config
from charity_status.form990.irs_page_discovery import (
    discover_irs_form990_sources,
)
from charity_status.form990.source_downloads import execute_source_download_batch, load_downloaded_source_state, plan_source_downloads
from charity_status.form990.policy import IngestPolicyConfig, select_target_years
from charity_status.form990.source_catalog import (
    Form990SourceArtifact,
    SOURCE_KIND_ZIP_ARCHIVE,
    compute_source_signature,
    derive_source_archive_key,
    discovery_state_payload,
    diff_source_catalog,
    normalize_configured_sources,
    select_sources_by_years,
    source_years,
)
from charity_status.form990.static_source_discovery import discover_static_form990_sources
from charity_status.form990.teos_batch_processing import (
    PROCESSING_STATUS_PENDING,
    process_teos_manifest_batch,
    should_process_teos_batch,
)
from charity_status.form990.teos_manifest import S3TeosZipManifestRepository, TeosZipManifestRecord
from charity_status.form990.teos_zip_probe import TeosZipProbeFailure, TeosZipProbeResult, probe_teos_zip_metadata
from charity_status.form990.teos_zip_raw_sync import TeosZipExtractionError, extract_teos_zip_from_s3
from charity_status.form990.teos_zip_discovery import fetch_teos_download_page_html, parse_teos_zip_links
from charity_status.form990.zip_selected_processing import ZipBackedXmlLoader, select_zip_sources_for_records
from charity_status.ops import S3RunStore
from charity_status.form990.storage import checkpoint_key, discovery_diff_key, discovery_manifest_key, discovery_state_key, source_download_state_prefix, state_manifest_key, teos_zip_manifest_state_prefix
from charity_status_backend.ingest_task.persistence import build_form990_nonprofit_persistence_service

BUCKET = os.environ.get("BUCKET")
RAW_PREFIX = os.environ.get("FORM990_RAW_PREFIX", "form990/raw/")
TEOS_RAW_XML_PREFIX = os.environ.get("FORM990_TEOS_RAW_XML_PREFIX", "teos/raw/xml/").strip()
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
FORM990_SOURCE_MODE = os.environ.get("FORM990_SOURCE_MODE", "static_manifest").strip().lower()
FORM990_ENABLE_NEXT_YEAR_GENERATION = os.environ.get("FORM990_ENABLE_NEXT_YEAR_GENERATION", "true").lower() == "true"
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
logging.getLogger().setLevel(logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
VALID_FORM990_SOURCE_MODES = {"configured", "irs_page", "static_manifest"}


class Form990OperationalError(RuntimeError):
    pass


def handler(event, context):
    api_context = build_response_context(event, context, plan="internal")

    def respond(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
        return json_response(status_code, payload, response_context=api_context)

    def fail(status_code: int, message: str, code: str | None = None) -> dict[str, Any]:
        return error_response(status_code, message, response_context=api_context, code=code)

    if not BUCKET:
        return fail(500, "BUCKET environment variable is required")
    config_errors = _validate_handler_config()
    if config_errors:
        return fail(500, "; ".join(config_errors))

    try:
        payload = _parse_event_payload(event)
    except ValueError as exc:
        return fail(400, str(exc))
    service = Form990IngestService(
        bucket=BUCKET,
        raw_prefix=RAW_PREFIX,
        metadata_prefix=METADATA_PREFIX,
        manifest_prefix=MANIFEST_PREFIX,
        metrics_prefix=METRICS_PREFIX,
        governance_prefix=GOVERNANCE_PREFIX,
        quality_prefix=QUALITY_PREFIX,
        relationships_prefix=RELATIONSHIPS_PREFIX,
        nonprofit_persistence_service=build_form990_nonprofit_persistence_service(),
    )

    explicit_records = payload.get("records")
    if explicit_records is not None:
        if not isinstance(explicit_records, list):
            return fail(400, "records must be an array")
        result = service.ingest_index_payload(payload=explicit_records, download_raw=bool(payload.get("download_raw", DEFAULT_DOWNLOAD_RAW)))
        update_filing_state_from_ingest_result(
            s3_client=service.s3,
            bucket=BUCKET or "",
            manifest_prefix=MANIFEST_PREFIX,
            input_records=explicit_records,
            ingest_result=result,
        )
        result["filing_state_key"] = state_manifest_key(MANIFEST_PREFIX)
        return respond(200, result)

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
            return respond(200, result)

    try:
        execution_mode = _resolve_execution_mode(payload)
        _log_structured(
            "form990.run.start",
            execution_mode=execution_mode,
            source_mode=str(payload.get("source_mode") or FORM990_SOURCE_MODE),
            mode=str(payload.get("mode") or FORM990_RUN_MODE),
        )
        if execution_mode == "orchestrated":
            result = _run_discovery_orchestrated(service, payload)
        else:
            result = _run_discovery_ingestion(service, payload)
        return respond(200, result)
    except ValueError as exc:
        return fail(400, str(exc))
    except Form990OperationalError as exc:
        _log_structured("form990.run.failed", error_type="operational_error", error=str(exc))
        return fail(500, str(exc))
    except Exception as exc:
        _log_structured("form990.run.failed", error_type=classify_error(exc), error=str(exc))
        return fail(500, "Form 990 ingest failed")


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
    teos_batches = _load_current_teos_manifest_records(service, prepared)
    use_teos_batch_processing = _has_teos_processing_state(teos_batches)
    zip_loader: ZipBackedXmlLoader | None = None
    source_batch_results: list[dict[str, Any]] = []
    processable_teos_batches: list[TeosZipManifestRecord] = []
    if use_teos_batch_processing:
        processable_teos_batches = [item for item in teos_batches if should_process_teos_batch(item)]
        source_batch_results = [
            _process_teos_batch_for_response(
                service=service,
                manifest_record=record,
            )
            for record in processable_teos_batches
        ]
        ingest_result = _aggregate_source_batch_results(source_batch_results)
    elif selected_records:
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
        "stage": "source_batch_processing" if use_teos_batch_processing else "csv_reconciliation",
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
        "teos_zip_extracted_file_count": download_manifest.get("extracted_file_count", 0),
        "teos_zip_manifest": prepared["teos_zip_manifest"],
        "discovery_state_key": discovery_state_key(MANIFEST_PREFIX),
        "discovery_manifest_key": prepared["discovery_manifest_key"],
        "discovery_diff_key": prepared["discovery_diff_key"],
        "source_download_manifest_key": download_manifest.get("manifest_key"),
        "source_download_manifest_keys": download_manifest.get("manifest_keys", []),
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
        "next_stage": "normalized_parsing" if use_teos_batch_processing else "zip_extraction",
        "next_stage_implemented": bool(use_teos_batch_processing),
        "source_batch_count": len(teos_batches),
        "processable_source_batch_count": len(processable_teos_batches),
        "processed_source_batch_count": len(source_batch_results),
        "source_batches": source_batch_results[:10],
        "selected_records": len(selected_records),
        "selected_filings": selected_records[:10],
        "processed_records": int(ingest_result.get("records_processed") or 0),
        "parsed_count": int(ingest_result.get("parsed_count") or 0),
        "failed_count": int(ingest_result.get("failed_count") or 0),
        "manifest_s3_keys": ingest_result.get("manifest_s3_keys", []),
        "zip_resolved_count": int(zip_loader.zip_extracted_count) if zip_loader else 0,
        "zip_fallback_url_count": int(zip_loader.url_fallback_count) if zip_loader else 0,
        "zip_unresolved_count": int(zip_loader.unresolved_count) if zip_loader else 0,
        "batch_count": len(processable_teos_batches) if use_teos_batch_processing else (1 if selected_records else 0),
        "checkpoint_key": checkpoint_key(MANIFEST_PREFIX),
        "manifest_s3_key": ingest_result.get("manifest_s3_key"),
    }
    _write_checkpoint(service.s3, response)
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
        teos_zip_extracted_file_count=download_manifest.get("extracted_file_count", 0),
        filings_discovered=len(reconciliation.current_records),
        selected_records=len(selected_records),
        parsed_count=int(ingest_result.get("parsed_count") or 0),
        source_batch_count=len(teos_batches),
        processable_source_batch_count=len(processable_teos_batches),
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
    teos_batches = _load_current_teos_manifest_records(service, prepared)
    use_teos_batch_processing = _has_teos_processing_state(teos_batches)
    processable_teos_batches = [item for item in teos_batches if should_process_teos_batch(item)]
    selected_records = reconciliation.selected_records
    chunk_size = int(payload.get("chunk_size") or FORM990_CHUNK_SIZE)
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")

    queue = boto3.client("sqs")
    bucket = OPS_METADATA_BUCKET or BUCKET or ""
    prefix = OPS_METADATA_PREFIX.strip("/") or "ops"
    chunks = []
    chunk_index = 0
    if use_teos_batch_processing:
        batch_chunk: list[TeosZipManifestRecord] = []
        for record in processable_teos_batches:
            batch_chunk.append(record)
            if len(batch_chunk) < chunk_size:
                continue
            chunks.append(
                _queue_source_batch_chunk(
                    service=service,
                    queue=queue,
                    bucket=bucket,
                    prefix=prefix,
                    run_id=run_id,
                    chunk_index=chunk_index,
                    source_batches=batch_chunk,
                    mode=prepared["mode"],
                    source_mode=prepared["source_mode"],
                )
            )
            batch_chunk = []
            chunk_index += 1
        if batch_chunk:
            chunks.append(
                _queue_source_batch_chunk(
                    service=service,
                    queue=queue,
                    bucket=bucket,
                    prefix=prefix,
                    run_id=run_id,
                    chunk_index=chunk_index,
                    source_batches=batch_chunk,
                    mode=prepared["mode"],
                    source_mode=prepared["source_mode"],
                )
            )
    else:
        chunk: list[dict[str, Any]] = []
        for record in selected_records:
            chunk.append(_record_to_dict(record))
            if len(chunk) < chunk_size:
                continue
            chunks.append(
                _queue_filing_records_chunk(
                    service=service,
                    queue=queue,
                    bucket=bucket,
                    prefix=prefix,
                    run_id=run_id,
                    chunk_index=chunk_index,
                    records=chunk,
                    mode=prepared["mode"],
                    source_mode=prepared["source_mode"],
                )
            )
            chunk = []
            chunk_index += 1
        if chunk:
            chunks.append(
                _queue_filing_records_chunk(
                    service=service,
                    queue=queue,
                    bucket=bucket,
                    prefix=prefix,
                    run_id=run_id,
                    chunk_index=chunk_index,
                    records=chunk,
                    mode=prepared["mode"],
                    source_mode=prepared["source_mode"],
                )
            )

    run_store = S3RunStore(bucket=bucket, prefix=prefix, s3_client=service.s3)
    selected_count = len(selected_records)
    source_batch_count = len(teos_batches)
    processable_source_batch_count = len(processable_teos_batches)
    chunk_count = len(chunks)
    sample_chunks = chunks[:10]
    run_summary = {
        "ingest_run_id": run_id,
        "mode": prepared["mode"],
        "execution_mode": "orchestrated",
        "stage": "source_batch_processing" if use_teos_batch_processing else "csv_reconciliation",
        "status": "queued" if chunk_count else "success",
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
        "teos_zip_extracted_file_count": download_manifest.get("extracted_file_count", 0),
        "teos_zip_manifest": prepared["teos_zip_manifest"],
        "filings_discovered": len(reconciliation.current_records),
        "filings_new": reconciliation.new_count,
        "filings_changed": reconciliation.changed_count,
        "filings_incomplete": reconciliation.incomplete_count,
        "filings_skipped": reconciliation.unchanged_count,
        "selected_records": selected_count,
        "source_batch_count": source_batch_count,
        "processable_source_batch_count": processable_source_batch_count,
        "chunk_size": chunk_size,
        "chunk_count": chunk_count,
        "chunk_status_counts": {"queued": chunk_count, "running": 0, "succeeded": 0, "failed": 0, "dlq": 0},
        "policy": prepared["policy"],
        "discovery_state_key": discovery_state_key(MANIFEST_PREFIX),
        "discovery_manifest_key": prepared["discovery_manifest_key"],
        "discovery_diff_key": prepared["discovery_diff_key"],
        "source_download_manifest_key": download_manifest.get("manifest_key"),
        "source_download_manifest_keys": download_manifest.get("manifest_keys", []),
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
        Body=json.dumps({"ingest_run_id": run_id, "chunk_count": chunk_count, "status": "queued"}, sort_keys=True).encode("utf-8"),
    )
    _write_checkpoint(
        service.s3,
        {
            "run_id": run_id,
            "stage": "source_batch_processing" if use_teos_batch_processing else "zip_extraction",
            "status": "queued" if chunk_count else "success",
            "chunk_count": chunk_count,
            "selected_records": selected_count,
            "filing_state_key": reconciliation.state_key,
        },
    )

    return {
        "status": "queued" if chunk_count else "success",
        "stage": "source_batch_processing" if use_teos_batch_processing else "zip_extraction",
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
        "teos_zip_manifest": prepared["teos_zip_manifest"],
        "filings_discovered": len(reconciliation.current_records),
        "filings_new": reconciliation.new_count,
        "filings_changed": reconciliation.changed_count,
        "filings_incomplete": reconciliation.incomplete_count,
        "filings_skipped": reconciliation.unchanged_count,
        "selected_records": selected_count,
        "source_batch_count": source_batch_count,
        "processable_source_batch_count": processable_source_batch_count,
        "chunk_size": chunk_size,
        "chunk_count": chunk_count,
        "discovery_state_key": discovery_state_key(MANIFEST_PREFIX),
        "discovery_manifest_key": prepared["discovery_manifest_key"],
        "discovery_diff_key": prepared["discovery_diff_key"],
        "source_download_manifest_key": download_manifest.get("manifest_key"),
        "source_download_state_prefix": source_download_state_prefix(MANIFEST_PREFIX),
        "filing_catalog_key": reconciliation.catalog_key,
        "filing_diff_key": reconciliation.diff_key,
        "filing_state_key": reconciliation.state_key,
        "run_s3_key": ops_run_key,
        "chunks": sample_chunks,
        "next_stage": "normalized_parsing",
        "next_stage_implemented": True,
    }


def _queue_filing_records_chunk(
    *,
    service: Form990IngestService,
    queue: Any,
    bucket: str,
    prefix: str,
    run_id: str,
    chunk_index: int,
    records: list[dict[str, Any]],
    mode: str,
    source_mode: str,
) -> dict[str, Any]:
    chunk_id = f"{run_id}-{chunk_index:05d}"
    chunk_key = f"{prefix}/form990-runs/{run_id}/chunks/{chunk_id}.json"
    chunk_payload = {
        "run_id": run_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "task_type": "filing_records",
        "stage": "zip_extraction",
        "records": records,
        "mode": mode,
        "source_mode": source_mode,
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
    return {"chunk_id": chunk_id, "chunk_index": chunk_index, "record_count": len(records), "chunk_s3_key": chunk_key}


def _queue_source_batch_chunk(
    *,
    service: Form990IngestService,
    queue: Any,
    bucket: str,
    prefix: str,
    run_id: str,
    chunk_index: int,
    source_batches: list[TeosZipManifestRecord],
    mode: str,
    source_mode: str,
) -> dict[str, Any]:
    chunk_id = f"{run_id}-{chunk_index:05d}"
    chunk_key = f"{prefix}/form990-runs/{run_id}/chunks/{chunk_id}.json"
    chunk_payload = {
        "run_id": run_id,
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "task_type": "source_batch",
        "stage": "source_batch_processing",
        "source_batches": [_teos_batch_to_dict(item) for item in source_batches],
        "mode": mode,
        "source_mode": source_mode,
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
    return {
        "chunk_id": chunk_id,
        "chunk_index": chunk_index,
        "source_batch_count": len(source_batches),
        "chunk_s3_key": chunk_key,
    }


def _load_current_teos_manifest_records(service: Form990IngestService, prepared: dict[str, Any]) -> list[TeosZipManifestRecord]:
    repository = S3TeosZipManifestRepository(
        s3_client=service.s3,
        bucket=BUCKET or "",
        manifest_prefix=MANIFEST_PREFIX,
        raw_xml_prefix=TEOS_RAW_XML_PREFIX,
    )
    records: list[TeosZipManifestRecord] = []
    seen: set[tuple[str, str]] = set()
    for year in prepared.get("target_years", []):
        for record in repository.load_year_records(str(year)):
            identity = (record.tax_year, record.zip_basename)
            if identity in seen:
                continue
            seen.add(identity)
            records.append(record)
    return sorted(records, key=lambda item: (item.tax_year, item.zip_basename))


def _has_teos_processing_state(records: list[TeosZipManifestRecord]) -> bool:
    return any(
        str(record.extraction_status or "").strip().lower() == "extracted"
        or str(record.download_status or "").strip().lower() == "failed"
        or str(record.extraction_status or "").strip().lower() == "failed"
        for record in records
    )


def _process_teos_batch_for_response(
    *,
    service: Form990IngestService,
    manifest_record: TeosZipManifestRecord,
) -> dict[str, Any]:
    repository = S3TeosZipManifestRepository(
        s3_client=service.s3,
        bucket=BUCKET or "",
        manifest_prefix=MANIFEST_PREFIX,
        raw_xml_prefix=TEOS_RAW_XML_PREFIX,
    )
    result = process_teos_manifest_batch(
        service=service,
        repository=repository,
        manifest_record=manifest_record,
        bucket=BUCKET or "",
        manifest_prefix=MANIFEST_PREFIX,
    )
    return {
        "tax_year": result.manifest_record.tax_year,
        "zip_basename": result.manifest_record.zip_basename,
        "processing_status": result.manifest_record.processing_status,
        "destination_raw_s3_prefix": result.manifest_record.destination_raw_s3_prefix,
        "source_object_count": len(result.source_object_keys),
        "records_processed": int(result.ingest_result.get("records_processed") or 0),
        "parsed_count": int(result.ingest_result.get("parsed_count") or 0),
        "failed_count": int(result.ingest_result.get("failed_count") or 0),
        "manifest_s3_key": result.ingest_result.get("manifest_s3_key"),
        "last_error": result.manifest_record.last_error,
        "skipped": result.skipped,
    }


def _aggregate_source_batch_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "status": "success",
            "records_processed": 0,
            "parsed_count": 0,
            "failed_count": 0,
            "manifest_s3_key": None,
            "manifest_s3_keys": [],
            "filing_records_s3_key": None,
            "metrics_s3_key": None,
            "governance_s3_key": None,
            "quality_s3_key": None,
            "relationships_s3_key": None,
            "records": [],
        }
    failed_batches = sum(1 for item in results if int(item.get("failed_count") or 0) > 0)
    parsed_count = sum(int(item.get("parsed_count") or 0) for item in results)
    failed_count = sum(int(item.get("failed_count") or 0) for item in results)
    records_processed = sum(int(item.get("records_processed") or 0) for item in results)
    manifest_keys = [str(item.get("manifest_s3_key") or "").strip() for item in results if str(item.get("manifest_s3_key") or "").strip()]
    if failed_batches and parsed_count:
        status = "partial_success"
    elif failed_batches:
        status = "failed"
    else:
        status = "success"
    return {
        "status": status,
        "records_processed": records_processed,
        "parsed_count": parsed_count,
        "failed_count": failed_count,
        "manifest_s3_key": manifest_keys[0] if manifest_keys else None,
        "manifest_s3_keys": manifest_keys,
        "filing_records_s3_key": None,
        "metrics_s3_key": None,
        "governance_s3_key": None,
        "quality_s3_key": None,
        "relationships_s3_key": None,
        "records": [],
    }


def _teos_batch_to_dict(record: TeosZipManifestRecord) -> dict[str, Any]:
    return {
        "tax_year": record.tax_year,
        "zip_basename": record.zip_basename,
        "destination_raw_s3_prefix": record.destination_raw_s3_prefix,
        "download_status": record.download_status,
        "extraction_status": record.extraction_status,
        "processing_status": record.processing_status,
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
    explicit_mode = str(payload.get("source_mode") or "").strip().lower()
    if explicit_mode:
        if explicit_mode not in VALID_FORM990_SOURCE_MODES:
            raise ValueError(
                "source_mode must be one of configured, static_manifest, or irs_page"
            )
        return explicit_mode

    env_mode = str(FORM990_SOURCE_MODE or "static_manifest").strip().lower()
    if _has_manual_source_inputs(payload):
        return "configured"
    if env_mode in VALID_FORM990_SOURCE_MODES:
        if env_mode == "static_manifest":
            return env_mode
        if env_mode in {"configured", "irs_page"} and not FORM990_SOURCE_CATALOG_JSON and not INDEX_URL and not INDEX_URLS:
            return env_mode
        if env_mode == "configured":
            return "configured"
    if FORM990_SOURCE_CATALOG_JSON or INDEX_URL or INDEX_URLS:
        return "configured"
    return "static_manifest"


def _has_manual_source_inputs(payload: dict[str, Any]) -> bool:
    if isinstance(payload.get("source_catalog"), list):
        return True
    if _extract_index_urls(payload):
        return True
    if FORM990_SOURCE_CATALOG_JSON:
        try:
            parsed = json.loads(FORM990_SOURCE_CATALOG_JSON)
        except json.JSONDecodeError:
            return bool(INDEX_URL or INDEX_URLS)
        return isinstance(parsed, list) and any(isinstance(item, dict) for item in parsed)
    return False


def _resolve_execution_mode(payload: dict[str, Any]) -> str:
    mode = str(payload.get("execution_mode") or FORM990_EXECUTION_MODE or "inline").strip().lower()
    if mode in {"inline", "orchestrated"}:
        return mode
    return "inline"


def _discover_sources(payload: dict[str, Any], source_mode: str, now: datetime) -> list[Form990SourceArtifact]:
    if source_mode == "static_manifest":
        try:
            return discover_static_form990_sources(
                now=now,
                enable_next_year_generation=FORM990_ENABLE_NEXT_YEAR_GENERATION,
            )
        except FileNotFoundError as exc:
            raise Form990OperationalError(
                "Form 990 static manifest is missing; expected infrastructure/charity_status/form990/Form990Links.txt in the deployed package"
            ) from exc
        except ValueError as exc:
            raise Form990OperationalError(f"Form 990 static manifest is malformed: {exc}") from exc
    if source_mode == "irs_page":
        # Legacy compatibility path only. Normal runtime discovery uses the repo-backed static manifest.
        page_url = str(payload.get("irs_downloads_page_url") or FORM990_IRS_DOWNLOADS_PAGE_URL or "").strip()
        if not page_url:
            raise ValueError("irs_page source_mode requires irs_downloads_page_url or FORM990_IRS_DOWNLOADS_PAGE_URL")
        return discover_irs_form990_sources(page_url=page_url, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS, now=now)
    return normalize_configured_sources(_resolve_source_catalog(payload), now=now)


def _persist_discovery_state(
    s3_client: Any,
    *,
    run_id: str,
    discovered_sources: list[Form990SourceArtifact],
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
    teos_zip_manifest = _sync_teos_zip_manifest_state(
        service.s3,
        run_id=run_id,
        target_years=selected_years,
        now=now_dt,
    )
    teos_zip_manifest_records = tuple(item for item in teos_zip_manifest.pop("_records", ()) if isinstance(item, TeosZipManifestRecord))
    selected_sources = select_sources_by_years(discovered_sources, set(selected_years))
    selected_source_dicts = _merge_selected_sources_with_teos_manifest(
        selected_sources=[item.to_dict() for item in selected_sources],
        teos_zip_manifest_records=teos_zip_manifest_records,
        target_years=selected_years,
    )
    downloaded_state = load_downloaded_source_state(service.s3, BUCKET or "", MANIFEST_PREFIX)
    download_plan = _plan_selected_source_downloads(
        selected_sources=selected_source_dicts,
        downloaded_state=downloaded_state,
        teos_zip_manifest_records=teos_zip_manifest_records,
    )
    actionable_sources = download_plan["to_download"]
    _log_structured(
        "form990.discovery.prepare",
        run_id=run_id,
        mode=mode,
        source_mode=source_mode,
        sources_discovered=len(discovered_sources),
        new_sources=len(diff.new_sources),
        changed_sources=len(diff.changed_sources),
        removed_sources=len(diff.removed_sources),
        selected_source_count=len(selected_sources),
        scheduled_source_count=len(actionable_sources),
        skipped_source_count=len(download_plan["skipped"]),
        teos_zip_discovered_count=teos_zip_manifest.get("discovered_count", 0),
    )
    return {
        "run_id": run_id,
        "mode": mode,
        "source_mode": source_mode,
        "source_catalog_count": len(discovered_sources),
        "source_years": discovered_years,
        "target_years": selected_years,
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
        "teos_zip_manifest": teos_zip_manifest,
        "teos_zip_manifest_records": teos_zip_manifest_records,
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


def _sync_teos_zip_manifest_state(
    s3_client: Any,
    *,
    run_id: str,
    target_years: list[str],
    now: datetime,
) -> dict[str, Any]:
    summary = {
        "run_id": run_id,
        "checked_at": now.isoformat(),
        "state_prefix": teos_zip_manifest_state_prefix(MANIFEST_PREFIX),
        "catalog_keys": [],
        "target_years": list(target_years),
        "discovered_count": 0,
        "new_count": 0,
        "changed_count": 0,
        "removed_count": 0,
        "unchanged_count": 0,
        "scheduled_download_count": 0,
        "skipped_download_count": 0,
        "probe_failed_count": 0,
        "error": None,
    }
    page_url = FORM990_IRS_DOWNLOADS_PAGE_URL.strip()
    if not page_url or not target_years:
        return summary

    try:
        html = fetch_teos_download_page_html(page_url=page_url, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS)
        discovered_sources = []
        for year in target_years:
            discovered_sources.extend(parse_teos_zip_links(html, page_url=page_url, target_year=year, now=now))
        probe_results = _probe_teos_zip_sources(discovered_sources, now=now)
        repository = S3TeosZipManifestRepository(
            s3_client=s3_client,
            bucket=BUCKET or "",
            manifest_prefix=MANIFEST_PREFIX,
            raw_xml_prefix=TEOS_RAW_XML_PREFIX,
        )
        manifest_summary = repository.sync_discovered_records(
            run_id=run_id,
            discovered_sources=discovered_sources,
            probe_results=probe_results,
            checked_years=target_years,
            checked_at=now,
        )
        return {
            **summary,
            **manifest_summary.to_dict(),
            "_records": manifest_summary.records,
        }
    except Exception as exc:
        _log_structured(
            "form990.teos_zip_manifest.sync_failed",
            run_id=run_id,
            target_years=target_years,
            page_url=page_url,
            error=str(exc),
        )
        return {**summary, "error": str(exc)}


def _probe_teos_zip_sources(
    discovered_sources: list[Any],
    *,
    now: datetime,
) -> dict[tuple[str, str], TeosZipProbeResult | TeosZipProbeFailure]:
    outcomes: dict[tuple[str, str], TeosZipProbeResult | TeosZipProbeFailure] = {}
    for source in discovered_sources:
        if not hasattr(source, "tax_year"):
            continue
        tax_year = str(getattr(source, "tax_year", "") or "").strip()
        zip_basename = str(getattr(source, "zip_basename", "") or "").strip()
        source_url = str(getattr(source, "source_url", "") or "").strip()
        if not tax_year or not zip_basename or not source_url:
            continue
        identity = (tax_year, zip_basename)
        try:
            outcomes[identity] = probe_teos_zip_metadata(
                source_url,
                timeout_seconds=FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
                now=now,
            )
        except Exception as exc:
            _log_structured(
                "form990.teos_zip_manifest.probe_failed",
                tax_year=tax_year,
                zip_basename=zip_basename,
                source_url=source_url,
                error=str(exc),
            )
            outcomes[identity] = TeosZipProbeFailure(
                source_url=source_url,
                checked_at=now.isoformat(),
                error=str(exc),
            )
    return outcomes


def _plan_selected_source_downloads(
    *,
    selected_sources: list[dict[str, Any]],
    downloaded_state: list[dict[str, Any]],
    teos_zip_manifest_records: tuple[TeosZipManifestRecord, ...],
) -> dict[str, list[dict[str, Any]]]:
    manifest_lookup = {
        (record.tax_year, derive_source_archive_key(record.zip_basename)): record
        for record in teos_zip_manifest_records
    }
    downloaded_by_identity = {
        _source_identity(item): item
        for item in downloaded_state
        if isinstance(item, dict) and item.get("raw_source_s3_key")
    }

    generic_plan = plan_source_downloads(selected_sources, downloaded_state)
    generic_to_download = {
        _source_identity(item): item
        for item in generic_plan["to_download"]
        if isinstance(item, dict)
    }
    generic_skipped = {
        _source_identity(item): item
        for item in generic_plan["skipped"]
        if isinstance(item, dict)
    }

    to_download: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for source in selected_sources:
        if not isinstance(source, dict):
            continue
        identity = _source_identity(source)
        manifest_record = manifest_lookup.get((str(source.get("source_year") or "").strip(), str(source.get("source_archive_key") or "").strip()))
        if manifest_record is None or str(source.get("source_kind") or "").strip() != SOURCE_KIND_ZIP_ARCHIVE:
            planned = generic_to_download.get(identity)
            if planned is not None:
                to_download.append(planned)
                continue
            skipped_entry = generic_skipped.get(identity)
            if skipped_entry is not None:
                skipped.append(skipped_entry)
            continue

        previous = downloaded_by_identity.get(identity)
        if manifest_record.download_status == "probe_failed":
            skipped.append(
                {
                    **source,
                    "status": "skipped",
                    "reason": "probe_failed",
                    "raw_source_s3_key": previous.get("raw_source_s3_key") if previous else None,
                    "downloaded_at": previous.get("downloaded_at") if previous else None,
                    "content_length": previous.get("content_length") if previous else None,
                    "content_type": previous.get("content_type") if previous else None,
                    "error": manifest_record.last_error,
                }
            )
            continue

        if manifest_record.download_status == "scheduled" or previous is None:
            to_download.append(_build_teos_zip_download_source(source, manifest_record))
            continue

        skipped.append(
            {
                **source,
                "status": "skipped",
                "reason": "unchanged_remote_zip",
                "raw_source_s3_key": previous.get("raw_source_s3_key"),
                "downloaded_at": previous.get("downloaded_at"),
                "content_length": previous.get("content_length"),
                "content_type": previous.get("content_type"),
            }
        )

    return {"to_download": to_download, "skipped": skipped}


def _merge_selected_sources_with_teos_manifest(
    *,
    selected_sources: list[dict[str, Any]],
    teos_zip_manifest_records: tuple[TeosZipManifestRecord, ...],
    target_years: list[str],
) -> list[dict[str, Any]]:
    merged = list(selected_sources)
    existing_identities = {_source_identity(item) for item in selected_sources if isinstance(item, dict)}
    allowed_years = {str(year).strip() for year in target_years if str(year).strip()}

    for record in teos_zip_manifest_records:
        if record.tax_year not in allowed_years:
            continue
        if record.current_sync_status == "not_listed":
            continue
        source = _teos_manifest_record_to_source(record)
        identity = _source_identity(source)
        if identity in existing_identities:
            continue
        existing_identities.add(identity)
        merged.append(source)

    return merged


def _teos_manifest_record_to_source(record: TeosZipManifestRecord) -> dict[str, Any]:
    archive_key = derive_source_archive_key(record.zip_basename)
    source_url = str(record.resolved_source_url or record.source_url or "").strip()
    filename = f"{record.zip_basename}.zip"
    page_url = FORM990_IRS_DOWNLOADS_PAGE_URL
    signature = compute_source_signature(
        source_year=record.tax_year,
        source_kind=SOURCE_KIND_ZIP_ARCHIVE,
        source_url=source_url,
        source_filename=filename,
        source_archive_key=archive_key,
        page_url=page_url,
        source_etag=record.etag,
        source_last_modified=record.last_modified,
    )
    return {
        "source_year": record.tax_year,
        "year": record.tax_year,
        "source_kind": SOURCE_KIND_ZIP_ARCHIVE,
        "source_url": source_url,
        "zip_url": source_url,
        "source_filename": filename,
        "source_archive_key": archive_key,
        "source_archive": archive_key,
        "archive_name": archive_key,
        "source_signature": signature,
        "page_url": page_url,
        "source_page_url": page_url,
        "source_etag": record.etag,
        "source_last_modified": record.last_modified,
        "discovered_at": record.discovered_at,
    }


def _build_teos_zip_download_source(source: dict[str, Any], record: TeosZipManifestRecord) -> dict[str, Any]:
    page_url = str(source.get("page_url") or source.get("source_page_url") or "").strip()
    signature = compute_source_signature(
        source_year=str(source.get("source_year") or "").strip(),
        source_kind=str(source.get("source_kind") or "").strip(),
        source_url=str(record.resolved_source_url or source.get("source_url") or "").strip(),
        source_filename=str(source.get("source_filename") or "").strip(),
        source_archive_key=str(source.get("source_archive_key") or "").strip(),
        page_url=page_url,
        source_etag=record.etag,
        source_last_modified=record.last_modified,
    )
    return {
        **source,
        "source_url": str(record.resolved_source_url or source.get("source_url") or "").strip(),
        "source_signature": signature,
        "source_etag": record.etag,
        "source_last_modified": record.last_modified,
    }


def _source_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("source_year") or "").strip(),
        str(entry.get("source_kind") or "").strip(),
        str(entry.get("source_archive_key") or "").strip(),
    )


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
        return {"manifest_key": None, "manifest_keys": [], "downloaded_count": 0, "downloads": [], "extracted_file_count": 0}

    repository = S3TeosZipManifestRepository(
        s3_client=service.s3,
        bucket=BUCKET or "",
        manifest_prefix=MANIFEST_PREFIX,
        raw_xml_prefix=TEOS_RAW_XML_PREFIX,
    )
    teos_manifest_lookup = {
        (record.tax_year, derive_source_archive_key(record.zip_basename)): record
        for record in prepared.get("teos_zip_manifest_records", ())
        if isinstance(record, TeosZipManifestRecord)
    }

    non_teos_sources: list[dict[str, Any]] = []
    teos_zip_sources: list[dict[str, Any]] = []
    for source in prepared["scheduled_sources"]:
        if _is_teos_zip_source(source, teos_manifest_lookup):
            teos_zip_sources.append(source)
        else:
            non_teos_sources.append(source)

    manifest_keys: list[str] = []
    downloads: list[dict[str, Any]] = []
    downloaded_count = 0
    extracted_file_count = 0
    batch_index = 0

    if non_teos_sources:
        batch_manifest = execute_source_download_batch(
            sources=non_teos_sources,
            bucket=BUCKET or "",
            raw_source_prefix=RAW_SOURCE_PREFIX,
            manifest_prefix=MANIFEST_PREFIX,
            s3_client=service.s3,
            run_id=prepared["run_id"],
            batch_index=batch_index,
            timeout_seconds=FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
        )
        if batch_manifest.get("manifest_key"):
            manifest_keys.append(str(batch_manifest["manifest_key"]))
        downloads.extend(batch_manifest.get("downloads", []))
        downloaded_count += int(batch_manifest.get("downloaded_count", 0) or 0)
        batch_index += 1

    for source in teos_zip_sources:
        manifest_record = teos_manifest_lookup.get((str(source.get("source_year") or "").strip(), str(source.get("source_archive_key") or "").strip()))
        if manifest_record is None:
            continue
        current_batch_index = batch_index
        batch_index += 1
        try:
            batch_manifest = execute_source_download_batch(
                sources=[source],
                bucket=BUCKET or "",
                raw_source_prefix=RAW_SOURCE_PREFIX,
                manifest_prefix=MANIFEST_PREFIX,
                s3_client=service.s3,
                run_id=prepared["run_id"],
                batch_index=current_batch_index,
                timeout_seconds=FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
            )
            if batch_manifest.get("manifest_key"):
                manifest_keys.append(str(batch_manifest["manifest_key"]))
            downloads.extend(batch_manifest.get("downloads", []))
            downloaded_count += int(batch_manifest.get("downloaded_count", 0) or 0)
            download_entry = next(
                (
                    item
                    for item in batch_manifest.get("downloads", [])
                    if isinstance(item, dict) and str(item.get("status") or "") == "downloaded"
                ),
                None,
            )
            if not isinstance(download_entry, dict) or not download_entry.get("raw_source_s3_key"):
                continue

            updated_record = replace(
                manifest_record,
                download_status="downloaded",
                download_attempted_at=str(download_entry.get("downloaded_at") or datetime.now(timezone.utc).isoformat()),
                downloaded_zip_s3_key=str(download_entry.get("raw_source_s3_key") or ""),
                processing_status=PROCESSING_STATUS_PENDING,
                last_error=None,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            repository.save_record(updated_record)

            extraction_result = extract_teos_zip_from_s3(
                s3_client=service.s3,
                bucket=BUCKET or "",
                zip_s3_key=str(download_entry.get("raw_source_s3_key") or ""),
                raw_xml_prefix=TEOS_RAW_XML_PREFIX,
                tax_year=manifest_record.tax_year,
                zip_basename=manifest_record.zip_basename,
                max_xml_file_size_bytes=FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES,
            )
            extracted_file_count += extraction_result.extracted_file_count
            repository.save_record(
                replace(
                    updated_record,
                    extraction_status="extracted",
                    extraction_attempted_at=extraction_result.extracted_at,
                    destination_raw_s3_prefix=extraction_result.destination_raw_s3_prefix,
                    extracted_file_count=extraction_result.extracted_file_count,
                    processing_status=PROCESSING_STATUS_PENDING,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            _log_structured(
                "form990.teos_zip.extracted",
                tax_year=manifest_record.tax_year,
                zip_basename=manifest_record.zip_basename,
                raw_source_s3_key=download_entry.get("raw_source_s3_key"),
                destination_raw_s3_prefix=extraction_result.destination_raw_s3_prefix,
                extracted_file_count=extraction_result.extracted_file_count,
            )
        except Exception as exc:
            attempt_at = datetime.now(timezone.utc).isoformat()
            existing = repository.load_record(manifest_record.tax_year, manifest_record.zip_basename) or manifest_record
            failure_record = replace(
                existing,
                download_attempted_at=existing.download_attempted_at or attempt_at,
                download_status="failed" if not existing.downloaded_zip_s3_key else existing.download_status,
                extraction_attempted_at=attempt_at if existing.downloaded_zip_s3_key else existing.extraction_attempted_at,
                extraction_status="failed" if existing.downloaded_zip_s3_key else existing.extraction_status,
                last_error=str(exc),
                updated_at=attempt_at,
            )
            repository.save_record(failure_record)
            _log_structured(
                "form990.teos_zip.process_failed",
                tax_year=manifest_record.tax_year,
                zip_basename=manifest_record.zip_basename,
                source_url=source.get("source_url"),
                error=str(exc),
            )

    return {
        "manifest_key": manifest_keys[0] if manifest_keys else None,
        "manifest_keys": manifest_keys,
        "downloaded_count": downloaded_count,
        "downloads": downloads,
        "extracted_file_count": extracted_file_count,
    }


def _is_teos_zip_source(
    source: dict[str, Any],
    teos_manifest_lookup: dict[tuple[str, str], TeosZipManifestRecord],
) -> bool:
    if not isinstance(source, dict) or str(source.get("source_kind") or "").strip() != SOURCE_KIND_ZIP_ARCHIVE:
        return False
    identity = (
        str(source.get("source_year") or "").strip(),
        str(source.get("source_archive_key") or "").strip(),
    )
    return identity in teos_manifest_lookup


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


def _write_checkpoint(s3_client: Any, payload: dict[str, Any]) -> None:
    checkpoint_payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    s3_client.put_object(
        Bucket=BUCKET,
        Key=checkpoint_key(MANIFEST_PREFIX),
        Body=json.dumps(checkpoint_payload, sort_keys=True).encode("utf-8"),
    )


def _validate_handler_config() -> list[str]:
    errors = validate_runtime_config(
        required_text={
            "BUCKET": BUCKET,
            "FORM990_MANIFEST_PREFIX": MANIFEST_PREFIX,
            "FORM990_METADATA_PREFIX": METADATA_PREFIX,
            "FORM990_RAW_PREFIX": RAW_PREFIX,
            "FORM990_TEOS_RAW_XML_PREFIX": TEOS_RAW_XML_PREFIX,
            "FORM990_RAW_SOURCE_PREFIX": RAW_SOURCE_PREFIX,
        },
        positive_ints={
            "FORM990_INDEX_FETCH_TIMEOUT_SECONDS": INDEX_FETCH_TIMEOUT_SECONDS,
            "FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS": FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS,
            "FORM990_ZIP_FETCH_TIMEOUT_SECONDS": FORM990_ZIP_FETCH_TIMEOUT_SECONDS,
            "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES": FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES,
            "FORM990_CHUNK_SIZE": FORM990_CHUNK_SIZE,
        },
    )
    if FORM990_SOURCE_MODE not in VALID_FORM990_SOURCE_MODES:
        errors.append("FORM990_SOURCE_MODE must be one of configured, static_manifest, or irs_page")
    if FORM990_SOURCE_MODE == "irs_page" and not FORM990_IRS_DOWNLOADS_PAGE_URL:
        errors.append("FORM990_IRS_DOWNLOADS_PAGE_URL is required when FORM990_SOURCE_MODE=irs_page")
    return errors


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


def _count_zip_sources_for_records(records: tuple[Any, ...], downloaded_source_state: list[dict[str, Any]]) -> int:
    source_years = {
        str(record.source_year or "").strip()
        for record in records
        if str(record.source_year or "").strip()
    }
    return len(
        [
            entry
            for entry in downloaded_source_state
            if isinstance(entry, dict)
            and str(entry.get("source_kind") or "").strip() == "zip_archive"
            and entry.get("raw_source_s3_key")
            and str(entry.get("source_year") or "").strip() in source_years
        ]
    )


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
        "teos_zip_extracted_file_count": response.get("teos_zip_extracted_file_count"),
        "teos_zip_manifest": response.get("teos_zip_manifest"),
        "source_batch_count": response.get("source_batch_count"),
        "processable_source_batch_count": response.get("processable_source_batch_count"),
        "processed_source_batch_count": response.get("processed_source_batch_count"),
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
        "source_download_manifest_keys": response.get("source_download_manifest_keys"),
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
