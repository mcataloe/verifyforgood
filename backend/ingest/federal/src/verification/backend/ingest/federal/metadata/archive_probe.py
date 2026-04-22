"""Archive HEAD metadata probing and normalization."""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError

from verification.backend.ingest.federal.form990.hardening import is_transient_network_error, retry_call


@dataclass(frozen=True)
class ArchiveProbeResult:
    source_url: str
    resolved_source_url: str | None
    etag: str | None
    normalized_etag: str | None
    last_modified: str | None
    content_length: int | None
    response_status: int
    checked_at: str
    method_used: str


def probe_archive_metadata(
    source_url: str,
    *,
    timeout_seconds: int = 60,
    now: datetime | None = None,
    max_attempts: int = 3,
    opener: Callable[..., Any] | None = None,
) -> ArchiveProbeResult:
    checked_at = (now or datetime.now(timezone.utc)).isoformat()
    url_opener = opener or urllib.request.urlopen

    def _head() -> ArchiveProbeResult:
        return _request_probe_result(
            source_url,
            timeout_seconds=timeout_seconds,
            checked_at=checked_at,
            method="HEAD",
            opener=url_opener,
        )

    try:
        return retry_call(_head, max_attempts=max_attempts, is_retryable=is_transient_network_error)
    except Exception as exc:
        if not _should_fallback_to_get(exc):
            raise

    def _get() -> ArchiveProbeResult:
        return _request_probe_result(
            source_url,
            timeout_seconds=timeout_seconds,
            checked_at=checked_at,
            method="GET",
            opener=url_opener,
        )

    return retry_call(_get, max_attempts=max_attempts, is_retryable=is_transient_network_error)


def normalize_etag(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("W/"):
        text = text[2:].strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    text = text.strip()
    return text or None


def _request_probe_result(
    source_url: str,
    *,
    timeout_seconds: int,
    checked_at: str,
    method: str,
    opener: Callable[..., Any],
) -> ArchiveProbeResult:
    request = urllib.request.Request(source_url, method=method)
    if method == "GET":
        request.add_header("Range", "bytes=0-0")
    with opener(request, timeout=timeout_seconds) as response:
        status_code = int(getattr(response, "status", 200))
        if status_code >= 400:
            raise RuntimeError(f"archive probe failed with status {status_code}")
        if method == "GET":
            response.read(1)
        headers = response.headers
        etag = _as_optional_text(headers.get("ETag"))
        return ArchiveProbeResult(
            source_url=source_url,
            resolved_source_url=_as_optional_text(getattr(response, "geturl", lambda: source_url)()),
            etag=etag,
            normalized_etag=normalize_etag(etag),
            last_modified=_as_optional_text(headers.get("Last-Modified")),
            content_length=_as_optional_int(headers.get("Content-Length")),
            response_status=status_code,
            checked_at=checked_at,
            method_used=method,
        )


def _should_fallback_to_get(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return int(exc.code) in {403, 405, 501}
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status in {403, 405, 501}
    return False


def _as_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = ["ArchiveProbeResult", "normalize_etag", "probe_archive_metadata"]

