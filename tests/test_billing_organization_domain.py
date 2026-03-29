from __future__ import annotations

import pytest

from charity_status.billing import (
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
from charity_status.control_plane import ControlPlaneService, DynamoControlPlaneStore, FakeDynamoResource, FakeDynamoTable, InMemoryControlPlaneStore


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
