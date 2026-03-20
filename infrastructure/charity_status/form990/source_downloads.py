from __future__ import annotations

import json
import logging
import urllib.request
from urllib.error import HTTPError
from datetime import datetime, timezone
from typing import Any

from charity_status.form990.hardening import is_transient_network_error, retry_call
from charity_status.form990.storage import raw_source_key, source_download_manifest_key, source_download_state_entry_key, source_download_state_prefix

LOGGER = logging.getLogger(__name__)


def plan_source_downloads(selected_sources: list[dict[str, Any]], downloaded_state_entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    previous_by_identity = {
        _source_identity(item): item
        for item in downloaded_state_entries
        if isinstance(item, dict) and item.get("raw_source_s3_key")
    }
    to_download: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for source in selected_sources:
        if not isinstance(source, dict):
            continue
        previous = previous_by_identity.get(_source_identity(source))
        if previous and str(previous.get("source_signature") or "") == str(source.get("source_signature") or ""):
            skipped.append(
                {
                    **source,
                    "status": "skipped",
                    "reason": "already_downloaded",
                    "raw_source_s3_key": previous.get("raw_source_s3_key"),
                    "downloaded_at": previous.get("downloaded_at"),
                    "content_length": previous.get("content_length"),
                    "content_type": previous.get("content_type"),
                }
            )
            continue
        to_download.append(dict(source))

    _log_structured(
        "form990.source_download.plan",
        selected_sources=len(selected_sources),
        to_download=len(to_download),
        skipped=len(skipped),
    )
    return {"to_download": to_download, "skipped": skipped}


def execute_source_download_batch(
    *,
    sources: list[dict[str, Any]],
    bucket: str,
    raw_source_prefix: str,
    manifest_prefix: str,
    s3_client: Any,
    run_id: str,
    batch_index: int,
    timeout_seconds: int,
    max_attempts: int = 3,
    downloader: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    downloader = downloader or download_source_bytes
    now_dt = now or datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []
    manifest_key = source_download_manifest_key(manifest_prefix, run_id=run_id, batch_index=batch_index)

    for source in sources:
        if not isinstance(source, dict):
            continue
        downloaded_at = datetime.now(timezone.utc).isoformat()
        source_url = str(source.get("source_url") or "")
        state_entry_key = source_download_state_entry_key(
            manifest_prefix,
            str(source.get("source_year") or ""),
            str(source.get("source_kind") or ""),
            str(source.get("source_archive_key") or ""),
        )
        try:
            body, content_type = retry_call(
                lambda: downloader(source_url, timeout_seconds=timeout_seconds),
                max_attempts=max_attempts,
                is_retryable=is_transient_network_error,
            )
        except Exception as exc:
            if not _is_optional_generated_source_unavailable(source, exc):
                result = {
                    **source,
                    "status": "failed",
                    "reason": "source_download_failed",
                    "raw_source_s3_key": None,
                    "downloaded_at": downloaded_at,
                    "content_length": None,
                    "content_type": None,
                    "error": str(exc),
                }
                results.append(result)
                s3_client.put_object(Bucket=bucket, Key=state_entry_key, Body=json.dumps(_state_entry(result), sort_keys=True).encode("utf-8"))
                _write_manifest(
                    s3_client=s3_client,
                    bucket=bucket,
                    key=manifest_key,
                    run_id=run_id,
                    batch_index=batch_index,
                    results=results,
                    generated_at=now_dt,
                    manifest_prefix=manifest_prefix,
                )
                raise
            result = {
                **source,
                "status": "skipped_unavailable",
                "reason": "generated_source_unavailable",
                "raw_source_s3_key": None,
                "downloaded_at": downloaded_at,
                "content_length": None,
                "content_type": None,
                "error": str(exc),
            }
            results.append(result)
            s3_client.put_object(Bucket=bucket, Key=state_entry_key, Body=json.dumps(_state_entry(result), sort_keys=True).encode("utf-8"))
            _log_structured(
                "form990.source_download.skipped_unavailable",
                source_year=source.get("source_year"),
                source_kind=source.get("source_kind"),
                source_archive_key=source.get("source_archive_key"),
                source_url=source_url,
            )
            continue

        raw_key = raw_source_key(
            raw_source_prefix,
            str(source.get("source_year") or ""),
            str(source.get("source_kind") or ""),
            str(source.get("source_archive_key") or ""),
            str(source.get("source_signature") or ""),
            str(source.get("source_filename") or ""),
        )
        metadata = _metadata_for_source(source, downloaded_at=downloaded_at)
        put_kwargs = {
            "Bucket": bucket,
            "Key": raw_key,
            "Body": body,
            "Metadata": metadata,
        }
        if content_type:
            put_kwargs["ContentType"] = content_type
        s3_client.put_object(**put_kwargs)
        result = {
            **source,
            "status": "downloaded",
            "raw_source_s3_key": raw_key,
            "downloaded_at": downloaded_at,
            "content_length": len(body),
            "content_type": content_type,
        }
        results.append(result)
        s3_client.put_object(Bucket=bucket, Key=state_entry_key, Body=json.dumps(_state_entry(result), sort_keys=True).encode("utf-8"))
        _log_structured(
            "form990.source_download.completed",
            source_year=source.get("source_year"),
            source_kind=source.get("source_kind"),
            source_archive_key=source.get("source_archive_key"),
            content_length=len(body),
            raw_source_s3_key=raw_key,
        )

    _write_manifest(
        s3_client=s3_client,
        bucket=bucket,
        key=manifest_key,
        run_id=run_id,
        batch_index=batch_index,
        results=results,
        generated_at=now_dt,
        manifest_prefix=manifest_prefix,
    )
    _log_structured(
        "form990.source_download.batch_complete",
        run_id=run_id,
        batch_index=batch_index,
        downloaded_count=sum(1 for item in results if str(item.get("status") or "") == "downloaded"),
        skipped_unavailable_count=sum(1 for item in results if str(item.get("status") or "") == "skipped_unavailable"),
        failed_count=sum(1 for item in results if str(item.get("status") or "") == "failed"),
        manifest_key=manifest_key,
    )
    return {"manifest_key": manifest_key, **_manifest_payload(results, run_id=run_id, batch_index=batch_index, generated_at=now_dt, manifest_prefix=manifest_prefix)}


def load_downloaded_source_state(s3_client: Any, bucket: str, manifest_prefix: str) -> list[dict[str, Any]]:
    prefix = source_download_state_prefix(manifest_prefix)
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    except Exception:
        return []

    entries: list[dict[str, Any]] = []
    for item in response.get("Contents", []):
        key = str(item.get("Key") or "").strip()
        if not key.endswith(".json"):
            continue
        try:
            body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
            payload = json.loads(body)
        except Exception:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return sorted(entries, key=_entry_sort_key)


def download_source_bytes(source_url: str, timeout_seconds: int) -> tuple[bytes, str | None]:
    request = urllib.request.Request(source_url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"source download failed with status {response.status}")
        content_type = response.headers.get("Content-Type")
        return response.read(), content_type


def _log_structured(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    try:
        LOGGER.info(json.dumps(payload, sort_keys=True))
    except Exception:
        LOGGER.info("%s %s", event, fields)


def _metadata_for_source(source: dict[str, Any], *, downloaded_at: str) -> dict[str, str]:
    return {
        "source_url": str(source.get("source_url") or "")[:1024],
        "source_kind": str(source.get("source_kind") or "")[:128],
        "source_year": str(source.get("source_year") or "")[:32],
        "source_signature": str(source.get("source_signature") or "")[:256],
        "downloaded_at": downloaded_at[:64],
    }


def _state_entry(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_year": result.get("source_year"),
        "source_kind": result.get("source_kind"),
        "source_url": result.get("source_url"),
        "source_filename": result.get("source_filename"),
        "source_archive_key": result.get("source_archive_key"),
        "source_signature": result.get("source_signature"),
        "page_url": result.get("page_url"),
        "source_etag": result.get("source_etag"),
        "source_last_modified": result.get("source_last_modified"),
        "status": result.get("status"),
        "reason": result.get("reason"),
        "raw_source_s3_key": result.get("raw_source_s3_key"),
        "downloaded_at": result.get("downloaded_at"),
        "content_length": result.get("content_length"),
        "content_type": result.get("content_type"),
    }


def _write_manifest(
    *,
    s3_client: Any,
    bucket: str,
    key: str,
    run_id: str,
    batch_index: int,
    results: list[dict[str, Any]],
    generated_at: datetime,
    manifest_prefix: str,
) -> None:
    payload = _manifest_payload(
        results,
        run_id=run_id,
        batch_index=batch_index,
        generated_at=generated_at,
        manifest_prefix=manifest_prefix,
    )
    s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload, sort_keys=True).encode("utf-8"))


def _manifest_payload(
    results: list[dict[str, Any]],
    *,
    run_id: str,
    batch_index: int,
    generated_at: datetime,
    manifest_prefix: str,
) -> dict[str, Any]:
    return {
        "generated_at": generated_at.isoformat(),
        "run_id": run_id,
        "batch_index": batch_index,
        "downloaded_count": sum(1 for item in results if str(item.get("status") or "") == "downloaded"),
        "skipped_unavailable_count": sum(1 for item in results if str(item.get("status") or "") == "skipped_unavailable"),
        "failed_count": sum(1 for item in results if str(item.get("status") or "") == "failed"),
        "downloads": results,
        "source_download_state_prefix": source_download_state_prefix(manifest_prefix),
    }


def _is_optional_generated_source_unavailable(source: dict[str, Any], exc: Exception) -> bool:
    if not _is_generated_source(source):
        return False
    status_code = _http_status_code(exc)
    return status_code == 404


def _is_generated_source(source: dict[str, Any]) -> bool:
    page_url = str(source.get("page_url") or source.get("source_page_url") or "").strip().lower()
    return page_url.startswith("generated://form990-next-year/")


def _http_status_code(exc: Exception) -> int | None:
    if isinstance(exc, HTTPError):
        return int(exc.code)
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status
    response = getattr(exc, "response", None)
    if response is None:
        return None
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    return None


def _source_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("source_year") or "").strip(),
        str(entry.get("source_kind") or "").strip(),
        str(entry.get("source_archive_key") or "").strip(),
    )


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return _source_identity(entry)
