from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol
from urllib.error import HTTPError

from verification.backend.ingest.federal.form990.hardening import is_transient_network_error, retry_call

class TeosZipProbeState(Protocol):
    etag: str | None
    last_modified: str | None
    content_length: int | None


@dataclass(frozen=True)
class TeosZipProbeResult:
    source_url: str
    resolved_source_url: str | None
    etag: str | None
    last_modified: str | None
    content_length: int | None
    checked_at: str
    method_used: str


@dataclass(frozen=True)
class TeosZipProbeFailure:
    source_url: str
    checked_at: str
    error: str


@dataclass(frozen=True)
class TeosZipDownloadDecision:
    should_download: bool
    reason: str


def probe_teos_zip_metadata(
    source_url: str,
    *,
    timeout_seconds: int = 60,
    now: datetime | None = None,
    max_attempts: int = 3,
    opener: Callable[..., Any] | None = None,
) -> TeosZipProbeResult:
    checked_at = (now or datetime.now(timezone.utc)).isoformat()
    url_opener = opener or urllib.request.urlopen

    def _head() -> TeosZipProbeResult:
        return _request_probe_result(
            source_url,
            timeout_seconds=timeout_seconds,
            checked_at=checked_at,
            method="HEAD",
            opener=url_opener,
        )

    try:
        return retry_call(
            _head,
            max_attempts=max_attempts,
            is_retryable=is_transient_network_error,
        )
    except Exception as exc:
        if not _should_fallback_to_get(exc):
            raise

    def _get() -> TeosZipProbeResult:
        return _request_probe_result(
            source_url,
            timeout_seconds=timeout_seconds,
            checked_at=checked_at,
            method="GET",
            opener=url_opener,
        )

    return retry_call(
        _get,
        max_attempts=max_attempts,
        is_retryable=is_transient_network_error,
    )


def should_download_teos_zip(
    *,
    previous: TeosZipProbeState | None,
    current_probe: TeosZipProbeResult,
) -> TeosZipDownloadDecision:
    if previous is None:
        return TeosZipDownloadDecision(should_download=True, reason="new_zip")
    if current_probe.etag and current_probe.etag != (previous.etag or ""):
        return TeosZipDownloadDecision(should_download=True, reason="etag_changed")
    if current_probe.last_modified and current_probe.last_modified != (previous.last_modified or ""):
        return TeosZipDownloadDecision(should_download=True, reason="last_modified_changed")
    if current_probe.content_length is not None and current_probe.content_length != previous.content_length:
        return TeosZipDownloadDecision(should_download=True, reason="content_length_changed")
    return TeosZipDownloadDecision(should_download=False, reason="unchanged_remote_zip")


def _request_probe_result(
    source_url: str,
    *,
    timeout_seconds: int,
    checked_at: str,
    method: str,
    opener: Callable[..., Any],
) -> TeosZipProbeResult:
    request = urllib.request.Request(source_url, method=method)
    if method == "GET":
        request.add_header("Range", "bytes=0-0")
    with opener(request, timeout=timeout_seconds) as response:
        status_code = int(getattr(response, "status", 200))
        if status_code >= 400:
            raise RuntimeError(f"TEOS ZIP probe failed with status {status_code}")
        if method == "GET":
            response.read(1)
        headers = response.headers
        return TeosZipProbeResult(
            source_url=source_url,
            resolved_source_url=_as_optional_text(getattr(response, "geturl", lambda: source_url)()),
            etag=_as_optional_text(headers.get("ETag")),
            last_modified=_as_optional_text(headers.get("Last-Modified")),
            content_length=_as_optional_int(headers.get("Content-Length")),
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


__all__ = [
    "TeosZipDownloadDecision",
    "TeosZipProbeFailure",
    "TeosZipProbeResult",
    "probe_teos_zip_metadata",
    "should_download_teos_zip",
]

