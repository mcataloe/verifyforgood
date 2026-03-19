from __future__ import annotations

from typing import Protocol

from charity_status.billing.service import EntitlementService


_PLAN_SEQUENCE: tuple[str, ...] = ("free", "starter", "growth", "pro", "enterprise")


class ControlPlaneBillingVisibilityStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...


class BillingVisibilityService:
    def __init__(self, *, store: ControlPlaneBillingVisibilityStore) -> None:
        self._store = store
        self._entitlement_service = EntitlementService()

    def get_subscription_summary(self, *, account_id: str) -> dict[str, object | None]:
        account = self._store.get_account(account_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            from charity_status.billing.checkout import BillingEligibilityError

            raise BillingEligibilityError("Organization is not eligible for billing visibility")
        subscription = self._store.get_subscription(account_id)
        if subscription is None:
            plan_code = "free"
            billing_status = "not_enrolled"
            renewal_date = None
            pending_downgrade = None
        else:
            plan_code = self._entitlement_service.normalize_plan_code(getattr(subscription, "plan_code", "free"))
            billing_status = str(getattr(subscription, "billing_status", None) or getattr(subscription, "status", "active") or "active")
            renewal_date = getattr(subscription, "billing_period_end", None)
            pending_downgrade = _pending_downgrade_payload(subscription, current_plan_code=plan_code, normalize=self._entitlement_service.normalize_plan_code)
        return {
            "plan": plan_code,
            "billing_status": billing_status,
            "renewal_date": renewal_date,
            "pending_downgrade": pending_downgrade,
        }


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
