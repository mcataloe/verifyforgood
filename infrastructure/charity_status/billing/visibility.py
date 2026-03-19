from __future__ import annotations

from typing import Protocol

from charity_status.billing.service import EntitlementService
from charity_status.billing.trials import TrialLifecycleService


_PLAN_SEQUENCE: tuple[str, ...] = ("free", "starter", "growth", "pro", "enterprise")


class ControlPlaneBillingVisibilityStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...


class BillingVisibilityService:
    def __init__(
        self,
        *,
        store: ControlPlaneBillingVisibilityStore,
        entitlement_service: EntitlementService | None = None,
        trial_lifecycle_service: TrialLifecycleService | None = None,
    ) -> None:
        self._store = store
        self._entitlement_service = entitlement_service or EntitlementService()
        self._trial_lifecycle_service = trial_lifecycle_service

    def get_subscription_summary(self, *, account_id: str) -> dict[str, object | None]:
        account = self._store.get_account(account_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            from charity_status.billing.checkout import BillingEligibilityError

            raise BillingEligibilityError("Organization is not eligible for billing visibility")
        subscription = self._refresh_subscription(account_id)
        if subscription is None:
            plan_code = "free"
            effective_access_plan = "free"
            billing_status = "not_enrolled"
            renewal_date = None
            pending_downgrade = None
            trial = None
        else:
            plan_code = self._entitlement_service.normalize_plan_code(getattr(subscription, "plan_code", "free"))
            resolved = self._entitlement_service.resolve(
                account_id=account_id,
                fallback_plan_code=plan_code,
                subscription=subscription.to_subscription(),
            )
            effective_access_plan = resolved.entitlements.plan_code
            billing_status = str(getattr(subscription, "billing_status", None) or getattr(subscription, "status", "active") or "active")
            renewal_date = getattr(subscription, "billing_period_end", None)
            pending_downgrade = _pending_downgrade_payload(subscription, current_plan_code=plan_code, normalize=self._entitlement_service.normalize_plan_code)
            trial = self._trial_lifecycle_service.trial_summary(subscription) if self._trial_lifecycle_service is not None else None
        return {
            "plan": plan_code,
            "effective_access_plan": effective_access_plan,
            "billing_status": billing_status,
            "renewal_date": renewal_date,
            "pending_downgrade": pending_downgrade,
            "trial": trial,
        }

    def _refresh_subscription(self, account_id: str):
        if self._trial_lifecycle_service is None:
            return self._store.get_subscription(account_id)
        refreshed = self._trial_lifecycle_service.refresh_subscription(account_id=account_id)
        if refreshed is not None:
            return refreshed
        return self._store.get_subscription(account_id)


def _pending_downgrade_payload(subscription: object, *, current_plan_code: str, normalize) -> dict[str, str | None] | None:
    pending_plan_code = normalize(getattr(subscription, "pending_plan_code", None))
    effective_at = getattr(subscription, "pending_plan_effective_at", None)
    if not effective_at or pending_plan_code == current_plan_code:
        return None
    if _plan_rank(pending_plan_code) >= _plan_rank(current_plan_code):
        return None
    return {
        "plan": pending_plan_code,
        "effective_at": effective_at,
    }


def _plan_rank(plan_code: str) -> int:
    try:
        return _PLAN_SEQUENCE.index(plan_code)
    except ValueError:
        return 0
