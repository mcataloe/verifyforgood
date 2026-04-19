from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from time import time

from verification.billing.webhooks import (
    BillingWebhookSignatureError,
    StripeWebhookConfig,
    StripeWebhookService,
    _stripe_epoch_to_iso,
    load_stripe_webhook_config,
    verify_and_parse_stripe_event,
)
from verification.billing.trials import TrialConfig, TrialLifecycleService
from verification.control_plane import ControlPlaneService, InMemoryControlPlaneStore


class _PlanCatalogProvider:
    class _Mapping:
        def __init__(self, internal_plan_id: str) -> None:
            self.internal_plan_id = internal_plan_id

    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def get_mapping_for_price_id(self, stripe_price_id: str):
        self.calls.append(stripe_price_id)
        internal_plan_id = self.mapping.get(stripe_price_id)
        if internal_plan_id is None:
            raise ValueError("missing mapping")
        return self._Mapping(internal_plan_id)


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


def test_verify_and_parse_stripe_event_rejects_malformed_signature_header():
    payload = json.dumps({"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {}}})

    try:
        verify_and_parse_stripe_event(
            raw_body=payload,
            signature_header="t=1770000000",
            webhook_secret="whsec_right",
            now=datetime.fromtimestamp(1770000000, tz=timezone.utc),
        )
    except BillingWebhookSignatureError as exc:
        assert "malformed" in str(exc)
    else:
        assert False, "Expected malformed signature error"


def test_verify_and_parse_stripe_event_rejects_signature_outside_tolerance():
    payload = json.dumps({"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {}}})
    header = _sign_payload(payload, secret="whsec_right", timestamp=1770000000)

    try:
        verify_and_parse_stripe_event(
            raw_body=payload,
            signature_header=header,
            webhook_secret="whsec_right",
            tolerance_seconds=300,
            now=datetime.fromtimestamp(1770000401, tz=timezone.utc),
        )
    except BillingWebhookSignatureError as exc:
        assert "tolerance" in str(exc)
    else:
        assert False, "Expected tolerance error"


def test_stripe_webhook_service_syncs_subscription_and_invoice_data():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    plan_catalog = _PlanCatalogProvider({"price_growth": "growth"})
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
        plan_catalog_provider=plan_catalog,
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
    assert plan_catalog.calls == ["price_growth"]

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
    assert billing_event.processing_outcome == "processed"
    assert billing_event.payload_fingerprint is not None


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


def test_stripe_webhook_service_persists_ignored_outcome_for_unsupported_events():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
    )
    payload = _event_payload(
        event_id="evt_ignored",
        event_type="customer.created",
        event_object={"object": "customer", "id": "cus_123"},
    )

    result = service.handle(raw_body=payload, signature_header=_sign_payload(payload, secret="whsec_test"))
    event = control_plane.store.get_billing_event("evt_ignored")

    assert result == {"received": True, "processed": False, "ignored": True, "event_id": "evt_ignored"}
    assert event is not None
    assert event.processing_outcome == "ignored"
    assert event.payload_fingerprint is not None


def test_stripe_webhook_service_clears_failed_payment_state_after_invoice_paid():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        control_plane.store.get_subscription(account["id"]).__class__(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
            billing_status="payment_failed",
            billing_period_start="2026-02-01T00:00:00+00:00",
            billing_period_end="2026-03-01T00:00:00+00:00",
            grace_period_ends_at="2026-02-08T00:00:00+00:00",
            updated_at="2026-02-01T00:00:00+00:00",
        )
    )
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
    )
    payload = _event_payload(
        event_id="evt_invoice_paid",
        event_type="invoice.paid",
        event_object={
            "object": "invoice",
            "id": "in_123",
            "customer": "cus_123",
            "subscription": "sub_123",
            "lines": {"data": [{"period": {"start": 1770000000, "end": 1772592000}}]},
        },
    )

    service.handle(raw_body=payload, signature_header=_sign_payload(payload, secret="whsec_test"))

    updated = control_plane.store.get_subscription(account["id"])
    assert updated is not None
    assert updated.billing_status == "active"
    assert updated.billing_period_end == _stripe_epoch_to_iso(1772592000)
    assert updated.grace_period_ends_at is None


def test_stripe_webhook_service_sets_grace_period_on_payment_failed():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        control_plane.store.get_subscription(account["id"]).__class__(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
            billing_status="active",
            updated_at="2026-02-01T00:00:00+00:00",
        )
    )
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
            payment_failure_grace_period_days=5,
        ),
    )
    payload = _event_payload(
        event_id="evt_invoice_failed",
        event_type="invoice.payment_failed",
        event_object={
            "object": "invoice",
            "id": "in_999",
            "customer": "cus_123",
            "subscription": "sub_123",
            "lines": {"data": [{"period": {"start": 1770000000, "end": 1772592000}}]},
        },
    )

    before = datetime.now(timezone.utc)
    service.handle(raw_body=payload, signature_header=_sign_payload(payload, secret="whsec_test"))
    after = datetime.now(timezone.utc)

    updated = control_plane.store.get_subscription(account["id"])
    assert updated is not None
    assert updated.billing_status == "payment_failed"
    assert updated.grace_period_ends_at is not None
    parsed = datetime.fromisoformat(updated.grace_period_ends_at)
    assert before + timedelta(days=5) <= parsed <= after + timedelta(days=5, seconds=1)


def test_stripe_webhook_service_updates_cancel_at_period_end_and_pending_downgrade():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        control_plane.store.get_subscription(account["id"]).__class__(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
            billing_status="active",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
    )
    payload = _event_payload(
        event_id="evt_subscription_updated",
        event_type="customer.subscription.updated",
        event_object={
            "object": "subscription",
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "current_period_start": 1770000000,
            "current_period_end": 1772592000,
            "cancel_at_period_end": True,
            "items": {"data": [{"price": {"id": "price_growth"}}]},
        },
    )

    service.handle(raw_body=payload, signature_header=_sign_payload(payload, secret="whsec_test"))

    updated = control_plane.store.get_subscription(account["id"])
    assert updated is not None
    assert updated.cancel_at_period_end is True
    assert updated.pending_plan_code == "free"
    assert updated.pending_plan_effective_at == _stripe_epoch_to_iso(1772592000)


def test_stripe_webhook_service_marks_deleted_subscription_without_losing_stripe_ids():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        control_plane.store.get_subscription(account["id"]).__class__(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
            billing_status="active",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
    )
    payload = _event_payload(
        event_id="evt_subscription_deleted",
        event_type="customer.subscription.deleted",
        event_object={
            "object": "subscription",
            "id": "sub_123",
            "customer": "cus_123",
            "status": "canceled",
            "current_period_end": 1772592000,
            "canceled_at": 1771000000,
        },
    )

    service.handle(raw_body=payload, signature_header=_sign_payload(payload, secret="whsec_test"))

    updated = control_plane.store.get_subscription(account["id"])
    assert updated is not None
    assert updated.status == "canceled"
    assert updated.stripe_customer_id == "cus_123"
    assert updated.stripe_subscription_id == "sub_123"


def test_stripe_webhook_marks_active_trial_as_converted_when_paid_subscription_syncs():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Webhook Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        control_plane.store.get_subscription(account["id"]).__class__(
            account_id=account["id"],
            plan_code="free",
            status="active",
            effective_from="2026-03-19T00:00:00+00:00",
            trial_status="active",
            trial_started_at="2026-03-19T00:00:00+00:00",
            trial_ends_at="2026-04-02T00:00:00+00:00",
            trial_trigger_event="POST /v1/verify",
            trial_consumed=True,
            stripe_customer_id="cus_123",
            stripe_subscription_id="sub_123",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    service = StripeWebhookService(
        store=control_plane.store,
        config=StripeWebhookConfig(
            enabled=True,
            webhook_secret="whsec_test",
            price_ids={"growth": "price_growth"},
        ),
        trial_lifecycle_service=trial_service,
    )
    payload = _event_payload(
        event_id="evt_subscription",
        event_type="customer.subscription.updated",
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

    service.handle(raw_body=payload, signature_header=_sign_payload(payload, secret="whsec_test"))

    updated = control_plane.store.get_subscription(account["id"])
    assert updated is not None
    assert updated.plan_code == "growth"
    assert updated.trial_status == "converted"
    assert updated.trial_termination_reason == "converted_to_paid"


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

