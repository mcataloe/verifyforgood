from __future__ import annotations

import pytest

from verification.billing import (
    BillingCustomerBootstrapService,
    BillingEvent,
    BillingMappingError,
    BillingService,
    BillingSubscription,
    ConfiguredStripeBillingProvider,
    ControlPlaneBillingCustomerRepository,
    ControlPlaneBillingEventRepository,
    ControlPlaneBillingSubscriptionRepository,
    PlanCatalogMapping,
)
from verification.billing.checkout import BillingProviderError, StripeCheckoutConfig
from verification.control_plane import ControlPlaneService, DynamoControlPlaneStore, FakeDynamoResource, FakeDynamoTable, InMemoryControlPlaneStore


def _provider() -> ConfiguredStripeBillingProvider:
    return ConfiguredStripeBillingProvider(
        [
            PlanCatalogMapping(internal_plan_id="growth", stripe_price_id="price_growth", stripe_product_id="prod_growth"),
            PlanCatalogMapping(internal_plan_id="pro", stripe_price_id="price_pro", stripe_product_id="prod_pro"),
        ]
    )


def _service_with_store(store) -> BillingService:
    return BillingService(
        customers=ControlPlaneBillingCustomerRepository(store),
        subscriptions=ControlPlaneBillingSubscriptionRepository(store),
        events=ControlPlaneBillingEventRepository(store),
        provider=_provider(),
    )


class _StripeBootstrapProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_customer(
        self,
        *,
        account_id: str,
        account_name: str,
        ein: str | None,
        metadata: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "ein": ein,
                "metadata": metadata,
                "idempotency_key": idempotency_key,
            }
        )
        return "cus_bootstrap_123"


def test_billing_service_persists_organization_billing_customer():
    service = _service_with_store(InMemoryControlPlaneStore())

    created = service.create_or_update_customer(
        organization_id="org_1",
        stripe_customer_id="cus_test_123",
        updated_at="2026-03-29T00:00:00+00:00",
    )
    loaded = service.get_customer("org_1")

    assert created.organization_id == "org_1"
    assert created.account_id == "org_1"
    assert created.stripe_customer_id == "cus_test_123"
    assert loaded == created


def test_billing_service_resolves_internal_and_stripe_plan_mappings():
    service = _service_with_store(InMemoryControlPlaneStore())

    by_plan = service.get_mapping_for_plan("growth")
    by_price = service.get_mapping_for_price_id("price_pro")

    assert by_plan.stripe_price_id == "price_growth"
    assert by_plan.stripe_product_id == "prod_growth"
    assert by_price.internal_plan_id == "pro"


def test_configured_stripe_billing_provider_rejects_unknown_or_invalid_mappings():
    with pytest.raises(BillingMappingError, match="Unknown internal plan id"):
        ConfiguredStripeBillingProvider(
            [PlanCatalogMapping(internal_plan_id="unknown", stripe_price_id="price_unknown")]
        )

    with pytest.raises(BillingMappingError, match="stripe_price_id is required"):
        ConfiguredStripeBillingProvider(
            [PlanCatalogMapping(internal_plan_id="growth", stripe_price_id="")]
        )

    service = _service_with_store(InMemoryControlPlaneStore())
    with pytest.raises(BillingMappingError, match="Unknown Stripe price id"):
        service.get_mapping_for_price_id("price_missing")


def test_billing_subscription_upsert_preserves_created_at_and_updates_current_state():
    service = _service_with_store(InMemoryControlPlaneStore())

    first = service.upsert_subscription(
        BillingSubscription(
            organization_id="org_1",
            internal_plan_id="growth",
            billing_status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            current_period_start="2026-03-01T00:00:00+00:00",
            current_period_end="2026-04-01T00:00:00+00:00",
            cancel_at_period_end=False,
            created_at="2026-03-01T00:00:00+00:00",
            updated_at="2026-03-01T00:00:00+00:00",
        )
    )
    updated = service.upsert_subscription(
        BillingSubscription(
            organization_id="org_1",
            internal_plan_id="pro",
            billing_status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            current_period_start="2026-04-01T00:00:00+00:00",
            current_period_end="2026-05-01T00:00:00+00:00",
            cancel_at_period_end=True,
            created_at="2026-04-01T00:00:00+00:00",
            updated_at="2026-04-01T00:00:00+00:00",
        )
    )

    assert first.internal_plan_id == "growth"
    assert updated.internal_plan_id == "pro"
    assert updated.created_at == "2026-03-01T00:00:00+00:00"
    assert updated.current_period_end == "2026-05-01T00:00:00+00:00"
    assert updated.cancel_at_period_end is True


def test_control_plane_billing_domain_repositories_round_trip_through_dynamo_store():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    control_plane = ControlPlaneService(store=store)
    account = control_plane.create_account({"name": "Billing Domain", "ein": "123456789"})
    account_id = account["id"]
    service = _service_with_store(store)

    customer = service.create_or_update_customer(
        organization_id=account_id,
        stripe_customer_id="cus_test_123",
        updated_at="2026-03-29T00:00:00+00:00",
    )
    subscription = service.upsert_subscription(
        BillingSubscription(
            organization_id=account_id,
            internal_plan_id="growth",
            billing_status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            current_period_start="2026-03-29T00:00:00+00:00",
            current_period_end="2026-04-29T00:00:00+00:00",
            cancel_at_period_end=False,
            created_at="2026-03-29T00:00:00+00:00",
            updated_at="2026-03-29T00:00:00+00:00",
        )
    )
    event = service.record_event(
        BillingEvent(
            event_id="evt_test_123",
            event_type="customer.subscription.updated",
            organization_id=account_id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            created_at="2026-03-29T00:00:00+00:00",
            updated_at="2026-03-29T00:00:00+00:00",
        )
    )
    reloaded_service = _service_with_store(DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))
    reloaded_events = ControlPlaneBillingEventRepository(DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))

    assert customer.organization_id == account_id
    assert reloaded_service.get_customer(account_id) == customer
    assert reloaded_service.get_subscription(account_id) == subscription
    assert reloaded_service.get_mapping_for_price_id("price_growth").internal_plan_id == "growth"
    assert reloaded_events.get(event.event_id) == event


def test_billing_customer_bootstrap_creates_and_persists_first_time_customer():
    store = InMemoryControlPlaneStore()
    account = ControlPlaneService(store=store).create_account({"name": "Bootstrap Org", "ein": "123456789"})
    provider = _StripeBootstrapProvider()
    service = BillingCustomerBootstrapService(
        store=store,
        billing_service=_service_with_store(store),
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test", price_ids={"growth": "price_growth"}),
        stripe_provider=provider,
    )

    result = service.bootstrap_customer(
        organization_id=account["id"],
        created_by_user_id="user_admin",
    )

    persisted = _service_with_store(store).get_customer(account["id"])
    assert result.organization_id == account["id"]
    assert result.stripe_customer_id == "cus_bootstrap_123"
    assert result.reused is False
    assert persisted is not None
    assert persisted.stripe_customer_id == "cus_bootstrap_123"
    assert provider.calls[0]["metadata"] == {
        "organization_id": account["id"],
        "organization_name": "Bootstrap Org",
        "created_by_user_id": "user_admin",
    }
    assert provider.calls[0]["idempotency_key"] == f"billing-customer-bootstrap:{account['id']}"


def test_billing_customer_bootstrap_reuses_existing_customer_without_provider_call():
    store = InMemoryControlPlaneStore()
    account = ControlPlaneService(store=store).create_account({"name": "Bootstrap Org", "ein": "123456789"})
    billing_service = _service_with_store(store)
    billing_service.create_or_update_customer(
        organization_id=account["id"],
        stripe_customer_id="cus_existing_123",
        updated_at="2026-03-29T00:00:00+00:00",
    )
    provider = _StripeBootstrapProvider()
    service = BillingCustomerBootstrapService(
        store=store,
        billing_service=billing_service,
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test", price_ids={"growth": "price_growth"}),
        stripe_provider=provider,
    )

    result = service.bootstrap_customer(
        organization_id=account["id"],
        created_by_user_id="user_admin",
    )

    assert result.stripe_customer_id == "cus_existing_123"
    assert result.reused is True
    assert provider.calls == []


def test_billing_customer_bootstrap_provider_failure_does_not_corrupt_local_state():
    class _FailingStripeBootstrapProvider:
        def create_customer(self, **kwargs) -> str:
            raise BillingProviderError("Stripe rejected bootstrap")

    store = InMemoryControlPlaneStore()
    account = ControlPlaneService(store=store).create_account({"name": "Bootstrap Org", "ein": "123456789"})
    service = BillingCustomerBootstrapService(
        store=store,
        billing_service=_service_with_store(store),
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test", price_ids={"growth": "price_growth"}),
        stripe_provider=_FailingStripeBootstrapProvider(),
    )

    with pytest.raises(BillingProviderError, match="Stripe rejected bootstrap"):
        service.bootstrap_customer(
            organization_id=account["id"],
            created_by_user_id="user_admin",
        )

    assert _service_with_store(store).get_customer(account["id"]) is None

