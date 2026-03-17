from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .routes import API_RELEASE, API_VERSION


_BASE_HEADERS = {
    "Content-Type": "application/json",
}


@dataclass(frozen=True)
class DeprecationMetadata:
    status: str = "active"
    sunset_date: str | None = None
    recommended_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sunset_date": self.sunset_date,
            "recommended_version": self.recommended_version,
        }


@dataclass(frozen=True)
class ResponseContext:
    request_id: str
    plan: str
    deprecation: DeprecationMetadata


def build_response_context(
    event: dict[str, Any] | None = None,
    context: Any | None = None,
    *,
    plan: str | None = None,
    deprecation: DeprecationMetadata | None = None,
) -> ResponseContext:
    request_context = (event or {}).get("requestContext") or {}
    request_id = (
        str(request_context.get("requestId") or "").strip()
        or str(getattr(context, "aws_request_id", "") or "").strip()
        or str(uuid4())
    )
    resolved_plan = str(plan or "public").strip() or "public"
    return ResponseContext(
        request_id=request_id,
        plan=resolved_plan,
        deprecation=deprecation or DeprecationMetadata(),
    )


def json_response(
    status_code: int,
    payload: dict[str, Any] | None,
    *,
    response_context: ResponseContext,
    meta: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    if status_code >= 400:
        return _structured_error_response(
            status_code,
            payload or {},
            response_context=response_context,
            meta=meta,
            headers=headers,
        )
    body = {
        "api_version": API_VERSION,
        "api_release": API_RELEASE,
        "request_id": response_context.request_id,
        "deprecation": response_context.deprecation.to_dict(),
        "plan": response_context.plan,
        "data": payload or {},
        "meta": meta or {},
        "errors": [],
    }
    return {
        "statusCode": status_code,
        "headers": _response_headers(response_context.deprecation, headers=headers),
        "body": json.dumps(body, default=_json_default),
    }


def error_response(
    status_code: int,
    message: str,
    *,
    response_context: ResponseContext,
    code: str | None = None,
    meta: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = {
        "api_version": API_VERSION,
        "api_release": API_RELEASE,
        "request_id": response_context.request_id,
        "deprecation": response_context.deprecation.to_dict(),
        "plan": response_context.plan,
        "data": {},
        "meta": meta or {},
        "errors": [
            {
                "code": str(code or _default_error_code(status_code)),
                "message": message,
            }
        ],
    }
    return {
        "statusCode": status_code,
        "headers": _response_headers(response_context.deprecation, headers=headers),
        "body": json.dumps(body, default=_json_default),
    }


def _response_headers(
    deprecation: DeprecationMetadata,
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, str]:
    resolved = dict(_BASE_HEADERS)
    if headers:
        resolved.update(headers)
    if deprecation.status == "deprecated":
        resolved["Deprecation"] = "true"
        if deprecation.sunset_date:
            resolved["Sunset"] = deprecation.sunset_date
    return resolved


def _structured_error_response(
    status_code: int,
    payload: dict[str, Any],
    *,
    response_context: ResponseContext,
    meta: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    details = dict(payload)
    code = details.pop("code", None)
    message = str(details.pop("message", "") or "Request failed")
    response_meta = dict(meta or {})
    if details:
        response_meta["details"] = details
    return error_response(
        status_code,
        message,
        response_context=response_context,
        code=str(code) if code else None,
        meta=response_meta,
        headers=headers,
    )


def _default_error_code(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "internal_error"
    return "error"


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
