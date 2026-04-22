from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from verification.backend.shared.branding import load_branding_config

from .routes import API_RELEASE, API_VERSION


_BASE_HEADERS = {
    "Content-Type": "application/json",
}
_CORS_ALLOWED_HEADERS = "Content-Type,Authorization,X-Portal-Account-Id,X-Portal-Workspace-Id"
_CORS_ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"


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
    cors_origin: str | None = None


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
        cors_origin=_resolve_cors_origin(event),
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
        "headers": _response_headers(
            response_context.deprecation,
            cors_origin=response_context.cors_origin,
            headers=headers,
        ),
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
    response_meta = dict(meta or {})
    if status_code >= 500:
        response_meta.setdefault("support", load_branding_config().support_details())
    body = {
        "api_version": API_VERSION,
        "api_release": API_RELEASE,
        "request_id": response_context.request_id,
        "deprecation": response_context.deprecation.to_dict(),
        "plan": response_context.plan,
        "data": {},
        "meta": response_meta,
        "errors": [
            {
                "code": str(code or _default_error_code(status_code)),
                "message": message,
            }
        ],
    }
    return {
        "statusCode": status_code,
        "headers": _response_headers(
            response_context.deprecation,
            cors_origin=response_context.cors_origin,
            headers=headers,
        ),
        "body": json.dumps(body, default=_json_default),
    }


def _response_headers(
    deprecation: DeprecationMetadata,
    *,
    cors_origin: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, str]:
    resolved = dict(_BASE_HEADERS)
    if headers:
        resolved.update(headers)
    if cors_origin:
        resolved["Access-Control-Allow-Origin"] = cors_origin
        resolved["Access-Control-Allow-Headers"] = _CORS_ALLOWED_HEADERS
        resolved["Access-Control-Allow-Methods"] = _CORS_ALLOWED_METHODS
        resolved["Vary"] = _merge_vary_header(resolved.get("Vary"), "Origin")
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


def _resolve_cors_origin(event: dict[str, Any] | None) -> str | None:
    if not event:
        return None
    headers = event.get("headers") or {}
    origin = _get_header(headers, "origin")
    if not origin:
        return None
    if origin in _allowed_cors_origins():
        return origin
    return None


def _allowed_cors_origins() -> set[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    return {value.strip() for value in raw.split(",") if value.strip()}


def _get_header(headers: dict[str, Any], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if str(key).lower() == target:
            text = str(value).strip()
            return text or None
    return None


def _merge_vary_header(existing: str | None, value: str) -> str:
    parts = [item.strip() for item in str(existing or "").split(",") if item.strip()]
    if value not in parts:
        parts.append(value)
    return ", ".join(parts)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

