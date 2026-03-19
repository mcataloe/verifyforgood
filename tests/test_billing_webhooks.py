from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from time import time

from charity_status.billing.webhooks import (
    BillingWebhookSignatureError,
    StripeWebhookConfig,
    StripeWebhookService,
    _stripe_epoch_to_iso,
    load_stripe_webhook_config,
    verify_and_parse_stripe_event,
)
from charity_status.control_plane import ControlPlaneService, InMemoryControlPlaneStore


def test_load_stripe_webhook_config_requires_secret_when_enabled():
    try:
        load_stripe_webhook_config(
            {
                "STRIPE_BILLING_ENABLED": "true",
                "STRIPE_PRICE_IDS": '{"growth":"price_growth"}',
            }
        )
    except ValueError as exc:
        assert str(exc) == "STRIPE_WEBHOOK_SECRET is required when STRIPE_BILLING_ENABLED=true"
    else:
        assert False, "Expected Stripe webhook secret validation error"


def test_verify_and_parse_stripe_event_rejects_invalid_signature():
    payload = json.dumps({"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {}}})
    header = _sign_payload(payload, secret="whsec_right", timestamp=1770000000).replace("v1=", "v1=bad", 1)

    try:
        verify_and_parse_stripe_event(
            raw_body=payload,
            signature_header=header,
            webhook_secret="whsec_right",
            now=datetime.fromtimestamp(1770000000, tz=timezone.utc),
        )
    except BillingWebhookSignatureError as exc:
        assert "invalid" in str(exc)
    else:
        assert False, "Expected invalid signature error"


def test_stripe_webhook_service_syncs_subscription_and_invoice_data():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
    )

    checkout_payload = _event_payload(
        event_id="evt_checkout",
        event_type="checkout.session.completed",
        event_object={
            "object": "checkout.session",
            "id": "cs_123",
            "mode": "subscription",
            "customer": "cus_123",
            "subscription": "sub_123",
            "client_reference_id": account["id"],
            "metadata": {"account_id": account["id"], "requested_plan_code": "growth"},
        },
    )
    checkout_result = service.handle(
        raw_body=checkout_payload,
        signature_header=_sign_payload(checkout_payload, secret="whsec_test"),
    )
    after_checkout = control_plane.store.get_subscription(account["id"])

    assert checkout_result["processed"] is True
    assert after_checkout is not None
    assert after_checkout.billing_status == "checkout_completed"
    assert after_checkout.stripe_customer_id == "cus_123"
    assert after_checkout.stripe_subscription_id == "sub_123"

    subscription_payload = _event_payload(
        event_id="evt_subscription",
        event_type="customer.subscription.created",
        event_object={
            "object": "subscription",
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "current_period_start": 1770000000,
            "current_period_end": 1772592000,
            "metadata": {"account_id": account["id"]},
            "items": {"data": [{"price": {"id": "price_growth"}}]},
        },
    )
    service.handle(
        raw_body=subscription_payload,
        signature_header=_sign_payload(subscription_payload, secret="whsec_test"),
    )
    after_subscription = control_plane.store.get_subscription(account["id"])

    assert after_subscription is not None
    assert after_subscription.plan_code == "growth"
    assert after_subscription.status == "active"
    assert after_subscription.billing_status == "active"
    assert after_subscription.billing_period_start == _stripe_epoch_to_iso(1770000000)
    assert after_subscription.billing_period_end == _stripe_epoch_to_iso(1772592000)

    invoice_payload = _event_payload(
        event_id="evt_invoice_paid",
        event_type="invoice.paid",
        event_object={
            "object": "invoice",
            "id": "in_123",
            "customer": "cus_123",
            "subscription": "sub_123",
            "subtotal": 10000,
            "tax": 800,
            "total": 10800,
            "currency": "usd",
            "lines": {"data": [{"period": {"start": 1770000000, "end": 1772592000}}]},
        },
    )
    invoice_result = service.handle(
        raw_body=invoice_payload,
        signature_header=_sign_payload(invoice_payload, secret="whsec_test"),
    )
    billing_event = control_plane.store.get_billing_event("evt_invoice_paid")

    assert invoice_result["processed"] is True
    assert billing_event is not None
    assert billing_event.account_id == account["id"]
    assert billing_event.gross_amount == 10000
    assert billing_event.tax_amount == 800
    assert billing_event.invoice_total == 10800
    assert billing_event.currency == "usd"


def test_stripe_webhook_service_ignores_duplicate_events():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
    )
    payload = _event_payload(
        event_id="evt_duplicate",
        event_type="checkout.session.completed",
        event_object={
            "object": "checkout.session",
            "id": "cs_123",
            "mode": "subscription",
            "customer": "cus_123",
            "subscription": "sub_123",
            "client_reference_id": account["id"],
            "metadata": {"account_id": account["id"], "requested_plan_code": "growth"},
        },
    )
    signature = _sign_payload(payload, secret="whsec_test")

    first = service.handle(raw_body=payload, signature_header=signature)
    second = service.handle(raw_body=payload, signature_header=signature)

    assert first["processed"] is True
    assert second["processed"] is False
    assert second["duplicate"] is True


def _event_payload(*, event_id: str, event_type: str, event_object: dict[str, object]) -> str:
    return json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "created": 1770000000,
            "data": {"object": event_object},
        },
        separators=(",", ":"),
    )


def _sign_payload(payload: str, *, secret: str, timestamp: int | None = None) -> str:
    timestamp = int(time()) if timestamp is None else timestamp
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"
