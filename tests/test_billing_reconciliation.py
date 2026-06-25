from __future__ import annotations

from verification.backend.shared.billing.checkout import BillingConflictError, StripeCheckoutConfig
from verification.backend.shared.billing.organization_billing import BillingService, ConfiguredStripeBillingProvider, ControlPlaneBillingCustomerRepository, ControlPlaneBillingEventRepository, ControlPlaneBillingSubscriptionRepository, PlanCatalogMapping
from verification.backend.shared.billing.reconciliation import BillingReconciliationService
from verification.backend.shared.control_plane import ControlPlaneService, InMemoryControlPlaneStore, ManagedSubscription


def _billing_service(store):
    return BillingService(
        customers=ControlPlaneBillingCustomerRepository(store),
        subscriptions=ControlPlaneBillingSubscriptionRepository(store),
        events=ControlPlaneBillingEventRepository(store),
        provider=ConfiguredStripeBillingProvider(
            [
                PlanCatalogMapping(internal_plan_id="growth", stripe_price_id="price_growth"),
                PlanCatalogMapping(internal_plan_id="pro", stripe_price_id="price_pro"),
            ]
        ),
    )


class _StripeLookupClient:
    def __init__(self, *, snapshot=None, snapshots=None):
        self.snapshot = snapshot
        self.snapshots = snapshots or []
        self.retrieve_calls: list[str] = []
        self.list_calls: list[str] = []

    def retrieve_subscription(self, *, subscription_id: str):
        self.retrieve_calls.append(subscription_id)
        return self.snapshot

    def list_customer_subscriptions(self, *, customer_id: str):
        self.list_calls.append(customer_id)
        return self.snapshots


def test_billing_reconciliation_updates_local_state_from_subscription_snapshot():
    store = InMemoryControlPlaneStore()
    control_plane = ControlPlaneService(store=store)
    account = control_plane.create_account({"name": "Reconcile Org", "ein": "123456789"})
    store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="free",
            status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="checkout_pending",
            pending_plan_code="growth",
            pending_checkout_session_id="cs_test_123",
            pending_checkout_session_url="https://checkout.stripe.com/c/pay/cs_test_123",
            updated_at="2026-03-29T00:00:00+00:00",
        )
    )
    stripe_client = _StripeLookupClient(
        snapshot=type(
            "Snapshot",
            (),
            {
                "subscription_id": "sub_test_123",
                "customer_id": "cus_test_123",
                "item_id": "si_test_123",
                "price_id": "price_growth",
                "status": "active",
                "current_period_start": "2026-03-29T00:00:00+00:00",
                "current_period_end": "2026-04-29T00:00:00+00:00",
                "current_period_start_epoch": 0,
                "current_period_end_epoch": 0,
                "quantity": 1,
                "cancel_at_period_end": False,
                "schedule_id": None,
            },
        )()
    )
    service = BillingReconciliationService(
        store=store,
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test", price_ids={"growth": "price_growth"}),
        stripe_client=stripe_client,
        plan_catalog_provider=_billing_service(store),
    )

    result = service.reconcile_account(account_id=account["id"])
    updated = store.get_subscription(account["id"])

    assert result["source"] == "stripe_subscription"
    assert result["current_plan_code"] == "growth"
    assert updated is not None
    assert updated.plan_code == "growth"
    assert updated.billing_status == "active"
    assert updated.pending_plan_code is None
    assert updated.pending_checkout_session_id is None
    assert stripe_client.retrieve_calls == ["sub_test_123"]


def test_billing_reconciliation_lists_customer_subscriptions_when_subscription_id_missing():
    store = InMemoryControlPlaneStore()
    control_plane = ControlPlaneService(store=store)
    account = control_plane.create_account({"name": "Reconcile Org", "ein": "123456789"})
    store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="free",
            status="active",
            stripe_customer_id="cus_test_123",
            billing_status="checkout_pending",
            pending_plan_code="growth",
            updated_at="2026-03-29T00:00:00+00:00",
        )
    )
    snapshot = type(
        "Snapshot",
        (),
        {
            "subscription_id": "sub_test_123",
            "customer_id": "cus_test_123",
            "item_id": "si_test_123",
            "price_id": "price_growth",
            "status": "active",
            "current_period_start": "2026-03-29T00:00:00+00:00",
            "current_period_end": "2026-04-29T00:00:00+00:00",
            "current_period_start_epoch": 0,
            "current_period_end_epoch": 10,
            "quantity": 1,
            "cancel_at_period_end": False,
            "schedule_id": None,
        },
    )()
    service = BillingReconciliationService(
        store=store,
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test", price_ids={"growth": "price_growth"}),
        stripe_client=_StripeLookupClient(snapshots=[snapshot]),
        plan_catalog_provider=_billing_service(store),
    )

    result = service.reconcile_account(account_id=account["id"])

    assert result["source"] == "stripe_customer"
    assert store.get_subscription(account["id"]).stripe_subscription_id == "sub_test_123"


def test_billing_reconciliation_requires_persisted_stripe_identity():
    store = InMemoryControlPlaneStore()
    control_plane = ControlPlaneService(store=store)
    account = control_plane.create_account({"name": "Reconcile Org", "ein": "123456789"})
    store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="free",
            status="active",
            updated_at="2026-03-29T00:00:00+00:00",
        )
    )
    service = BillingReconciliationService(
        store=store,
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test", price_ids={"growth": "price_growth"}),
        stripe_client=_StripeLookupClient(),
        plan_catalog_provider=_billing_service(store),
    )

    try:
        service.reconcile_account(account_id=account["id"])
    except BillingConflictError as exc:
        assert "Stripe customer or subscription id" in str(exc)
    else:
        assert False, "Expected reconciliation identity error"

