from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import TypeVar

from verification.backend.shared.billing.service import EntitlementService, PLAN_CODE_ALIASES, PLAN_CODES
from verification.backend.shared.runtime_logging import log_structured


T = TypeVar("T")


def validate_stripe_billing_environment(env: Mapping[str, str] | None = None) -> None:
    source = env or {}
    enabled = _mapping_bool(source, "STRIPE_BILLING_ENABLED", False)
    if not enabled:
        return
    if not _clean_text(source.get("STRIPE_SECRET_KEY")):
        raise ValueError("STRIPE_SECRET_KEY is required when STRIPE_BILLING_ENABLED=true")
    if not _clean_text(source.get("STRIPE_WEBHOOK_SECRET")):
        raise ValueError("STRIPE_WEBHOOK_SECRET is required when STRIPE_BILLING_ENABLED=true")
    price_ids = _parse_price_ids(source.get("STRIPE_PRICE_IDS"))
    if not price_ids:
        raise ValueError("STRIPE_PRICE_IDS is required when STRIPE_BILLING_ENABLED=true")


def call_with_retries(
    operation_name: str,
    func: Callable[[], T],
    *,
    should_retry: Callable[[Exception], bool],
    logger: logging.Logger | None = None,
    max_attempts: int = 2,
    extra: dict[str, object] | None = None,
) -> T:
    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= attempts or not should_retry(exc):
                raise
            if logger is not None:
                log_structured(
                    logger,
                    "stripe_provider_retry",
                    level=logging.WARNING,
                    operation_name=operation_name,
                    attempt=attempt,
                    max_attempts=attempts,
                    **(extra or {}),
                )
    assert last_error is not None
    raise last_error


def _parse_price_ids(raw: str | None) -> dict[str, str]:
    candidate = _clean_text(raw)
    if not candidate:
        return {}
    import json

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("STRIPE_PRICE_IDS must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("STRIPE_PRICE_IDS must be a JSON object")
    price_ids: dict[str, str] = {}
    for key, value in payload.items():
        plan_key = str(key or "").strip().lower()
        if plan_key not in PLAN_CODES and plan_key not in PLAN_CODE_ALIASES:
            raise ValueError(f"STRIPE_PRICE_IDS contains unsupported plan key '{key}'")
        normalized_plan = EntitlementService().normalize_plan_code(plan_key)
        if normalized_plan == "free":
            raise ValueError("STRIPE_PRICE_IDS should not define a checkout price for the free plan")
        price_id = _clean_text(value)
        if not price_id:
            raise ValueError(f"STRIPE_PRICE_IDS entry for '{key}' must be a non-empty string")
        price_ids[normalized_plan] = price_id
    return price_ids


def _mapping_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    raw = source.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _clean_text(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None

