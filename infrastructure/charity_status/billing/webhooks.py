from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from charity_status.billing.checkout import _clean_text, _mapping_bool, _parse_price_ids
from charity_status.billing.trials import TrialLifecycleService
from charity_status.control_plane import ManagedBillingEvent, ManagedSubscription


SUPPORTED_STRIPE_EVENTS: tuple[str, ...] = (
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
)


class BillingWebhookError(ValueError):
    status_code = 400
    code = "billing_webhook_error"


class BillingWebhookNotEnabledError(BillingWebhookError):
    status_code = 404
    code = "not_found"


class BillingWebhookSignatureError(BillingWebhookError):
    status_code = 400
    code = "invalid_signature"


class BillingWebhookProcessingError(BillingWebhookError):
    status_code = 500
    code = "billing_webhook_processing_error"


@dataclass(frozen=True)
class StripeWebhookConfig:
    enabled: bool = False
    webhook_secret: str | None = None
    price_ids: dict[str, str] | None = None
    signature_tolerance_seconds: int = 300

    @property
    def plan_by_price_id(self) -> dict[str, str]:
        reverse: dict[str, str] = {}
        for plan_code, price_id in (self.price_ids or {}).items():
            reverse[str(price_id)] = str(plan_code)
        return reverse


class BillingWebhookStore(Protocol):
    def get_subscription(self, account_id: str) -> ManagedSubscription | None:
        ...

    def put_subscription(self, subscription: ManagedSubscription) -> None:
        ...

    def get_subscription_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedSubscription | None:
        ...

    def get_subscription_by_stripe_subscription_id(self, stripe_subscription_id: str) -> ManagedSubscription | None:
        ...

    def get_billing_event(self, event_id: str) -> ManagedBillingEvent | None:
        ...

    def put_billing_event(self, event: ManagedBillingEvent) -> None:
        ...


def load_stripe_webhook_config(env: Mapping[str, str] | None = None) -> StripeWebhookConfig:
    source = env or {}
    enabled = _mapping_bool(source, "STRIPE_BILLING_ENABLED", False)
    if not enabled:
        return StripeWebhookConfig(enabled=False, price_ids={})
    webhook_secret = _clean_text(source.get("STRIPE_WEBHOOK_SECRET"))
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET is required when STRIPE_BILLING_ENABLED=true")
    return StripeWebhookConfig(
        enabled=True,
        webhook_secret=webhook_secret,
        price_ids=_parse_price_ids(source.get("STRIPE_PRICE_IDS")),
        signature_tolerance_seconds=300,
    )


class StripeWebhookService:
    def __init__(
        self,
        *,
        store: BillingWebhookStore,
        config: StripeWebhookConfig,
        trial_lifecycle_service: TrialLifecycleService | None = None,
    ) -> None:
        self._store = store
        self._config = config
        self._trial_lifecycle_service = trial_lifecycle_service

    def handle(self, *, raw_body: str, signature_header: str | None) -> dict[str, Any]:
        if not self._config.enabled:
            raise BillingWebhookNotEnabledError("Stripe webhook endpoint is not enabled")
        payload = verify_and_parse_stripe_event(
            raw_body=raw_body,
            signature_header=signature_header,
            webhook_secret=self._config.webhook_secret or "",
            tolerance_seconds=self._config.signature_tolerance_seconds,
        )
        event_id = str(payload.get("id") or "").strip()
        event_type = str(payload.get("type") or "").strip()
        if not event_id or not event_type:
            raise BillingWebhookSignatureError("Stripe webhook payload is missing required event fields")
        existing = self._store.get_billing_event(event_id)
        if existing is not None:
            return {"received": True, "processed": False, "duplicate": True, "event_id": event_id}
        if event_type not in SUPPORTED_STRIPE_EVENTS:
            self._store.put_billing_event(
                ManagedBillingEvent(
                    event_id=event_id,
                    event_type=event_type,
                    processed_at=_utcnow(),
                    webhook_created_at=_stripe_epoch_to_iso(payload.get("created")),
                )
            )
            return {"received": True, "processed": False, "ignored": True, "event_id": event_id}

        data_object = ((payload.get("data") or {}).get("object") or {})
        if not isinstance(data_object, dict):
            raise BillingWebhookProcessingError("Stripe webhook payload is missing event data")
        subscription = self._resolve_subscription(event_type=event_type, event_object=data_object)
        if subscription is None:
            raise BillingWebhookProcessingError("Unable to resolve local account for Stripe webhook event")
        updated_subscription = self._apply_event(event_type=event_type, event_object=data_object, subscription=subscription)
        self._store.put_subscription(updated_subscription)
        if self._trial_lifecycle_service is not None:
            updated_subscription = self._trial_lifecycle_service.mark_paid_conversion(account_id=updated_subscription.account_id) or updated_subscription
        self._store.put_billing_event(
            ManagedBillingEvent(
                event_id=event_id,
                event_type=event_type,
                processed_at=_utcnow(),
                account_id=updated_subscription.account_id,
                stripe_customer_id=_event_customer_id(data_object) or updated_subscription.stripe_customer_id,
                stripe_subscription_id=_event_subscription_id(data_object) or updated_subscription.stripe_subscription_id,
                stripe_invoice_id=_optional_string(data_object.get("id")) if event_type.startswith("invoice.") else None,
                gross_amount=_event_gross_amount(event_type, data_object),
                tax_amount=_event_tax_amount(event_type, data_object),
                invoice_total=_event_invoice_total(event_type, data_object),
                currency=_optional_string(data_object.get("currency")),
                webhook_created_at=_stripe_epoch_to_iso(payload.get("created")),
            )
        )
        return {"received": True, "processed": True, "event_id": event_id}

    def _resolve_subscription(self, *, event_type: str, event_object: dict[str, Any]) -> ManagedSubscription | None:
        metadata = _event_metadata(event_object)
        account_id = _optional_string(metadata.get("account_id")) or _optional_string(event_object.get("client_reference_id"))
        if account_id:
            return self._store.get_subscription(account_id)
        subscription_id = _event_subscription_id(event_object)
        if subscription_id:
            by_subscription = self._store.get_subscription_by_stripe_subscription_id(subscription_id)
            if by_subscription is not None:
                return by_subscription
        customer_id = _event_customer_id(event_object)
        if customer_id:
            return self._store.get_subscription_by_stripe_customer_id(customer_id)
        return None

    def _apply_event(
        self,
        *,
        event_type: str,
        event_object: dict[str, Any],
        subscription: ManagedSubscription,
    ) -> ManagedSubscription:
        if event_type == "checkout.session.completed":
            return self._apply_checkout_completed(event_object, subscription)
        if event_type in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"}:
            return self._apply_subscription_event(event_object, subscription, is_deleted=event_type.endswith(".deleted"))
        if event_type in {"invoice.paid", "invoice.payment_failed"}:
            return self._apply_invoice_event(event_type, event_object, subscription)
        return subscription

    def _apply_checkout_completed(self, event_object: dict[str, Any], subscription: ManagedSubscription) -> ManagedSubscription:
        metadata = _event_metadata(event_object)
        return replace(
            subscription,
            stripe_customer_id=_event_customer_id(event_object) or subscription.stripe_customer_id,
            stripe_subscription_id=_event_subscription_id(event_object) or subscription.stripe_subscription_id,
            billing_status="checkout_completed",
            pending_plan_code=_optional_string(metadata.get("requested_plan_code")) or subscription.pending_plan_code,
            pending_plan_effective_at=None,
            stripe_subscription_schedule_id=None,
            pending_checkout_session_id=None,
            pending_checkout_session_url=None,
            pending_checkout_expires_at=None,
            updated_at=_utcnow(),
        )

    def _apply_subscription_event(
        self,
        event_object: dict[str, Any],
        subscription: ManagedSubscription,
        *,
        is_deleted: bool,
    ) -> ManagedSubscription:
        stripe_status = _optional_string(event_object.get("status")) or subscription.billing_status or "active"
        plan_code = self._plan_code_for_event(event_object) or subscription.plan_code
        period_start = _stripe_epoch_to_iso(event_object.get("current_period_start")) or subscription.billing_period_start
        period_end = _stripe_epoch_to_iso(event_object.get("current_period_end")) or subscription.billing_period_end
        schedule_id = _optional_string(event_object.get("schedule")) or subscription.stripe_subscription_schedule_id
        cancel_at_period_end = bool(event_object.get("cancel_at_period_end"))
        pending_plan_code = subscription.pending_plan_code
        pending_plan_effective_at = subscription.pending_plan_effective_at
        if is_deleted:
            pending_plan_code = None
            pending_plan_effective_at = None
            schedule_id = None
        elif cancel_at_period_end:
            pending_plan_code = pending_plan_code or "free"
            pending_plan_effective_at = period_end or pending_plan_effective_at
        elif pending_plan_code and plan_code == pending_plan_code:
            pending_plan_code = None
            pending_plan_effective_at = None
        effective_from = period_start or subscription.effective_from or _utcnow()
        effective_to = None if not is_deleted else (period_end or _stripe_epoch_to_iso(event_object.get("canceled_at")) or _utcnow())
        return replace(
            subscription,
            plan_code=plan_code,
            status=_local_subscription_status(stripe_status, deleted=is_deleted),
            effective_from=effective_from,
            effective_to=effective_to,
            stripe_customer_id=_event_customer_id(event_object) or subscription.stripe_customer_id,
            stripe_subscription_id=_event_subscription_id(event_object) or subscription.stripe_subscription_id,
            billing_status=stripe_status,
            billing_period_start=period_start,
            billing_period_end=period_end,
            pending_plan_code=pending_plan_code,
            pending_plan_effective_at=pending_plan_effective_at,
            stripe_subscription_schedule_id=schedule_id,
            pending_checkout_session_id=None,
            pending_checkout_session_url=None,
            pending_checkout_expires_at=None,
            updated_at=_utcnow(),
        )

    def _apply_invoice_event(
        self,
        event_type: str,
        event_object: dict[str, Any],
        subscription: ManagedSubscription,
    ) -> ManagedSubscription:
        billing_status = "payment_failed" if event_type == "invoice.payment_failed" else (subscription.billing_status or "active")
        period = _invoice_period_bounds(event_object)
        return replace(
            subscription,
            stripe_customer_id=_event_customer_id(event_object) or subscription.stripe_customer_id,
            stripe_subscription_id=_event_subscription_id(event_object) or subscription.stripe_subscription_id,
            billing_status=billing_status,
            billing_period_start=period[0] or subscription.billing_period_start,
            billing_period_end=period[1] or subscription.billing_period_end,
            pending_plan_effective_at=subscription.pending_plan_effective_at,
            stripe_subscription_schedule_id=subscription.stripe_subscription_schedule_id,
            updated_at=_utcnow(),
        )

    def _plan_code_for_event(self, event_object: dict[str, Any]) -> str | None:
        metadata = _event_metadata(event_object)
        requested_plan_code = _optional_string(metadata.get("requested_plan_code"))
        if requested_plan_code:
            return requested_plan_code
        price_id = _event_price_id(event_object)
        if not price_id:
            return None
        return self._config.plan_by_price_id.get(price_id)


def verify_and_parse_stripe_event(
    *,
    raw_body: str,
    signature_header: str | None,
    webhook_secret: str,
    tolerance_seconds: int = 300,
    now: datetime | None = None,
) -> dict[str, Any]:
    candidate = str(raw_body or "")
    if not candidate:
        raise BillingWebhookSignatureError("Stripe webhook body is required")
    timestamp, signatures = _parse_signature_header(signature_header)
    current = now or datetime.now(timezone.utc)
    if abs(int(current.timestamp()) - timestamp) > max(0, int(tolerance_seconds)):
        raise BillingWebhookSignatureError("Stripe webhook signature timestamp is outside the allowed tolerance")
    signed_payload = f"{timestamp}.{candidate}".encode("utf-8")
    expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, signature) for signature in signatures):
        raise BillingWebhookSignatureError("Stripe webhook signature is invalid")
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise BillingWebhookSignatureError("Stripe webhook body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise BillingWebhookSignatureError("Stripe webhook payload must be a JSON object")
    return payload


def _parse_signature_header(signature_header: str | None) -> tuple[int, list[str]]:
    header_value = _clean_text(signature_header)
    if not header_value:
        raise BillingWebhookSignatureError("Missing Stripe-Signature header")
    timestamp: int | None = None
    signatures: list[str] = []
    for part in header_value.split(","):
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "t" and value.isdigit():
            timestamp = int(value)
        elif key == "v1" and value:
            signatures.append(value)
    if timestamp is None or not signatures:
        raise BillingWebhookSignatureError("Stripe-Signature header is malformed")
    return timestamp, signatures


def _event_metadata(event_object: dict[str, Any]) -> dict[str, Any]:
    metadata = event_object.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    parent = (event_object.get("parent") or {}).get("subscription_details") or {}
    metadata = parent.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    return {}


def _event_customer_id(event_object: dict[str, Any]) -> str | None:
    return _optional_string(event_object.get("customer"))


def _event_subscription_id(event_object: dict[str, Any]) -> str | None:
    direct = _optional_string(event_object.get("subscription"))
    if direct:
        return direct
    return _optional_string(event_object.get("id")) if str(event_object.get("object") or "") == "subscription" else None


def _event_price_id(event_object: dict[str, Any]) -> str | None:
    items = (((event_object.get("items") or {}).get("data")) or [])
    if items and isinstance(items[0], dict):
        price_id = _optional_string(((items[0].get("price") or {}).get("id")))
        if price_id:
            return price_id
    lines = (((event_object.get("lines") or {}).get("data")) or [])
    if lines and isinstance(lines[0], dict):
        line = lines[0]
        price_id = _optional_string(((line.get("price") or {}).get("id")))
        if price_id:
            return price_id
    return None


def _event_gross_amount(event_type: str, event_object: dict[str, Any]) -> int | None:
    if not event_type.startswith("invoice."):
        return None
    return _optional_int(event_object.get("subtotal"))


def _event_tax_amount(event_type: str, event_object: dict[str, Any]) -> int | None:
    if not event_type.startswith("invoice."):
        return None
    tax = _optional_int(event_object.get("tax"))
    if tax is not None:
        return tax
    total_tax_amounts = event_object.get("total_tax_amounts") or []
    if isinstance(total_tax_amounts, list):
        return sum(_optional_int((item or {}).get("amount")) or 0 for item in total_tax_amounts)
    return None


def _event_invoice_total(event_type: str, event_object: dict[str, Any]) -> int | None:
    if not event_type.startswith("invoice."):
        return None
    return _optional_int(event_object.get("total"))


def _invoice_period_bounds(event_object: dict[str, Any]) -> tuple[str | None, str | None]:
    lines = (((event_object.get("lines") or {}).get("data")) or [])
    if not lines or not isinstance(lines[0], dict):
        return None, None
    period = lines[0].get("period") or {}
    return _stripe_epoch_to_iso(period.get("start")), _stripe_epoch_to_iso(period.get("end"))


def _stripe_epoch_to_iso(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        epoch = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _local_subscription_status(stripe_status: str, *, deleted: bool) -> str:
    if deleted or stripe_status in {"canceled", "incomplete_expired"}:
        return "canceled"
    if stripe_status == "scheduled":
        return "scheduled"
    return "active"


def _optional_string(value: Any) -> str | None:
    candidate = str(value or "").strip()
    return candidate or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()
