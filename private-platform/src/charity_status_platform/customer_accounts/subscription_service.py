from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from .billing_calendar import month_cycle_window, next_month_boundary, proration_detail, prorated_delta_amount_cents, prorated_quota_delta
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
    current_charge_cents: int | None = None
    is_prorated: bool = False
    billable_days: int | None = None
    days_in_month: int | None = None
    next_renewal_at: str | None = None
    pending_plan_id: str | None = None
    pending_plan_effective_at: str | None = None
    cancel_at_period_end: bool = False
    quota_delta: int | None = None

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
                "pending_plan_id": self.subscription.pending_plan_id,
                "pending_plan_effective_at": self.subscription.pending_plan_effective_at,
                "cancel_at_period_end": self.subscription.cancel_at_period_end,
                "updated_at": self.subscription.updated_at,
                "grace_period_ends_at": self.subscription.grace_period_ends_at,
                "billing_status": self.subscription.billing_status,
            },
            "plan": {
                "plan_id": self.plan.plan_id,
                "plan_name": self.plan.plan_name,
                "monthly_price": self.plan.monthly_price,
                "feature_flags": list(self.plan.feature_flags),
                "request_limit": self.plan.request_limit,
                "description": self.plan.description,
            },
            "billing": {
                "current_charge_cents": self.current_charge_cents,
                "is_prorated": self.is_prorated,
                "billable_days": self.billable_days,
                "days_in_month": self.days_in_month,
                "next_renewal_at": self.next_renewal_at,
                "pending_plan_id": self.pending_plan_id,
                "pending_plan_effective_at": self.pending_plan_effective_at,
                "cancel_at_period_end": self.cancel_at_period_end,
                "quota_delta": self.quota_delta,
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
        return self.create_or_activate_subscription(
            organization_id=organization_id,
            plan_id=plan_id,
            status=status,
            billing_cycle_start=billing_cycle_start,
            billing_cycle_end=billing_cycle_end,
        )

    def create_or_activate_subscription(
        self,
        *,
        organization_id: str,
        plan_id: str,
        status: str = SubscriptionStatus.ACTIVE.value,
        billing_cycle_start: str | None = None,
        billing_cycle_end: str | None = None,
        effective_at: str | None = None,
    ) -> SubscriptionResolvedResponse:
        self._ensure_seeded_plans()
        if self._organizations.get(organization_id) is None:
            raise SubscriptionScaffoldingError("organization_id must reference an existing organization")

        plan = self.get_plan(plan_id)
        normalized_status = _validate_status(status)
        existing = self._subscriptions.get_by_organization(organization_id)
        created_at = existing.created_at if existing is not None else _utc_now()
        effective = _parse_or_now(effective_at or billing_cycle_start or created_at)
        cycle_start, cycle_end = (
            billing_cycle_start or _to_iso(effective),
            billing_cycle_end or month_cycle_window(effective)[1],
        )
        detail = proration_detail(plan.monthly_price, effective)
        persisted = self._subscriptions.put(
            SubscriptionRecord(
                subscription_id=existing.subscription_id if existing is not None else f"sub_{secrets.token_hex(16)}",
                organization_id=organization_id,
                plan_id=plan.plan_id,
                status=normalized_status,
                billing_cycle_start=(existing.billing_cycle_start if existing is not None and billing_cycle_start is None else cycle_start),
                billing_cycle_end=(existing.billing_cycle_end if existing is not None and billing_cycle_end is None else cycle_end),
                created_at=created_at,
                pending_plan_id=existing.pending_plan_id if existing is not None else None,
                pending_plan_effective_at=existing.pending_plan_effective_at if existing is not None else None,
                cancel_at_period_end=existing.cancel_at_period_end if existing is not None else False,
                updated_at=_utc_now(),
                grace_period_ends_at=existing.grace_period_ends_at if existing is not None else None,
                billing_status=(existing.billing_status if existing is not None else normalized_status.value),
            )
        )
        return self._resolve_response(
            subscription=persisted,
            plan=plan,
            current_charge_cents=plan.monthly_price if effective.day == 1 else detail.amount_cents,
            is_prorated=effective.day != 1,
            billable_days=detail.billable_days,
            days_in_month=detail.days_in_month,
            next_renewal_at=persisted.billing_cycle_end,
        )

    def apply_immediate_upgrade(
        self,
        *,
        organization_id: str,
        plan_id: str,
        effective_at: str | None = None,
    ) -> SubscriptionResolvedResponse:
        current, plan, effective = self._resolve_existing_subscription(organization_id=organization_id, plan_id=plan_id, effective_at=effective_at)
        current_plan = self.get_plan(current.plan_id)
        if plan.monthly_price < current_plan.monthly_price:
            raise SubscriptionScaffoldingError("Downgrades must be scheduled for the next billing period")
        cycle_start, cycle_end = month_cycle_window(effective)
        charge_cents = prorated_delta_amount_cents(current_plan.monthly_price, plan.monthly_price, effective)
        quota_delta = prorated_quota_delta(current_plan.request_limit, plan.request_limit, effective)
        persisted = self._subscriptions.put(
            SubscriptionRecord(
                subscription_id=current.subscription_id,
                organization_id=current.organization_id,
                plan_id=plan.plan_id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle_start=cycle_start,
                billing_cycle_end=cycle_end,
                created_at=current.created_at,
                pending_plan_id=None,
                pending_plan_effective_at=None,
                cancel_at_period_end=False,
                updated_at=_utc_now(),
                grace_period_ends_at=current.grace_period_ends_at,
                billing_status=current.billing_status or SubscriptionStatus.ACTIVE.value,
            )
        )
        detail = proration_detail(plan.monthly_price, effective)
        return self._resolve_response(
            subscription=persisted,
            plan=plan,
            current_charge_cents=charge_cents,
            is_prorated=effective.day != 1,
            billable_days=detail.billable_days,
            days_in_month=detail.days_in_month,
            next_renewal_at=persisted.billing_cycle_end,
            quota_delta=quota_delta,
        )

    def schedule_downgrade(
        self,
        *,
        organization_id: str,
        plan_id: str,
        effective_at: str | None = None,
    ) -> SubscriptionResolvedResponse:
        current, plan, effective = self._resolve_existing_subscription(organization_id=organization_id, plan_id=plan_id, effective_at=effective_at)
        next_renewal_at = _to_iso(next_month_boundary(effective))
        persisted = self._subscriptions.put(
            SubscriptionRecord(
                subscription_id=current.subscription_id,
                organization_id=current.organization_id,
                plan_id=current.plan_id,
                status=current.status,
                billing_cycle_start=current.billing_cycle_start,
                billing_cycle_end=current.billing_cycle_end,
                created_at=current.created_at,
                pending_plan_id=plan.plan_id,
                pending_plan_effective_at=next_renewal_at,
                cancel_at_period_end=current.cancel_at_period_end,
                updated_at=_utc_now(),
                grace_period_ends_at=current.grace_period_ends_at,
                billing_status=current.billing_status,
            )
        )
        current_plan = self.get_plan(current.plan_id)
        return self._resolve_response(
            subscription=persisted,
            plan=current_plan,
            current_charge_cents=0,
            is_prorated=False,
            next_renewal_at=persisted.billing_cycle_end,
            pending_plan_id=plan.plan_id,
            pending_plan_effective_at=next_renewal_at,
        )

    def schedule_cancellation(
        self,
        *,
        organization_id: str,
    ) -> SubscriptionResolvedResponse:
        self._ensure_seeded_plans()
        if self._organizations.get(organization_id) is None:
            raise SubscriptionScaffoldingError("organization_id must reference an existing organization")
        current = self._subscriptions.get_by_organization(organization_id)
        if current is None:
            raise SubscriptionScaffoldingError("Subscription was not found for this organization")
        plan = self.get_plan(current.plan_id)
        persisted = self._subscriptions.put(
            SubscriptionRecord(
                subscription_id=current.subscription_id,
                organization_id=current.organization_id,
                plan_id=current.plan_id,
                status=current.status,
                billing_cycle_start=current.billing_cycle_start,
                billing_cycle_end=current.billing_cycle_end,
                created_at=current.created_at,
                pending_plan_id=current.pending_plan_id,
                pending_plan_effective_at=current.pending_plan_effective_at,
                cancel_at_period_end=True,
                updated_at=_utc_now(),
                grace_period_ends_at=current.grace_period_ends_at,
                billing_status=current.billing_status,
            )
        )
        return self._resolve_response(
            subscription=persisted,
            plan=plan,
            current_charge_cents=0,
            is_prorated=False,
            next_renewal_at=persisted.billing_cycle_end,
            cancel_at_period_end=True,
        )

    def get_subscription_for_organization(self, organization_id: str) -> SubscriptionResolvedResponse:
        self._ensure_seeded_plans()
        if self._organizations.get(organization_id) is None:
            raise SubscriptionScaffoldingError("organization_id must reference an existing organization")
        subscription = self._subscriptions.get_by_organization(organization_id)
        if subscription is None:
            raise SubscriptionScaffoldingError("Subscription was not found for this organization")
        plan = self.get_plan(subscription.plan_id)
        return self._resolve_response(
            subscription=subscription,
            plan=plan,
            current_charge_cents=None,
            is_prorated=False,
            next_renewal_at=subscription.billing_cycle_end,
        )

    def _ensure_seeded_plans(self) -> None:
        if self._plans.list_all():
            return
        self._plans.seed_defaults(list(DEFAULT_PORTAL_PLANS))

    def _resolve_response(
        self,
        *,
        subscription: SubscriptionRecord,
        plan: PlanRecord,
        current_charge_cents: int | None,
        is_prorated: bool,
        next_renewal_at: str | None,
        billable_days: int | None = None,
        days_in_month: int | None = None,
        pending_plan_id: str | None = None,
        pending_plan_effective_at: str | None = None,
        cancel_at_period_end: bool | None = None,
        quota_delta: int | None = None,
    ) -> SubscriptionResolvedResponse:
        return SubscriptionResolvedResponse(
            subscription=subscription,
            plan=plan,
            current_charge_cents=current_charge_cents,
            is_prorated=is_prorated,
            billable_days=billable_days,
            days_in_month=days_in_month,
            next_renewal_at=next_renewal_at,
            pending_plan_id=pending_plan_id or subscription.pending_plan_id,
            pending_plan_effective_at=pending_plan_effective_at or subscription.pending_plan_effective_at,
            cancel_at_period_end=subscription.cancel_at_period_end if cancel_at_period_end is None else cancel_at_period_end,
            quota_delta=quota_delta,
        )

    def _resolve_existing_subscription(
        self,
        *,
        organization_id: str,
        plan_id: str,
        effective_at: str | None,
    ) -> tuple[SubscriptionRecord, PlanRecord, datetime]:
        self._ensure_seeded_plans()
        if self._organizations.get(organization_id) is None:
            raise SubscriptionScaffoldingError("organization_id must reference an existing organization")
        current = self._subscriptions.get_by_organization(organization_id)
        if current is None:
            raise SubscriptionScaffoldingError("Subscription was not found for this organization")
        plan = self.get_plan(plan_id)
        return current, plan, _parse_or_now(effective_at or _utc_now())


def _normalize_plan_id(plan_id: str) -> str:
    return str(plan_id or "").strip().lower()


def _validate_status(status: str) -> SubscriptionStatus:
    try:
        return SubscriptionStatus(str(status or "").strip().lower())
    except Exception as exc:  # noqa: BLE001
        raise SubscriptionScaffoldingError("status must be one of: active, past_due, canceled") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _parse_or_now(value: str) -> datetime:
    normalized = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized) if normalized else datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _to_iso(value: datetime) -> str:
    current = value
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()
