from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .identity_models import PlanRecord, SubscriptionRecord, SubscriptionStatus
from .identity_repositories import OrganizationRepository, PlanRepository, SubscriptionRepository


class SubscriptionScaffoldingError(ValueError):
    status_code = 400


DEFAULT_PORTAL_PLANS: tuple[PlanRecord, ...] = (
    PlanRecord(
        plan_id="starter",
        plan_name="Starter",
        monthly_price=4900,
        feature_flags=("verification", "risk_flags"),
        request_limit=1000,
        description="Entry-level plan for early portal teams.",
    ),
    PlanRecord(
        plan_id="growth",
        plan_name="Growth",
        monthly_price=14900,
        feature_flags=("verification", "risk_flags", "financial_trends", "benchmarking"),
        request_limit=10000,
        description="Expanded feature access for growing organizations.",
    ),
    PlanRecord(
        plan_id="enterprise",
        plan_name="Enterprise",
        monthly_price=49900,
        feature_flags=("verification", "risk_flags", "financial_trends", "benchmarking", "state_registry", "monitoring"),
        request_limit=250000,
        description="High-capacity access designed for complex enterprise teams.",
    ),
)


@dataclass(frozen=True)
class SubscriptionResolvedResponse:
    subscription: SubscriptionRecord
    plan: PlanRecord

    def to_dict(self) -> dict[str, object]:
        return {
            "subscription": {
                "subscription_id": self.subscription.subscription_id,
                "organization_id": self.subscription.organization_id,
                "plan_id": self.subscription.plan_id,
                "status": self.subscription.status.value,
                "billing_cycle_start": self.subscription.billing_cycle_start,
                "billing_cycle_end": self.subscription.billing_cycle_end,
                "created_at": self.subscription.created_at,
            },
            "plan": {
                "plan_id": self.plan.plan_id,
                "plan_name": self.plan.plan_name,
                "monthly_price": self.plan.monthly_price,
                "feature_flags": list(self.plan.feature_flags),
                "request_limit": self.plan.request_limit,
                "description": self.plan.description,
            },
        }


class SubscriptionService:
    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        plans: PlanRepository,
        subscriptions: SubscriptionRepository,
    ) -> None:
        self._organizations = organizations
        self._plans = plans
        self._subscriptions = subscriptions

    def list_plans(self) -> list[PlanRecord]:
        self._ensure_seeded_plans()
        return self._plans.list_all()

    def get_plan(self, plan_id: str) -> PlanRecord:
        self._ensure_seeded_plans()
        plan = self._plans.get(_normalize_plan_id(plan_id))
        if plan is None:
            raise SubscriptionScaffoldingError("plan_id must reference a known portal subscription plan")
        return plan

    def upsert_subscription(
        self,
        *,
        organization_id: str,
        plan_id: str,
        status: str = SubscriptionStatus.ACTIVE.value,
        billing_cycle_start: str | None = None,
        billing_cycle_end: str | None = None,
    ) -> SubscriptionResolvedResponse:
        self._ensure_seeded_plans()
        if self._organizations.get(organization_id) is None:
            raise SubscriptionScaffoldingError("organization_id must reference an existing organization")

        plan = self.get_plan(plan_id)
        normalized_status = _validate_status(status)
        existing = self._subscriptions.get_by_organization(organization_id)
        created_at = existing.created_at if existing is not None else _utc_now()
        persisted = self._subscriptions.put(
            SubscriptionRecord(
                subscription_id=existing.subscription_id if existing is not None else f"sub_{secrets.token_hex(16)}",
                organization_id=organization_id,
                plan_id=plan.plan_id,
                status=normalized_status,
                billing_cycle_start=billing_cycle_start or (existing.billing_cycle_start if existing is not None else created_at),
                billing_cycle_end=billing_cycle_end or (existing.billing_cycle_end if existing is not None else _default_billing_cycle_end(created_at)),
                created_at=created_at,
            )
        )
        return SubscriptionResolvedResponse(subscription=persisted, plan=plan)

    def get_subscription_for_organization(self, organization_id: str) -> SubscriptionResolvedResponse:
        self._ensure_seeded_plans()
        if self._organizations.get(organization_id) is None:
            raise SubscriptionScaffoldingError("organization_id must reference an existing organization")
        subscription = self._subscriptions.get_by_organization(organization_id)
        if subscription is None:
            raise SubscriptionScaffoldingError("Subscription was not found for this organization")
        plan = self.get_plan(subscription.plan_id)
        return SubscriptionResolvedResponse(subscription=subscription, plan=plan)

    def _ensure_seeded_plans(self) -> None:
        if self._plans.list_all():
            return
        self._plans.seed_defaults(list(DEFAULT_PORTAL_PLANS))


def _normalize_plan_id(plan_id: str) -> str:
    return str(plan_id or "").strip().lower()


def _validate_status(status: str) -> SubscriptionStatus:
    try:
        return SubscriptionStatus(str(status or "").strip().lower())
    except Exception as exc:  # noqa: BLE001
        raise SubscriptionScaffoldingError("status must be one of: active, past_due, canceled") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _default_billing_cycle_end(start: str) -> str:
    started_at = datetime.fromisoformat(start)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return (started_at + timedelta(days=30)).replace(microsecond=0).isoformat()
