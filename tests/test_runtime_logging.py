from __future__ import annotations

import io
import json
import logging

from verification.backend.shared.billing.runtime import call_with_retries
from verification.backend.shared.runtime_logging import configure_runtime_logging, log_exception, resolve_runtime_logging_config, sanitize_log_fields


def test_runtime_logging_defaults_to_info_without_traces_in_prod():
    config = resolve_runtime_logging_config({"APP_ENV": "prod"})

    assert config.log_level_name == "INFO"
    assert config.log_level == logging.INFO
    assert config.include_stack_traces is False


def test_runtime_logging_defaults_to_debug_with_traces_outside_prod():
    config = resolve_runtime_logging_config({"APP_ENV": "dev"})

    assert config.log_level_name == "DEBUG"
    assert config.log_level == logging.DEBUG
    assert config.include_stack_traces is True


def test_runtime_logging_respects_explicit_log_level_override():
    config = resolve_runtime_logging_config({"APP_ENV": "prod", "LOG_LEVEL": "WARNING"})

    assert config.log_level_name == "WARNING"
    assert config.log_level == logging.WARNING


def test_configure_runtime_logging_installs_console_handler_when_root_has_none():
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level
    try:
        root_logger.handlers = []
        configure_runtime_logging({"APP_ENV": "dev"})

        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)
        assert root_logger.handlers[0].formatter is not None
        assert root_logger.handlers[0].formatter._fmt == "%(message)s"
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def test_log_exception_omits_traceback_in_prod_by_default():
    stream = io.StringIO()
    logger = logging.getLogger("test.runtime_logging.prod")
    logger.handlers = [logging.StreamHandler(stream)]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    try:
        raise ValueError("database_url=postgresql://user:secret@localhost/db")
    except ValueError as exc:
        log_exception(logger, "runtime.failed", exc, env={"APP_ENV": "prod"})

    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "runtime.failed"
    assert payload["error_type"] == "ValueError"
    assert payload["error"] == "[REDACTED]"
    assert "traceback" not in payload


def test_log_exception_can_include_traceback_when_enabled():
    stream = io.StringIO()
    logger = logging.getLogger("test.runtime_logging.trace")
    logger.handlers = [logging.StreamHandler(stream)]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        log_exception(logger, "runtime.failed", exc, env={"APP_ENV": "prod", "LOG_STACK_TRACES": "true"})

    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "runtime.failed"
    assert "traceback" in payload


def test_sanitize_log_fields_redacts_sensitive_values_and_payloads():
    sanitized = sanitize_log_fields(
        {
            "Authorization": "Bearer abc123",
            "request_body": '{"client_secret":"abc"}',
            "headers": {"X-Test": "1"},
            "database_url": "postgresql://user:secret@localhost/db",
            "payload_fingerprint": "safe",
            "count": 2,
        }
    )

    assert sanitized["Authorization"] == "[REDACTED]"
    assert sanitized["request_body"] == "[OMITTED]"
    assert sanitized["headers"] == "[OMITTED]"
    assert sanitized["database_url"] == "[REDACTED]"
    assert sanitized["payload_fingerprint"] == "safe"
    assert sanitized["count"] == 2


def test_billing_retry_logging_redacts_idempotency_key():
    stream = io.StringIO()
    logger = logging.getLogger("test.runtime_logging.billing")
    logger.handlers = [logging.StreamHandler(stream)]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("try again")
        return "ok"

    result = call_with_retries(
        "portal session creation",
        flaky,
        should_retry=lambda exc: isinstance(exc, RuntimeError),
        logger=logger,
        extra={"account_id": "acct_123", "idempotency_key": "portal:acct_123:cus_123"},
    )

    assert result == "ok"
    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "stripe_provider_retry"
    assert payload["account_id"] == "acct_123"
    assert payload["idempotency_key"] == "[REDACTED]"

