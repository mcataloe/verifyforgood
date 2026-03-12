from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from charity_status.api import error_response, json_response
from charity_status.form990 import Form990IngestService
from charity_status.form990.discovery import discover_archives, fetch_index_records
from charity_status.form990.manifest import diff_manifest_entries, to_manifest_entries
from charity_status.form990.storage import checkpoint_key, discovery_manifest_key, filing_manifest_key, state_manifest_key

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

    catalog = _resolve_source_catalog(payload)
    now_year = int(payload.get("now_year") or datetime.now(timezone.utc).year)
    discovered = discover_archives(catalog, mode=mode, now_year=now_year, reconciliation_all_years=reconciliation_all_years)

    all_records = []
    archive_summaries: list[dict[str, Any]] = []
    for archive in discovered:
        records = _fetch_with_retries(archive.index_url, archive.source_year, archive.source_archive)
        all_records.extend(records)
        archive_manifest = {
            "run_id": run_id,
            "source_year": archive.source_year,
            "source_archive": archive.source_archive,
            "index_url": archive.index_url,
            "record_count": len(records),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        archive_summaries.append(archive_manifest)
        service.s3.put_object(
            Bucket=BUCKET,
            Key=discovery_manifest_key(MANIFEST_PREFIX, run_id=run_id, source_year=archive.source_year, source_archive=archive.source_archive),
            Body=json.dumps(archive_manifest, sort_keys=True).encode("utf-8"),
        )

    previous_entries = _load_previous_manifest_entries(service.s3)
    new_records, changed_records, unchanged_count = diff_manifest_entries(all_records, previous_entries)
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
    return {
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
