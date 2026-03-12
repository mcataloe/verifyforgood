from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from charity_status.api import error_response, json_response
from charity_status.form990 import Form990IngestService
from charity_status.form990.discovery import discover_archives, fetch_index_records
from charity_status.form990.irs_page_discovery import (
    IrsYearSource,
    discover_irs_form990_sources,
    discovery_state_changed,
    discovery_state_payload,
    sources_to_catalog,
)
from charity_status.form990.manifest import diff_manifest_entries, to_manifest_entries
from charity_status.form990.policy import IngestPolicyConfig, select_target_years
from charity_status.form990.zip_processing import fetch_zip_records
from charity_status.ops import S3RunStore
from charity_status.form990.storage import checkpoint_key, discovery_manifest_key, discovery_state_key, filing_manifest_key, state_manifest_key

BUCKET = os.environ.get("BUCKET")
RAW_PREFIX = os.environ.get("FORM990_RAW_PREFIX", "form990/raw/")
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
FORM990_ZIP_FETCH_TIMEOUT_SECONDS = int(os.environ.get("FORM990_ZIP_FETCH_TIMEOUT_SECONDS", "120"))
FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES = int(os.environ.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES", str(20 * 1024 * 1024)))
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
        return json_response(200, result)

    # Backward-compatible path: when callers provide index_url(s) without orchestration mode,
    # ingest directly and return legacy ingest payload shape.
    if "mode" not in payload and "source_catalog" not in payload:
        legacy_records = _load_legacy_index_records(payload)
        if legacy_records:
            result = service.ingest_index_payload(payload=legacy_records, download_raw=bool(payload.get("download_raw", DEFAULT_DOWNLOAD_RAW)))
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
    mode = str(payload.get("mode") or FORM990_RUN_MODE or "incremental").strip().lower()
    if mode not in {"bootstrap", "incremental"}:
        raise ValueError("mode must be bootstrap or incremental")

    batch_size = int(payload.get("batch_size") or FORM990_BATCH_SIZE)
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    run_id = str(payload.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    reconciliation_all_years = bool(payload.get("reconciliation_all_years", False))
    resume = bool(payload.get("resume", False))

    source_mode = _resolve_source_mode(payload)
    discovered_sources = _discover_sources(payload, source_mode=source_mode)
    catalog = sources_to_catalog(discovered_sources) if source_mode == "irs_page" else _resolve_source_catalog(payload)
    now_dt = _resolve_now(payload)
    now_year = now_dt.year
    discovered = discover_archives(catalog, mode="bootstrap", now_year=now_year, reconciliation_all_years=True)
    discovered_years = sorted({archive.source_year for archive in discovered})
    _log_structured("form990.discovery.summary", source_mode=source_mode, discovered_years=discovered_years, discovered_archives=len(discovered))
    policy = _build_policy_config(payload, mode=mode)
    selected_years, policy_metadata = select_target_years(discovered_years, policy, now=now_dt)
    _log_structured("form990.discovery.selected_years", selected_years=selected_years, mode=mode, policy_effective_mode=policy_metadata.get("effective_mode"))
    discovered = [archive for archive in discovered if archive.source_year in set(selected_years)] if selected_years else []
    if reconciliation_all_years:
        policy_metadata["effective_mode"] = "reconciliation"
        policy_metadata["reconciliation_due"] = True

    all_records = []
    archive_summaries: list[dict[str, Any]] = []
    if source_mode == "irs_page":
        _persist_discovery_state(service.s3, discovered_sources)

    for archive in discovered:
        _log_structured("form990.archive.start", source_year=archive.source_year, source_archive=archive.source_archive, source_mode=source_mode)
        records = _fetch_archive_records_with_retries(catalog, archive, source_mode=source_mode)
        all_records.extend(records)
        archive_manifest = {
            "run_id": run_id,
            "source_year": archive.source_year,
            "source_archive": archive.source_archive,
            "index_url": archive.index_url,
            "source_mode": source_mode,
            "record_count": len(records),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        archive_summaries.append(archive_manifest)
        _log_structured("form990.archive.complete", source_year=archive.source_year, source_archive=archive.source_archive, record_count=len(records))
        service.s3.put_object(
            Bucket=BUCKET,
            Key=discovery_manifest_key(MANIFEST_PREFIX, run_id=run_id, source_year=archive.source_year, source_archive=archive.source_archive),
            Body=json.dumps(archive_manifest, sort_keys=True).encode("utf-8"),
        )

    previous_entries = _load_previous_manifest_entries(service.s3)
    new_records, changed_records, unchanged_count = diff_manifest_entries(all_records, previous_entries)
    _log_structured(
        "form990.reconciliation.summary",
        total_index_records=len(all_records),
        new_records=len(new_records),
        changed_records=len(changed_records),
        unchanged_records=unchanged_count,
    )
    selected = all_records if mode == "bootstrap" and bool(payload.get("bootstrap_process_all", True)) else (new_records + changed_records)

    selected = _apply_index_filters([_record_to_dict(item) for item in selected], payload)
    start_offset = _resolve_start_offset(service.s3, payload, resume=resume)
    total_selected = len(selected)
    selected = selected[start_offset:]

    processed = 0
    parsed = 0
    failed = 0
    batches = 0
    batch_results: list[dict[str, Any]] = []
    for idx in range(0, len(selected), batch_size):
        chunk = selected[idx : idx + batch_size]
        if not chunk:
            continue
        batches += 1
        ingest_result = service.ingest_index_payload(payload=chunk, download_raw=True)
        processed += int(ingest_result.get("records_processed") or 0)
        parsed += int(ingest_result.get("parsed_count") or 0)
        failed += int(ingest_result.get("failed_count") or 0)
        manifest_entry = {
            "run_id": run_id,
            "batch_index": batches - 1,
            "chunk_size": len(chunk),
            "processed": ingest_result.get("records_processed"),
            "parsed": ingest_result.get("parsed_count"),
            "failed": ingest_result.get("failed_count"),
            "filing_records_s3_key": ingest_result.get("filing_records_s3_key"),
            "metrics_s3_key": ingest_result.get("metrics_s3_key"),
        }
        service.s3.put_object(
            Bucket=BUCKET,
            Key=filing_manifest_key(MANIFEST_PREFIX, run_id=run_id, batch_index=batches - 1),
            Body=json.dumps(manifest_entry, sort_keys=True).encode("utf-8"),
        )
        _save_checkpoint(
            service.s3,
            run_id=run_id,
            mode=mode,
            offset=start_offset + idx + len(chunk),
            total=total_selected,
            completed=False,
        )
        batch_results.append(manifest_entry)
        _log_structured("form990.batch.complete", batch_index=batches - 1, chunk_size=len(chunk), processed=manifest_entry.get("processed"), failed=manifest_entry.get("failed"))

    _save_checkpoint(
        service.s3,
        run_id=run_id,
        mode=mode,
        offset=total_selected,
        total=total_selected,
        completed=True,
    )
    service.s3.put_object(
        Bucket=BUCKET,
        Key=state_manifest_key(MANIFEST_PREFIX),
        Body=json.dumps({"run_id": run_id, "entries": to_manifest_entries(all_records)}, sort_keys=True).encode("utf-8"),
    )
    status = "success" if failed == 0 else ("partial_success" if processed > 0 else "failed")
    response = {
        "status": "success",
        "mode": mode,
        "run_id": run_id,
        "archives_discovered": len(discovered),
        "total_index_records": len(all_records),
        "new_records": len(new_records),
        "changed_records": len(changed_records),
        "unchanged_records": unchanged_count,
        "selected_records": total_selected,
        "processed_records": processed,
        "parsed_count": parsed,
        "failed_count": failed,
        "batch_count": batches,
        "affected_eins": sorted({str(item.get("ein") or "").strip() for item in selected if str(item.get("ein") or "").strip()}),
        "affected_filing_ids": _collect_filing_ids_by_ein(selected),
        "checkpoint_key": checkpoint_key(MANIFEST_PREFIX),
        "batches": batch_results,
        "archives": archive_summaries,
        "policy": {
            "mode_requested": mode,
            "effective_mode": policy_metadata.get("effective_mode"),
            "target_years": selected_years,
            "incremental_year_window": policy.incremental_year_window,
            "reconciliation_enabled": policy.reconciliation_enabled,
            "reconciliation_cadence_days": policy.reconciliation_cadence_days,
            "reconciliation_due": policy_metadata.get("reconciliation_due"),
            "fallback_used": policy_metadata.get("fallback_used"),
            "resume": resume,
            "batch_size": batch_size,
            "retry_count": FORM990_RETRY_COUNT,
        },
        "source_mode": source_mode,
    }
    response["status"] = status
    _log_structured("form990.run.complete", run_id=run_id, status=status, source_mode=source_mode, processed_records=processed, failed_count=failed)
    _persist_ingest_ops_run(service, response, selected)
    return response


def _run_discovery_orchestrated(service: Form990IngestService, payload: dict[str, Any]) -> dict[str, Any]:
    if not FORM990_WORK_QUEUE_URL:
        raise ValueError("FORM990_WORK_QUEUE_URL is required for orchestrated execution mode")

    prepared = _prepare_discovery_selection(service, payload)
    run_id = prepared["run_id"]
    selected = prepared["selected"]
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
            "records": chunk,
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
        "status": "queued",
        "source_mode": prepared["source_mode"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "archives_discovered": prepared["archives_discovered"],
        "filings_discovered": prepared["total_index_records"],
        "filings_new": prepared["new_records"],
        "filings_changed": prepared["changed_records"],
        "filings_skipped": prepared["unchanged_records"],
        "selected_records": len(selected),
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "chunk_status_counts": {"queued": len(chunks), "running": 0, "succeeded": 0, "failed": 0, "dlq": 0},
        "policy": prepared["policy"],
    }
    run_store.write_ingest_run(run_id, run_summary)
    run_store.write_ingest_filings(run_id, selected)

    ops_run_key = f"{prefix}/form990-runs/{run_id}/run.json"
    service.s3.put_object(Bucket=bucket, Key=ops_run_key, Body=json.dumps(run_summary, sort_keys=True).encode("utf-8"))
    service.s3.put_object(
        Bucket=bucket,
        Key=f"{prefix}/form990-runs/{run_id}/summary.json",
        Body=json.dumps({"ingest_run_id": run_id, "chunk_count": len(chunks), "status": "queued"}, sort_keys=True).encode("utf-8"),
    )

    return {
        "status": "queued",
        "mode": prepared["mode"],
        "execution_mode": "orchestrated",
        "run_id": run_id,
        "source_mode": prepared["source_mode"],
        "archives_discovered": prepared["archives_discovered"],
        "total_index_records": prepared["total_index_records"],
        "new_records": prepared["new_records"],
        "changed_records": prepared["changed_records"],
        "unchanged_records": prepared["unchanged_records"],
        "selected_records": len(selected),
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "run_s3_key": ops_run_key,
        "chunks": chunks[:10],
    }


def _fetch_with_retries(index_url: str, source_year: str, source_archive: str) -> list[Any]:
    last_error: Exception | None = None
    for _attempt in range(FORM990_RETRY_COUNT + 1):
        try:
            return fetch_index_records(index_url=index_url, source_year=source_year, source_archive=source_archive, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS)
        except Exception as exc:  # pragma: no cover - exercised by retries in runtime
            last_error = exc
    if last_error:
        raise last_error
    return []


def _fetch_archive_records_with_retries(catalog: list[dict[str, Any]], archive: Any, source_mode: str) -> list[Any]:
    source = _lookup_catalog_item(catalog, archive.source_year, archive.source_archive)
    if source_mode == "irs_page" and str(source.get("zip_url") or "").strip():
        return _fetch_zip_records_with_retries(
            zip_url=str(source.get("zip_url") or "").strip(),
            source_year=archive.source_year,
            source_archive=archive.source_archive,
            index_url=archive.index_url,
        )
    return _fetch_with_retries(archive.index_url, archive.source_year, archive.source_archive)


def _fetch_zip_records_with_retries(zip_url: str, source_year: str, source_archive: str, index_url: str | None = None) -> list[Any]:
    last_error: Exception | None = None
    for _attempt in range(FORM990_RETRY_COUNT + 1):
        try:
            return _zip_records_to_index_records(
                zip_url=zip_url,
                source_year=source_year,
                source_archive=source_archive,
                index_url=index_url,
            )
        except Exception as exc:  # pragma: no cover - exercised by retries in runtime
            last_error = exc
    if last_error:
        raise last_error
    return []


def _zip_records_to_index_records(zip_url: str, source_year: str, source_archive: str, index_url: str | None = None) -> list[Any]:
    zipped = fetch_zip_records(
        zip_url=zip_url,
        source_year=source_year,
        source_archive=source_archive,
        timeout_seconds=FORM990_ZIP_FETCH_TIMEOUT_SECONDS,
        max_xml_file_size_bytes=FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES,
    )
    records = []
    for record, _xml in zipped:
        records.append(record)
    return records


def _lookup_catalog_item(catalog: list[dict[str, Any]], source_year: str, source_archive: str) -> dict[str, Any]:
    for item in catalog:
        year = str(item.get("year") or item.get("source_year") or "").strip()
        archive = str(item.get("archive_name") or item.get("source_archive") or "").strip()
        if year == str(source_year).strip() and archive == str(source_archive).strip():
            return item
    return {}


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


def _discover_sources(payload: dict[str, Any], source_mode: str) -> list[IrsYearSource]:
    if source_mode != "irs_page":
        return []
    page_url = str(payload.get("irs_downloads_page_url") or FORM990_IRS_DOWNLOADS_PAGE_URL or "").strip()
    if not page_url:
        raise ValueError("irs_page source_mode requires irs_downloads_page_url or FORM990_IRS_DOWNLOADS_PAGE_URL")
    return discover_irs_form990_sources(page_url=page_url, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS)


def _persist_discovery_state(s3_client: Any, discovered_sources: list[IrsYearSource]) -> None:
    if not discovered_sources:
        return
    previous = _load_previous_discovery_state(s3_client)
    if not discovery_state_changed(discovered_sources, previous):
        _log_structured("form990.discovery.state_unchanged", discovery_sources=len(discovered_sources))
        return
    payload = discovery_state_payload(discovered_sources)
    s3_client.put_object(Bucket=BUCKET, Key=discovery_state_key(MANIFEST_PREFIX), Body=json.dumps(payload, sort_keys=True).encode("utf-8"))
    _log_structured("form990.discovery.state_updated", discovery_sources=len(discovered_sources), key=discovery_state_key(MANIFEST_PREFIX))


def _prepare_discovery_selection(service: Form990IngestService, payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or FORM990_RUN_MODE or "incremental").strip().lower()
    if mode not in {"bootstrap", "incremental"}:
        raise ValueError("mode must be bootstrap or incremental")

    run_id = str(payload.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    source_mode = _resolve_source_mode(payload)
    discovered_sources = _discover_sources(payload, source_mode=source_mode)
    catalog = sources_to_catalog(discovered_sources) if source_mode == "irs_page" else _resolve_source_catalog(payload)
    now_dt = _resolve_now(payload)
    discovered = discover_archives(catalog, mode="bootstrap", now_year=now_dt.year, reconciliation_all_years=True)
    discovered_years = sorted({archive.source_year for archive in discovered})
    policy = _build_policy_config(payload, mode=mode)
    selected_years, policy_metadata = select_target_years(discovered_years, policy, now=now_dt)
    discovered = [archive for archive in discovered if archive.source_year in set(selected_years)] if selected_years else []
    if bool(payload.get("reconciliation_all_years", False)):
        policy_metadata["effective_mode"] = "reconciliation"
        policy_metadata["reconciliation_due"] = True

    if source_mode == "irs_page":
        _persist_discovery_state(service.s3, discovered_sources)

    all_records = []
    for archive in discovered:
        records = _fetch_archive_records_with_retries(catalog, archive, source_mode=source_mode)
        all_records.extend(records)
    previous_entries = _load_previous_manifest_entries(service.s3)
    new_records, changed_records, unchanged_count = diff_manifest_entries(all_records, previous_entries)
    selected = all_records if mode == "bootstrap" and bool(payload.get("bootstrap_process_all", True)) else (new_records + changed_records)
    selected_dicts = _apply_index_filters([_record_to_dict(item) for item in selected], payload)
    return {
        "run_id": run_id,
        "mode": mode,
        "source_mode": source_mode,
        "archives_discovered": len(discovered),
        "total_index_records": len(all_records),
        "new_records": len(new_records),
        "changed_records": len(changed_records),
        "unchanged_records": unchanged_count,
        "selected": selected_dicts,
        "policy": {
            "mode_requested": mode,
            "effective_mode": policy_metadata.get("effective_mode"),
            "target_years": selected_years,
            "incremental_year_window": policy.incremental_year_window,
            "reconciliation_enabled": policy.reconciliation_enabled,
            "reconciliation_cadence_days": policy.reconciliation_cadence_days,
            "reconciliation_due": policy_metadata.get("reconciliation_due"),
            "fallback_used": policy_metadata.get("fallback_used"),
            "resume": bool(payload.get("resume", False)),
            "batch_size": int(payload.get("batch_size") or FORM990_BATCH_SIZE),
            "retry_count": FORM990_RETRY_COUNT,
        },
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


def _collect_filing_ids_by_ein(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = {}
    for row in records:
        if not isinstance(row, dict):
            continue
        ein = str(row.get("ein") or "").strip()
        filing_id = str(row.get("irs_object_id") or "").strip()
        if not ein or not filing_id:
            continue
        mapping.setdefault(ein, set()).add(filing_id)
    return {ein: sorted(values) for ein, values in mapping.items()}


def _persist_ingest_ops_run(service: Form990IngestService, response: dict[str, Any], selected_records: list[dict[str, Any]]) -> None:
    bucket = OPS_METADATA_BUCKET or BUCKET or ""
    if not bucket:
        return
    run_id = str(response.get("run_id") or "")
    if not run_id:
        return
    store = S3RunStore(bucket=bucket, prefix=OPS_METADATA_PREFIX, s3_client=service.s3)
    years_checked = sorted({str(item.get("source_year") or "") for item in response.get("archives", []) if str(item.get("source_year") or "")})
    summary = {
        "ingest_run_id": run_id,
        "mode": response.get("mode"),
        "started_at": None,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": response.get("status"),
        "years_checked": years_checked,
        "archives_discovered": response.get("archives_discovered"),
        "index_files_processed": response.get("archives_discovered"),
        "filings_discovered": response.get("total_index_records"),
        "filings_new": response.get("new_records"),
        "filings_changed": response.get("changed_records"),
        "filings_skipped": response.get("unchanged_records"),
        "filings_failed": response.get("failed_count"),
        "affected_ein_count": response.get("affected_ein_count"),
        "checkpoint_key": response.get("checkpoint_key"),
        "resume_supported": True,
        "safe_error_summary": {"count": int(response.get("failed_count") or 0), "samples": []},
        "policy": response.get("policy"),
    }
    store.write_ingest_run(run_id, summary)
    filing_items = [
        {
            "ein": item.get("ein"),
            "irs_object_id": item.get("irs_object_id"),
            "tax_year": item.get("tax_year"),
            "return_type": item.get("return_type"),
            "source_year": item.get("source_year"),
            "source_archive": item.get("source_archive"),
            "status": "selected",
            "parse_status": None,
            "error_code": None,
        }
        for item in selected_records
    ]
    store.write_ingest_filings(run_id, filing_items)


def _load_previous_manifest_entries(s3_client: Any) -> list[dict[str, Any]]:
    try:
        response = s3_client.get_object(Bucket=BUCKET, Key=state_manifest_key(MANIFEST_PREFIX))
        body = response["Body"].read().decode("utf-8")
        payload = json.loads(body)
        entries = payload.get("entries")
        if isinstance(entries, list):
            return [item for item in entries if isinstance(item, dict)]
    except Exception:
        return []
    return []


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


def _save_checkpoint(s3_client: Any, run_id: str, mode: str, offset: int, total: int, completed: bool) -> None:
    payload = {
        "run_id": run_id,
        "mode": mode,
        "offset": int(offset),
        "total_selected": int(total),
        "completed": bool(completed),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    s3_client.put_object(Bucket=BUCKET, Key=checkpoint_key(MANIFEST_PREFIX), Body=json.dumps(payload, sort_keys=True).encode("utf-8"))


def _resolve_start_offset(s3_client: Any, payload: dict[str, Any], resume: bool) -> int:
    if payload.get("start_offset") is not None:
        try:
            return max(0, int(payload.get("start_offset")))
        except (TypeError, ValueError):
            return 0
    if not resume:
        return 0
    try:
        response = s3_client.get_object(Bucket=BUCKET, Key=checkpoint_key(MANIFEST_PREFIX))
        body = response["Body"].read().decode("utf-8")
        checkpoint = json.loads(body)
        return max(0, int(checkpoint.get("offset") or 0))
    except Exception:
        return 0


def _log_structured(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    try:
        LOGGER.info(json.dumps(payload, sort_keys=True))
    except Exception:
        LOGGER.info("%s %s", event, fields)
