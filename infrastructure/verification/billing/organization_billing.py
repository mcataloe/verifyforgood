from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import logging
from typing import Any, Protocol

from verification.billing.checkout import BillingEligibilityError, BillingNotEnabledError, BillingProviderError, StripeCheckoutConfig
from verification.billing.service import PLAN_CODES
from verification.control_plane.models import ManagedBillingCustomer, ManagedBillingEvent, ManagedSubscription
from verification.control_plane.service import ControlPlaneStore

logger = logging.getLogger(__name__)


BILLING_CUSTOMER_ENTITY = "BILLING_CUSTOMER"
BILLING_SUBSCRIPTION_ENTITY = "BILLING_SUBSCRIPTION"
BILLING_EVENT_ENTITY = "BILLING_EVENT"
PLAN_CATALOG_MAPPING_ENTITY = "PLAN_CATALOG_MAPPING"


class BillingMappingError(ValueError):
    pass


@dataclass(frozen=True)
class BillingCustomer:
    organization_id: str
    stripe_customer_id: str
    created_at: str
    updated_at: str
    account_id: str | None = None


@dataclass(frozen=True)
class BillingSubscription:
    organization_id: str
    internal_plan_id: str
    billing_status: str
    created_at: str
    updated_at: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False
    account_id: str | None = None


@dataclass(frozen=True)
class BillingEvent:
    event_id: str
    event_type: str
    organization_id: str
    created_at: str
    updated_at: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    internal_plan_id: str | None = None
    account_id: str | None = None


@dataclass(frozen=True)
class PlanCatalogMapping:
    internal_plan_id: str
    stripe_price_id: str
    stripe_product_id: str | None = None


class BillingCustomerRepository(Protocol):
    def get_by_organization_id(self, organization_id: str) -> BillingCustomer | None:
        ...

    def get_by_stripe_customer_id(self, stripe_customer_id: str) -> BillingCustomer | None:
        ...

    def upsert(self, customer: BillingCustomer) -> BillingCustomer:
        ...


class BillingSubscriptionRepository(Protocol):
    def get_by_organization_id(self, organization_id: str) -> BillingSubscription | None:
        ...

    def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> BillingSubscription | None:
        ...

    def upsert(self, subscription: BillingSubscription) -> BillingSubscription:
        ...


class BillingEventRepository(Protocol):
    def get(self, event_id: str) -> BillingEvent | None:
        ...

    def upsert(self, event: BillingEvent) -> BillingEvent:
        ...


class StripeBillingProvider(Protocol):
    def get_mapping_for_plan(self, internal_plan_id: str) -> PlanCatalogMapping:
        ...

    def get_mapping_for_price_id(self, stripe_price_id: str) -> PlanCatalogMapping:
        ...


class StripeCustomerBootstrapProvider(Protocol):
    def create_customer(
        self,
        *,
        account_id: str,
        account_name: str,
        ein: str | None,
        metadata: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        ...


@dataclass(frozen=True)
class BillingCustomerBootstrapResult:
    organization_id: str
    stripe_customer_id: str
    created_at: str
    updated_at: str
    account_id: str
    reused: bool


class InMemoryBillingCustomerRepository:
    def __init__(self) -> None:
        self._by_org: dict[str, BillingCustomer] = {}

    def get_by_organization_id(self, organization_id: str) -> BillingCustomer | None:
        return self._by_org.get(organization_id)

    def get_by_stripe_customer_id(self, stripe_customer_id: str) -> BillingCustomer | None:
        for customer in self._by_org.values():
            if customer.stripe_customer_id == stripe_customer_id:
                return customer
        return None

    def upsert(self, customer: BillingCustomer) -> BillingCustomer:
        self._by_org[customer.organization_id] = customer
        return customer


class InMemoryBillingSubscriptionRepository:
    def __init__(self) -> None:
        self._by_org: dict[str, BillingSubscription] = {}

    def get_by_organization_id(self, organization_id: str) -> BillingSubscription | None:
        return self._by_org.get(organization_id)

    def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> BillingSubscription | None:
        for subscription in self._by_org.values():
            if subscription.stripe_subscription_id == stripe_subscription_id:
                return subscription
        return None

    def upsert(self, subscription: BillingSubscription) -> BillingSubscription:
        self._by_org[subscription.organization_id] = subscription
        return subscription


class InMemoryBillingEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, BillingEvent] = {}

    def get(self, event_id: str) -> BillingEvent | None:
        return self._events.get(event_id)

    def upsert(self, event: BillingEvent) -> BillingEvent:
        self._events[event.event_id] = event
        return event


class ConfiguredStripeBillingProvider:
    def __init__(self, mappings: list[PlanCatalogMapping]) -> None:
        self._by_plan: dict[str, PlanCatalogMapping] = {}
        self._by_price: dict[str, PlanCatalogMapping] = {}
        for mapping in mappings:
            normalized_plan = str(mapping.internal_plan_id or "").strip().lower()
            price_id = str(mapping.stripe_price_id or "").strip()
            if normalized_plan not in PLAN_CODES:
                raise BillingMappingError(f"Unknown internal plan id: {mapping.internal_plan_id}")
            if not price_id:
                raise BillingMappingError(f"stripe_price_id is required for plan: {mapping.internal_plan_id}")
            normalized_mapping = PlanCatalogMapping(
                internal_plan_id=normalized_plan,
                stripe_price_id=price_id,
                stripe_product_id=str(mapping.stripe_product_id or "").strip() or None,
            )
            self._by_plan[normalized_plan] = normalized_mapping
            self._by_price[price_id] = normalized_mapping

    def get_mapping_for_plan(self, internal_plan_id: str) -> PlanCatalogMapping:
        normalized_plan = str(internal_plan_id or "").strip().lower()
        mapping = self._by_plan.get(normalized_plan)
        if mapping is None:
            raise BillingMappingError(f"No Stripe price mapping configured for internal plan: {internal_plan_id}")
        return mapping

    def get_mapping_for_price_id(self, stripe_price_id: str) -> PlanCatalogMapping:
        normalized_price = str(stripe_price_id or "").strip()
        mapping = self._by_price.get(normalized_price)
        if mapping is None:
            raise BillingMappingError(f"Unknown Stripe price id: {stripe_price_id}")
        return mapping


class ControlPlaneBillingCustomerRepository:
    def __init__(self, store: ControlPlaneStore) -> None:
        self._store = store

    def get_by_organization_id(self, organization_id: str) -> BillingCustomer | None:
        customer = self._store.get_billing_customer(organization_id)
        return None if customer is None else _billing_customer_from_managed(customer)

    def get_by_stripe_customer_id(self, stripe_customer_id: str) -> BillingCustomer | None:
        customer = self._store.get_billing_customer_by_stripe_customer_id(stripe_customer_id)
        return None if customer is None else _billing_customer_from_managed(customer)

    def upsert(self, customer: BillingCustomer) -> BillingCustomer:
        self._store.put_billing_customer(_managed_billing_customer(customer))
        return customer


class ControlPlaneBillingSubscriptionRepository:
    def __init__(self, store: ControlPlaneStore) -> None:
        self._store = store

    def get_by_organization_id(self, organization_id: str) -> BillingSubscription | None:
        subscription = self._store.get_subscription(organization_id)
        return None if subscription is None else _billing_subscription_from_managed(subscription)

    def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> BillingSubscription | None:
        subscription = self._store.get_subscription_by_stripe_subscription_id(stripe_subscription_id)
        return None if subscription is None else _billing_subscription_from_managed(subscription)

    def upsert(self, subscription: BillingSubscription) -> BillingSubscription:
        current = self._store.get_subscription(subscription.organization_id)
        self._store.put_subscription(_managed_subscription(subscription, current=current))
        return self.get_by_organization_id(subscription.organization_id) or subscription


class ControlPlaneBillingEventRepository:
    def __init__(self, store: ControlPlaneStore) -> None:
        self._store = store

    def get(self, event_id: str) -> BillingEvent | None:
        event = self._store.get_billing_event(event_id)
        return None if event is None else _billing_event_from_managed(event)

    def upsert(self, event: BillingEvent) -> BillingEvent:
        self._store.put_billing_event(_managed_billing_event(event))
        return event


class BillingService:
    def __init__(
        self,
        *,
        customers: BillingCustomerRepository,
        subscriptions: BillingSubscriptionRepository,
        events: BillingEventRepository,
        provider: StripeBillingProvider,
    ) -> None:
        self._customers = customers
        self._subscriptions = subscriptions
        self._events = events
        self._provider = provider

    def create_or_update_customer(self, *, organization_id: str, stripe_customer_id: str, updated_at: str | None = None) -> BillingCustomer:
        timestamp = updated_at or _utcnow()
        current = self._customers.get_by_organization_id(organization_id)
        customer = BillingCustomer(
            organization_id=organization_id,
            stripe_customer_id=stripe_customer_id,
            created_at=current.created_at if current is not None else timestamp,
            updated_at=timestamp,
            account_id=current.account_id if current is not None else organization_id,
        )
        return self._customers.upsert(customer)

    def get_customer(self, organization_id: str) -> BillingCustomer | None:
        return self._customers.get_by_organization_id(organization_id)

    def upsert_subscription(self, subscription: BillingSubscription) -> BillingSubscription:
        current = self._subscriptions.get_by_organization_id(subscription.organization_id)
        normalized = replace(
            subscription,
            internal_plan_id=str(subscription.internal_plan_id or "").strip().lower(),
            created_at=current.created_at if current is not None else subscription.created_at,
            account_id=current.account_id if current is not None else (subscription.account_id or subscription.organization_id),
        )
        return self._subscriptions.upsert(normalized)

    def get_subscription(self, organization_id: str) -> BillingSubscription | None:
        return self._subscriptions.get_by_organization_id(organization_id)

    def record_event(self, event: BillingEvent) -> BillingEvent:
        current = self._events.get(event.event_id)
        normalized = replace(
            event,
            created_at=current.created_at if current is not None else event.created_at,
            account_id=current.account_id if current is not None else (event.account_id or event.organization_id),
        )
        return self._events.upsert(normalized)

    def get_mapping_for_plan(self, internal_plan_id: str) -> PlanCatalogMapping:
        return self._provider.get_mapping_for_plan(internal_plan_id)

    def get_mapping_for_price_id(self, stripe_price_id: str) -> PlanCatalogMapping:
        return self._provider.get_mapping_for_price_id(stripe_price_id)


class BillingCustomerBootstrapService:
    def __init__(
        self,
        *,
        store: ControlPlaneStore,
        billing_service: BillingService,
        config: StripeCheckoutConfig,
        stripe_provider: StripeCustomerBootstrapProvider,
    ) -> None:
        self._store = store
        self._billing_service = billing_service
        self._config = config
        self._stripe_provider = stripe_provider

    def bootstrap_customer(
        self,
        *,
        organization_id: str,
        created_by_user_id: str | None,
    ) -> BillingCustomerBootstrapResult:
        if not self._config.enabled:
            raise BillingNotEnabledError("Billing customer bootstrap is not enabled")
        account = self._store.get_account(organization_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            raise BillingEligibilityError("Organization is not eligible for billing customer bootstrap")

        existing = self._billing_service.get_customer(organization_id)
        if existing is not None:
            logger.info(
                "billing_customer_bootstrap_reused",
                extra={"organization_id": organization_id, "stripe_customer_id": existing.stripe_customer_id},
            )
            return BillingCustomerBootstrapResult(
                organization_id=existing.organization_id,
                stripe_customer_id=existing.stripe_customer_id,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
                account_id=str(existing.account_id or organization_id),
                reused=True,
            )

        metadata = {
            "organization_id": organization_id,
            "organization_name": str(getattr(account, "name", "") or organization_id),
        }
        if created_by_user_id:
            metadata["created_by_user_id"] = created_by_user_id

        stripe_customer_id = self._stripe_provider.create_customer(
            account_id=organization_id,
            account_name=str(getattr(account, "name", "") or organization_id),
            ein=getattr(account, "ein", None),
            metadata=metadata,
            idempotency_key=f"billing-customer-bootstrap:{organization_id}",
        )
        timestamp = _utcnow()
        persisted = self._billing_service.create_or_update_customer(
            organization_id=organization_id,
            stripe_customer_id=stripe_customer_id,
            updated_at=timestamp,
        )
        logger.info(
            "billing_customer_bootstrap_created",
            extra={"organization_id": organization_id, "stripe_customer_id": persisted.stripe_customer_id},
        )
        return BillingCustomerBootstrapResult(
            organization_id=persisted.organization_id,
            stripe_customer_id=persisted.stripe_customer_id,
            created_at=persisted.created_at,
            updated_at=persisted.updated_at,
            account_id=str(persisted.account_id or organization_id),
            reused=False,
        )


def _managed_billing_customer(customer: BillingCustomer) -> ManagedBillingCustomer:
    return ManagedBillingCustomer(
        account_id=customer.account_id or customer.organization_id,
        organization_id=customer.organization_id,
        stripe_customer_id=customer.stripe_customer_id,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


def _billing_customer_from_managed(customer: ManagedBillingCustomer) -> BillingCustomer:
    return BillingCustomer(
        organization_id=customer.organization_id,
        stripe_customer_id=customer.stripe_customer_id,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        account_id=customer.account_id,
    )


def _managed_subscription(subscription: BillingSubscription, *, current: ManagedSubscription | None) -> ManagedSubscription:
    existing = current or ManagedSubscription(
        account_id=subscription.account_id or subscription.organization_id,
        plan_code=subscription.internal_plan_id,
        status="active",
        created_at=subscription.created_at,
        effective_from=subscription.current_period_start,
        updated_at=subscription.updated_at,
    )
    return replace(
        existing,
        account_id=subscription.account_id or subscription.organization_id,
        plan_code=subscription.internal_plan_id,
        status=subscription.billing_status or existing.status,
        created_at=existing.created_at or subscription.created_at,
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        billing_status=subscription.billing_status,
        billing_period_start=subscription.current_period_start,
        billing_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        effective_from=subscription.current_period_start or existing.effective_from or subscription.created_at,
        effective_to=subscription.current_period_end if subscription.billing_status == "canceled" else existing.effective_to,
        updated_at=subscription.updated_at,
    )


def _billing_subscription_from_managed(subscription: ManagedSubscription) -> BillingSubscription:
    return BillingSubscription(
        organization_id=subscription.account_id,
        internal_plan_id=subscription.plan_code,
        billing_status=str(subscription.billing_status or subscription.status or "active"),
        created_at=str(subscription.created_at or subscription.effective_from or subscription.updated_at or ""),
        updated_at=str(subscription.updated_at or subscription.effective_from or ""),
        stripe_customer_id=subscription.stripe_customer_id,
        stripe_subscription_id=subscription.stripe_subscription_id,
        current_period_start=subscription.billing_period_start,
        current_period_end=subscription.billing_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        account_id=subscription.account_id,
    )


def _managed_billing_event(event: BillingEvent) -> ManagedBillingEvent:
    return ManagedBillingEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        processed_at=event.updated_at,
        account_id=event.account_id or event.organization_id,
        stripe_customer_id=event.stripe_customer_id,
        stripe_subscription_id=event.stripe_subscription_id,
    )


def _billing_event_from_managed(event: ManagedBillingEvent) -> BillingEvent:
    return BillingEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        organization_id=str(event.account_id or ""),
        created_at=event.processed_at,
        updated_at=event.processed_at,
        stripe_customer_id=event.stripe_customer_id,
        stripe_subscription_id=event.stripe_subscription_id,
        account_id=event.account_id,
    )


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

