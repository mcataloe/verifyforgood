from __future__ import annotations

import socket
import ssl
import urllib.error
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def retry_call(fn: Callable[[], T], *, max_attempts: int, is_retryable: Callable[[Exception], bool]) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - exercised through callers
            last_error = exc
            if attempt >= max_attempts or not is_retryable(exc):
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("retry_call exhausted without exception")


def is_transient_network_error(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, socket.timeout):
        return True
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError)):
        return True
    if isinstance(exc, ssl.SSLError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError):
            return True
        if isinstance(reason, OSError):
            return True
    if isinstance(exc, urllib.error.HTTPError):
        return int(exc.code) >= 500 or int(exc.code) in {408, 429}
    return isinstance(exc, OSError)


def validate_runtime_config(
    *,
    required_text: dict[str, str | None],
    positive_ints: dict[str, int],
    optional_text: dict[str, str | None] | None = None,
) -> list[str]:
    errors: list[str] = []
    for key, value in required_text.items():
        if not str(value or "").strip():
            errors.append(f"{key} is required")
    for key, value in positive_ints.items():
        if int(value) <= 0:
            errors.append(f"{key} must be > 0")
    for key, value in (optional_text or {}).items():
        if value is None:
            continue
        if not str(value).strip():
            errors.append(f"{key} must not be blank when set")
    return errors


def classify_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "zip" in text and "bad" in text:
        return "malformed_zip"
    if "xml member exceeds" in text:
        return "oversized_xml_member"
    if "unable to resolve filing xml" in text:
        return "missing_zip_member"
    if "malformed" in text and "xml" in text:
        return "malformed_xml"
    if is_transient_network_error(exc):
        return "transient_network_error"
    return "processing_error"
