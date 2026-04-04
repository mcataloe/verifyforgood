from __future__ import annotations

import json
import logging
import os
import re
import traceback
from dataclasses import dataclass
from typing import Any, Mapping


PRODUCTION_ENVIRONMENTS = {"prod", "production"}
DEFAULT_PRODUCTION_LOG_LEVEL = "INFO"
DEFAULT_NON_PRODUCTION_LOG_LEVEL = "DEBUG"

_REDACTED = "[REDACTED]"
_OMITTED = "[OMITTED]"

_SENSITIVE_FIELD_NAMES = {
    "authorization",
    "api_key",
    "apikey",
    "client_secret",
    "cookie",
    "database_url",
    "db_url",
    "dsn",
    "idempotency_key",
    "password",
    "secret",
    "set_cookie",
    "signature_header",
    "signed_payload",
    "stripe_signature",
    "token",
    "webhook_secret",
}

_PAYLOAD_FIELD_NAMES = {
    "body",
    "headers",
    "payload",
    "raw_body",
    "request_body",
    "request_headers",
    "response_body",
    "response_headers",
    "webhook_payload",
}

_URL_WITH_CREDENTIALS = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|mongodb|redis|amqp)\S*://[^/\s:@]+:[^/\s@]+@")
_SENSITIVE_TEXT = re.compile(
    r"(?i)(authorization:|bearer\s+[a-z0-9\-_\.]+|basic\s+[a-z0-9+/=]+|client_secret|webhook_secret|password=|token=|api[_-]?key=)"
)


@dataclass(frozen=True)
class RuntimeLoggingConfig:
    app_env: str
    log_level_name: str
    log_level: int
    include_stack_traces: bool


def configure_runtime_logging(
    env: Mapping[str, str] | None = None,
    *,
    logger: logging.Logger | None = None,
) -> RuntimeLoggingConfig:
    config = resolve_runtime_logging_config(env)
    logging.getLogger().setLevel(config.log_level)
    if logger is not None:
        logger.setLevel(config.log_level)
    return config


def resolve_runtime_logging_config(env: Mapping[str, str] | None = None) -> RuntimeLoggingConfig:
    source = dict(os.environ if env is None else env)
    app_env = str(source.get("APP_ENV") or "dev").strip().lower() or "dev"
    raw_level = str(source.get("LOG_LEVEL") or "").strip().upper()
    log_level_name = raw_level or (
        DEFAULT_PRODUCTION_LOG_LEVEL if app_env in PRODUCTION_ENVIRONMENTS else DEFAULT_NON_PRODUCTION_LOG_LEVEL
    )
    log_level = _coerce_log_level(log_level_name)
    raw_stack = source.get("LOG_STACK_TRACES")
    include_stack_traces = (
        str(raw_stack).strip().lower() == "true"
        if raw_stack is not None
        else app_env not in PRODUCTION_ENVIRONMENTS
    )
    return RuntimeLoggingConfig(
        app_env=app_env,
        log_level_name=log_level_name,
        log_level=log_level,
        include_stack_traces=include_stack_traces,
    )


def log_structured(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    payload = {"event": event, **sanitize_log_fields(fields)}
    try:
        logger.log(level, json.dumps(payload, sort_keys=True))
    except Exception:
        logger.log(level, "%s %s", event, sanitize_log_fields(fields))


def log_exception(
    logger: logging.Logger,
    event: str,
    exc: BaseException,
    *,
    env: Mapping[str, str] | None = None,
    level: int = logging.ERROR,
    include_stack_traces: bool | None = None,
    **fields: Any,
) -> None:
    config = resolve_runtime_logging_config(env)
    payload: dict[str, Any] = {
        "event": event,
        "error_type": type(exc).__name__,
        "error": sanitize_log_value(str(exc), key="error"),
        **sanitize_log_fields(fields),
    }
    if include_stack_traces if include_stack_traces is not None else config.include_stack_traces:
        payload["traceback"] = traceback.format_exc()
    log_structured(logger, event, level=level, **{key: value for key, value in payload.items() if key != "event"})


def sanitize_log_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): sanitize_log_value(value, key=str(key)) for key, value in fields.items()}


def sanitize_log_value(value: Any, *, key: str | None = None) -> Any:
    normalized_key = _normalize_key(key)
    if normalized_key and _is_payload_field(normalized_key):
        return _OMITTED
    if normalized_key and _is_sensitive_field(normalized_key):
        return _REDACTED
    if isinstance(value, Mapping):
        return {str(child_key): sanitize_log_value(child_value, key=str(child_key)) for child_key, child_value in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_log_value(item, key=key) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if _looks_like_credential_bearing_url(stripped):
            return _REDACTED
        if _looks_like_sensitive_text(stripped):
            return _REDACTED
        return stripped
    return value


def _coerce_log_level(level_name: str) -> int:
    return logging._nameToLevel.get(str(level_name or "").strip().upper(), logging.INFO)


def _normalize_key(key: str | None) -> str:
    return str(key or "").strip().lower().replace("-", "_")


def _is_payload_field(key: str) -> bool:
    return key in _PAYLOAD_FIELD_NAMES


def _is_sensitive_field(key: str) -> bool:
    if key in _SENSITIVE_FIELD_NAMES:
        return True
    return any(marker in key for marker in ("token", "secret", "password", "authorization", "api_key"))


def _looks_like_credential_bearing_url(value: str) -> bool:
    return bool(_URL_WITH_CREDENTIALS.search(value))


def _looks_like_sensitive_text(value: str) -> bool:
    return bool(_SENSITIVE_TEXT.search(value))


__all__ = [
    "RuntimeLoggingConfig",
    "configure_runtime_logging",
    "log_exception",
    "log_structured",
    "resolve_runtime_logging_config",
    "sanitize_log_fields",
    "sanitize_log_value",
]
