from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Protocol

from verification.backend.shared.billing.checkout import BillingConflictError, BillingEligibilityError, BillingNotEnabledError, StripeCheckoutConfig, _clean_text
from verification.backend.shared.billing.plan_changes import HttpStripePlanChangeClient, StripeSubscriptionSnapshot
from verification.backend.shared.billing.service import EntitlementService
from verification.backend.shared.billing.trials import TrialLifecycleService

logger = logging.getLogger(__name__)


class BillingReconciliationError(BillingConflictError):
    code = "billing_reconciliation_error"


class BillingReconciliationStripeClient(Protocol):
    def retrieve_subscription(self, *, subscription_id: str) -> StripeSubscriptionSnapshot:
        ...

    def list_customer_subscriptions(self, *, customer_id: str) -> list[StripeSubscriptionSnapshot]:
        ...


class BillingReconciliationStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...

    def put_subscription(self, subscription: Any) -> None:
        ...


class BillingReconciliationService:
    def __init__(
        self,
        *,
        store: BillingReconciliationStore,
        config: StripeCheckoutConfig,
        stripe_client: BillingReconciliationStripeClient | None = None,
        plan_catalog_provider: Any | None = None,
        trial_lifecycle_service: TrialLifecycleService | None = None,
    ) -> None:
        self._store = store
        self._config = config
        self._stripe_client = stripe_client or HttpStripeSubscriptionLookupClient(secret_key=config.secret_key or "")
        self._plan_catalog_provider = plan_catalog_provider
        self._entitlement_service = EntitlementService()
        self._trial_lifecycle_service = trial_lifecycle_service

    def reconcile_account(self, *, account_id: str) -> dict[str, Any]:
        if not self._config.enabled:
            raise BillingNotEnabledError("Billing reconciliation is not enabled")
        account = self._store.get_account(account_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            raise BillingEligibilityError("Organization is not eligible for billing reconciliation")
        subscription = self._store.get_subscription(account_id)
        if subscription is None:
            raise BillingReconciliationError("Organization does not have local billing state to reconcile")

        stripe_subscription_id = _clean_text(getattr(subscription, "stripe_subscription_id", None))
        stripe_customer_id = _clean_text(getattr(subscription, "stripe_customer_id", None))
        if stripe_subscription_id:
            snapshot = self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription_id)
            source = "stripe_subscription"
        elif stripe_customer_id:
            snapshot = self._select_subscription_snapshot(
                self._stripe_client.list_customer_subscriptions(customer_id=stripe_customer_id)
            )
            source = "stripe_customer"
        else:
            raise BillingReconciliationError("Organization does not have a persisted Stripe customer or subscription id")

        updated = self._apply_snapshot(subscription=subscription, snapshot=snapshot)
        self._store.put_subscription(updated)
        if self._trial_lifecycle_service is not None:
            updated = self._trial_lifecycle_service.mark_paid_conversion(account_id=updated.account_id) or updated
            self._store.put_subscription(updated)
        logger.info(
            "billing_reconciliation_completed",
            extra={
                "account_id": account_id,
                "source": source,
                "stripe_customer_id": updated.stripe_customer_id,
                "stripe_subscription_id": updated.stripe_subscription_id,
                "billing_status": updated.billing_status,
                "plan_code": updated.plan_code,
            },
        )
        return {
            "account_id": account_id,
            "source": source,
            "current_plan_code": updated.plan_code,
            "pending_plan_code": updated.pending_plan_code,
            "billing_status": updated.billing_status,
            "billing_period_start": updated.billing_period_start,
            "billing_period_end": updated.billing_period_end,
            "cancel_at_period_end": updated.cancel_at_period_end,
            "stripe_customer_id": updated.stripe_customer_id,
            "stripe_subscription_id": updated.stripe_subscription_id,
            "reconciled_at": updated.updated_at,
        }

    def _apply_snapshot(self, *, subscription: Any, snapshot: StripeSubscriptionSnapshot):
        plan_code = self._plan_code_for_snapshot(snapshot) or self._entitlement_service.normalize_plan_code(
            getattr(subscription, "pending_plan_code", None) or getattr(subscription, "plan_code", "free")
        )
        pending_plan_code = getattr(subscription, "pending_plan_code", None)
        pending_effective_at = getattr(subscription, "pending_plan_effective_at", None)
        if snapshot.cancel_at_period_end:
            pending_plan_code = "free"
            pending_effective_at = snapshot.current_period_end or pending_effective_at
        elif pending_plan_code and self._entitlement_service.normalize_plan_code(pending_plan_code) == plan_code:
            pending_plan_code = None
            pending_effective_at = None
        return replace(
            subscription,
            plan_code=plan_code,
            status="active" if snapshot.status not in {"canceled", "incomplete_expired"} else "canceled",
            effective_from=snapshot.current_period_start or getattr(subscription, "effective_from", None) or _utcnow(),
            effective_to=(snapshot.current_period_end if snapshot.status in {"canceled", "incomplete_expired"} else None),
            stripe_customer_id=snapshot.customer_id or getattr(subscription, "stripe_customer_id", None),
            stripe_subscription_id=snapshot.subscription_id,
            billing_status=snapshot.status,
            billing_period_start=snapshot.current_period_start or getattr(subscription, "billing_period_start", None),
            billing_period_end=snapshot.current_period_end or getattr(subscription, "billing_period_end", None),
            cancel_at_period_end=snapshot.cancel_at_period_end,
            stripe_subscription_schedule_id=snapshot.schedule_id,
            pending_plan_code=pending_plan_code,
            pending_plan_effective_at=pending_effective_at,
            pending_checkout_session_id=None,
            pending_checkout_session_url=None,
            pending_checkout_expires_at=None,
            updated_at=_utcnow(),
        )

    def _plan_code_for_snapshot(self, snapshot: StripeSubscriptionSnapshot) -> str | None:
        if self._plan_catalog_provider is not None:
            try:
                mapping = self._plan_catalog_provider.get_mapping_for_price_id(snapshot.price_id)
            except Exception:  # noqa: BLE001
                return None
            return _clean_text(getattr(mapping, "internal_plan_id", None))
        return None

    def _select_subscription_snapshot(self, snapshots: list[StripeSubscriptionSnapshot]) -> StripeSubscriptionSnapshot:
        if not snapshots:
            raise BillingReconciliationError("Stripe did not return any subscriptions for the organization billing customer")
        ranked = sorted(
            snapshots,
            key=lambda item: (
                item.status in {"active", "trialing"},
                item.current_period_end_epoch or 0,
            ),
            reverse=True,
        )
        return ranked[0]


class HttpStripeSubscriptionLookupClient(HttpStripePlanChangeClient):
    def list_customer_subscriptions(self, *, customer_id: str) -> list[StripeSubscriptionSnapshot]:
        response = self._request_json(
            "GET",
            f"/subscriptions?customer={customer_id}&status=all&limit=10",
            operation_name="customer subscription listing",
        )
        items = response.get("data") if isinstance(response, dict) else None
        if not isinstance(items, list):
            return []
        snapshots: list[StripeSubscriptionSnapshot] = []
        for item in items:
            if isinstance(item, dict):
                try:
                    snapshots.append(self._snapshot_from_payload(item))
                except Exception:  # noqa: BLE001
                    continue
        return snapshots

    def retrieve_subscription(self, *, subscription_id: str) -> StripeSubscriptionSnapshot:
        return self._snapshot_from_payload(
            self._request_json("GET", f"/subscriptions/{subscription_id}", operation_name="subscription retrieval")
        )

    @staticmethod
    def _snapshot_from_payload(payload: dict[str, Any]) -> StripeSubscriptionSnapshot:
        from verification.backend.shared.billing.plan_changes import _subscription_snapshot_from_response

        return _subscription_snapshot_from_response(payload)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

