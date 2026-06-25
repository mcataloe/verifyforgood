from __future__ import annotations

from urllib.error import URLError

from verification.backend.shared.billing.checkout import BillingProviderError, StripeCheckoutConfig
from verification.backend.shared.billing.plan_changes import BillingPlanChangeService, HttpStripePlanChangeClient, StripePriceSnapshot, StripeSubscriptionSnapshot
from verification.backend.shared.control_plane import ControlPlaneService, InMemoryControlPlaneStore, ManagedSubscription


class _StripePlanChangeClient:
    def __init__(self, snapshot: StripeSubscriptionSnapshot) -> None:
        self.snapshot = snapshot
        self.released_schedules: list[str] = []
        self.scheduled_plan_price_ids: list[str] = []
        self.applied_price_ids: list[str] = []

    def retrieve_subscription(self, *, subscription_id: str) -> StripeSubscriptionSnapshot:
        assert subscription_id == self.snapshot.subscription_id
        return self.snapshot

    def retrieve_price(self, *, price_id: str) -> StripePriceSnapshot:
        return StripePriceSnapshot(price_id=price_id, interval="month", interval_count=1)

    def apply_immediate_plan_change(self, *, subscription: StripeSubscriptionSnapshot, account_id: str, plan_code: str, price_id: str, idempotency_key: str) -> StripeSubscriptionSnapshot:
        assert account_id.startswith("acct_")
        assert plan_code
        assert idempotency_key == f"plan-change:{account_id}:upgrade:{plan_code}"
        self.applied_price_ids.append(price_id)
        self.snapshot = StripeSubscriptionSnapshot(
            subscription_id=subscription.subscription_id,
            customer_id=subscription.customer_id,
            item_id=subscription.item_id,
            price_id=price_id,
            status="active",
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            current_period_start_epoch=subscription.current_period_start_epoch,
            current_period_end_epoch=subscription.current_period_end_epoch,
            quantity=subscription.quantity,
            cancel_at_period_end=False,
            schedule_id=None,
        )
        return self.snapshot

    def set_cancel_at_period_end(self, *, subscription_id: str, cancel_at_period_end: bool, idempotency_key: str) -> StripeSubscriptionSnapshot:
        assert subscription_id == self.snapshot.subscription_id
        assert idempotency_key.startswith("plan-change:")
        self.snapshot = StripeSubscriptionSnapshot(
            subscription_id=self.snapshot.subscription_id,
            customer_id=self.snapshot.customer_id,
            item_id=self.snapshot.item_id,
            price_id=self.snapshot.price_id,
            status=self.snapshot.status,
            current_period_start=self.snapshot.current_period_start,
            current_period_end=self.snapshot.current_period_end,
            current_period_start_epoch=self.snapshot.current_period_start_epoch,
            current_period_end_epoch=self.snapshot.current_period_end_epoch,
            quantity=self.snapshot.quantity,
            cancel_at_period_end=cancel_at_period_end,
            schedule_id=self.snapshot.schedule_id,
        )
        return self.snapshot

    def create_schedule_from_subscription(self, *, subscription_id: str, idempotency_key: str) -> str:
        assert subscription_id == self.snapshot.subscription_id
        assert idempotency_key.startswith("plan-change:")
        self.snapshot = StripeSubscriptionSnapshot(
            subscription_id=self.snapshot.subscription_id,
            customer_id=self.snapshot.customer_id,
            item_id=self.snapshot.item_id,
            price_id=self.snapshot.price_id,
            status=self.snapshot.status,
            current_period_start=self.snapshot.current_period_start,
            current_period_end=self.snapshot.current_period_end,
            current_period_start_epoch=self.snapshot.current_period_start_epoch,
            current_period_end_epoch=self.snapshot.current_period_end_epoch,
            quantity=self.snapshot.quantity,
            cancel_at_period_end=self.snapshot.cancel_at_period_end,
            schedule_id="sub_sched_test_123",
        )
        return "sub_sched_test_123"

    def update_schedule_for_downgrade(
        self,
        *,
        schedule_id: str,
        subscription: StripeSubscriptionSnapshot,
        requested_price: StripePriceSnapshot,
        account_id: str,
        requested_plan_code: str,
        idempotency_key: str,
    ) -> str:
        assert schedule_id == "sub_sched_test_123"
        assert requested_plan_code
        assert account_id.startswith("acct_")
        assert idempotency_key.startswith("plan-change:")
        self.scheduled_plan_price_ids.append(requested_price.price_id)
        return schedule_id

    def release_schedule(self, *, schedule_id: str, idempotency_key: str) -> None:
        assert idempotency_key.startswith("plan-change:")
        self.released_schedules.append(schedule_id)
        self.snapshot = StripeSubscriptionSnapshot(
            subscription_id=self.snapshot.subscription_id,
            customer_id=self.snapshot.customer_id,
            item_id=self.snapshot.item_id,
            price_id=self.snapshot.price_id,
            status=self.snapshot.status,
            current_period_start=self.snapshot.current_period_start,
            current_period_end=self.snapshot.current_period_end,
            current_period_start_epoch=self.snapshot.current_period_start_epoch,
            current_period_end_epoch=self.snapshot.current_period_end_epoch,
            quantity=self.snapshot.quantity,
            cancel_at_period_end=False,
            schedule_id=None,
        )


class _FailingStripePlanChangeClient(_StripePlanChangeClient):
    def apply_immediate_plan_change(self, *, subscription: StripeSubscriptionSnapshot, account_id: str, plan_code: str, price_id: str, idempotency_key: str) -> StripeSubscriptionSnapshot:
        raise BillingProviderError("Stripe rejected the request during subscription upgrade")


def test_billing_plan_change_applies_upgrade_immediately():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Upgrade Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            effective_from="2026-03-01T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    stripe = _StripePlanChangeClient(
        StripeSubscriptionSnapshot(
            subscription_id="sub_test_123",
            customer_id="cus_test_123",
            item_id="si_test_123",
            price_id="price_growth",
            status="active",
            current_period_start="2026-03-01T00:00:00+00:00",
            current_period_end="2026-04-01T00:00:00+00:00",
            current_period_start_epoch=1772323200,
            current_period_end_epoch=1775001600,
            quantity=1,
            cancel_at_period_end=False,
            schedule_id=None,
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth", "pro": "price_pro"},
        ),
        stripe_client=stripe,
    )

    result = service.change_plan(account_id=account["id"], payload={"plan_code": "pro"})
    updated = control_plane.store.get_subscription(account["id"])

    assert result["change_type"] == "upgrade"
    assert result["current_plan_code"] == "pro"
    assert result["pending_plan_code"] is None
    assert updated is not None
    assert updated.plan_code == "pro"
    assert updated.pending_plan_code is None
    assert stripe.applied_price_ids == ["price_pro"]


def test_billing_plan_change_schedules_downgrade_for_next_billing_cycle():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Downgrade Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="pro",
            status="active",
            effective_from="2026-03-01T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    stripe = _StripePlanChangeClient(
        StripeSubscriptionSnapshot(
            subscription_id="sub_test_123",
            customer_id="cus_test_123",
            item_id="si_test_123",
            price_id="price_pro",
            status="active",
            current_period_start="2026-03-01T00:00:00+00:00",
            current_period_end="2026-04-01T00:00:00+00:00",
            current_period_start_epoch=1772323200,
            current_period_end_epoch=1775001600,
            quantity=1,
            cancel_at_period_end=False,
            schedule_id=None,
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth", "pro": "price_pro"},
        ),
        stripe_client=stripe,
    )

    result = service.change_plan(account_id=account["id"], payload={"plan_code": "growth"})
    updated = control_plane.store.get_subscription(account["id"])

    assert result["change_type"] == "downgrade_scheduled"
    assert result["current_plan_code"] == "pro"
    assert result["pending_plan_code"] == "growth"
    assert result["pending_plan_effective_at"] == "2026-04-01T00:00:00+00:00"
    assert updated is not None
    assert updated.plan_code == "pro"
    assert updated.pending_plan_code == "growth"
    assert updated.pending_plan_effective_at == "2026-04-01T00:00:00+00:00"
    assert updated.stripe_subscription_schedule_id == "sub_sched_test_123"
    assert stripe.scheduled_plan_price_ids == ["price_growth"]
    assert updated.cancel_at_period_end is False


def test_billing_plan_change_upgrade_overrides_pending_downgrade():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Override Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="pro",
            status="active",
            effective_from="2026-03-01T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            stripe_subscription_schedule_id="sub_sched_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            pending_plan_code="growth",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    stripe = _StripePlanChangeClient(
        StripeSubscriptionSnapshot(
            subscription_id="sub_test_123",
            customer_id="cus_test_123",
            item_id="si_test_123",
            price_id="price_pro",
            status="active",
            current_period_start="2026-03-01T00:00:00+00:00",
            current_period_end="2026-04-01T00:00:00+00:00",
            current_period_start_epoch=1772323200,
            current_period_end_epoch=1775001600,
            quantity=1,
            cancel_at_period_end=False,
            schedule_id="sub_sched_test_123",
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"pro": "price_pro", "enterprise": "price_enterprise"},
        ),
        stripe_client=stripe,
    )

    result = service.change_plan(account_id=account["id"], payload={"plan_code": "enterprise"})
    updated = control_plane.store.get_subscription(account["id"])

    assert result["change_type"] == "upgrade"
    assert result["current_plan_code"] == "enterprise"
    assert result["pending_plan_code"] is None
    assert updated is not None
    assert updated.plan_code == "enterprise"
    assert updated.pending_plan_code is None
    assert stripe.released_schedules == ["sub_sched_test_123"]
    assert stripe.applied_price_ids == ["price_enterprise"]
    assert updated.cancel_at_period_end is False


def test_billing_plan_change_schedules_cancellation_at_period_end():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Cancel Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="pro",
            status="active",
            effective_from="2026-03-01T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            stripe_subscription_schedule_id="sub_sched_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            pending_plan_code="growth",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    stripe = _StripePlanChangeClient(
        StripeSubscriptionSnapshot(
            subscription_id="sub_test_123",
            customer_id="cus_test_123",
            item_id="si_test_123",
            price_id="price_pro",
            status="active",
            current_period_start="2026-03-01T00:00:00+00:00",
            current_period_end="2026-04-01T00:00:00+00:00",
            current_period_start_epoch=1772323200,
            current_period_end_epoch=1775001600,
            quantity=1,
            cancel_at_period_end=False,
            schedule_id="sub_sched_test_123",
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth", "pro": "price_pro"},
        ),
        stripe_client=stripe,
    )

    result = service.change_plan(account_id=account["id"], payload={"plan_code": "free"})
    updated = control_plane.store.get_subscription(account["id"])

    assert result["change_type"] == "cancellation_scheduled"
    assert result["current_plan_code"] == "pro"
    assert result["pending_plan_code"] == "free"
    assert updated is not None
    assert updated.plan_code == "pro"
    assert updated.pending_plan_code == "free"
    assert updated.pending_plan_effective_at == "2026-04-01T00:00:00+00:00"
    assert updated.cancel_at_period_end is True
    assert updated.stripe_subscription_schedule_id is None
    assert stripe.released_schedules == ["sub_sched_test_123"]


def test_billing_plan_change_reuses_matching_pending_cancellation():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Cancel Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="pro",
            status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_end="2026-04-01T00:00:00+00:00",
            pending_plan_code="free",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            cancel_at_period_end=True,
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth", "pro": "price_pro"},
        ),
        stripe_client=_StripePlanChangeClient(
            StripeSubscriptionSnapshot(
                subscription_id="sub_test_123",
                customer_id="cus_test_123",
                item_id="si_test_123",
                price_id="price_pro",
                status="active",
                current_period_start="2026-03-01T00:00:00+00:00",
                current_period_end="2026-04-01T00:00:00+00:00",
                current_period_start_epoch=1772323200,
                current_period_end_epoch=1775001600,
                quantity=1,
                cancel_at_period_end=True,
                schedule_id=None,
            )
        ),
    )

    result = service.change_plan(account_id=account["id"], payload={"plan_code": "free"})

    assert result["change_type"] == "cancellation_scheduled"
    assert result["reused"] is True


def test_billing_plan_change_paid_request_clears_pending_cancellation_and_schedules_lower_paid_plan():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Resume Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="pro",
            status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            pending_plan_code="free",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            cancel_at_period_end=True,
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    stripe = _StripePlanChangeClient(
        StripeSubscriptionSnapshot(
            subscription_id="sub_test_123",
            customer_id="cus_test_123",
            item_id="si_test_123",
            price_id="price_pro",
            status="active",
            current_period_start="2026-03-01T00:00:00+00:00",
            current_period_end="2026-04-01T00:00:00+00:00",
            current_period_start_epoch=1772323200,
            current_period_end_epoch=1775001600,
            quantity=1,
            cancel_at_period_end=True,
            schedule_id=None,
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth", "pro": "price_pro"},
        ),
        stripe_client=stripe,
    )

    result = service.change_plan(account_id=account["id"], payload={"plan_code": "growth"})
    updated = control_plane.store.get_subscription(account["id"])

    assert result["change_type"] == "downgrade_scheduled"
    assert result["pending_plan_code"] == "growth"
    assert updated is not None
    assert updated.pending_plan_code == "growth"
    assert updated.cancel_at_period_end is False
    assert updated.stripe_subscription_schedule_id == "sub_sched_test_123"


def test_billing_plan_change_surfaces_stripe_failures():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Failure Account", "ein": "123456789"})
    control_plane.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            effective_from="2026-03-01T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    service = BillingPlanChangeService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth", "pro": "price_pro"},
        ),
        stripe_client=_FailingStripePlanChangeClient(
            StripeSubscriptionSnapshot(
                subscription_id="sub_test_123",
                customer_id="cus_test_123",
                item_id="si_test_123",
                price_id="price_growth",
                status="active",
                current_period_start="2026-03-01T00:00:00+00:00",
                current_period_end="2026-04-01T00:00:00+00:00",
                current_period_start_epoch=1772323200,
                current_period_end_epoch=1775001600,
                quantity=1,
                cancel_at_period_end=False,
                schedule_id=None,
            )
        ),
    )

    try:
        service.change_plan(account_id=account["id"], payload={"plan_code": "pro"})
    except BillingProviderError as exc:
        assert "Stripe rejected the request" in str(exc)
    else:
        assert False, "Expected Stripe provider error"


def test_http_stripe_plan_change_client_retries_transient_url_errors(monkeypatch):
    attempts = {"count": 0}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return (
                b'{"id":"sub_test_123","customer":"cus_test_123","status":"active",'
                b'"current_period_start":1772323200,"current_period_end":1775001600,'
                b'"items":{"data":[{"id":"si_test_123","quantity":1,"price":{"id":"price_growth"}}]}}'
            )

    def _fake_urlopen(request, timeout=15):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise URLError("temporary outage")
        return _Response()

    monkeypatch.setattr("verification.backend.shared.billing.plan_changes.urlopen", _fake_urlopen)
    client = HttpStripePlanChangeClient(secret_key="sk_test_123")

    snapshot = client.retrieve_subscription(subscription_id="sub_test_123")

    assert snapshot.subscription_id == "sub_test_123"
    assert attempts["count"] == 2

