from __future__ import annotations

import json
import os

from charity_status.api import error_response, json_response
from charity_status.form990 import Form990IngestService
from charity_status.form990.index import fetch_index_payload

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


def handler(event, context):
    if not BUCKET:
        return error_response(500, "BUCKET environment variable is required")

    payload = event.get("records") if isinstance(event, dict) else None
    download_raw = bool(event.get("download_raw")) if isinstance(event, dict) else DEFAULT_DOWNLOAD_RAW
    explicit_download_raw = isinstance(event, dict) and "download_raw" in event

    if payload is None and isinstance(event, dict) and event.get("body"):
        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return error_response(400, "Request body must be valid JSON")
        payload = body.get("records") if isinstance(body, dict) else None
        if isinstance(body, dict) and "download_raw" in body:
            download_raw = bool(body.get("download_raw"))
            explicit_download_raw = True

    if payload is None:
        payload = _load_index_records(event=event)
        if payload and not explicit_download_raw:
            download_raw = DEFAULT_DOWNLOAD_RAW

    if not isinstance(payload, list):
        return error_response(400, "records must be an array")

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
    result = service.ingest_index_payload(payload=payload, download_raw=download_raw)
    return json_response(200, result)


def _load_index_records(event: dict | None) -> list[dict]:
    candidate_urls = _extract_index_urls(event)
    if not candidate_urls:
        return []

    payload: list[dict] = []
    for url in candidate_urls:
        payload.extend(fetch_index_payload(url, timeout_seconds=INDEX_FETCH_TIMEOUT_SECONDS))
    return _apply_index_filters(payload, event or {})


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
