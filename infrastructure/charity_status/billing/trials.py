from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol


TRIAL_ACTIVATION_ROUTE_KEYS: tuple[str, ...] = (
    "POST /v1/verify",
    "POST /v1/nonprofits/verify",
    "POST /v1/verify/batch",
    "GET /v1/nonprofit/{ein}",
    "GET /v1/nonprofits/{ein}",
    "GET /v1/nonprofit/{ein}/filings",
    "GET /v1/nonprofits/search",
    "GET /v1/nonprofits/{ein}/sources",
    "GET /v1/nonprofits/{ein}/sources/{source_name}",
    "GET /v1/nonprofits/{ein}/compliance",
    "GET /v1/nonprofits/{ein}/federal-awards",
)


@dataclass(frozen=True)
class TrialConfig:
    enabled: bool = False
    duration_days: int = 14
    plan_code: str = "growth"
    monthly_request_limit_override: int | None = None


class TrialStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...

    def put_subscription(self, subscription: Any) -> None:
        ...

    def get_trial_history(self, ein: str):
        ...

    def put_trial_history(self, history: Any) -> None:
        ...


def load_trial_config(env: Mapping[str, str] | None = None) -> TrialConfig:
    source = env or {}
    enabled = _mapping_bool(source, "FREE_TRIAL_ENABLED", False)
    duration_days = _positive_int(source.get("FREE_TRIAL_DURATION_DAYS"), default=14, field_name="FREE_TRIAL_DURATION_DAYS")
    plan_code = str(source.get("FREE_TRIAL_PLAN_CODE") or "growth").strip().lower()
    if plan_code not in {"growth", "pro"}:
        raise ValueError("FREE_TRIAL_PLAN_CODE must be growth or pro")
    monthly_limit_override = _optional_positive_int(source.get("FREE_TRIAL_MONTHLY_REQUEST_LIMIT"), field_name="FREE_TRIAL_MONTHLY_REQUEST_LIMIT")
    return TrialConfig(
        enabled=enabled,
        duration_days=duration_days,
        plan_code=plan_code,
        monthly_request_limit_override=monthly_limit_override,
    )


class TrialLifecycleService:
    def __init__(self, *, store: TrialStore, config: TrialConfig) -> None:
        self._store = store
        self._config = config

    def refresh_subscription(self, *, account_id: str, now: datetime | None = None):
        subscription = self._store.get_subscription(account_id)
        if subscription is None:
            return None
        if not _trial_has_expired(subscription, now=now):
            return subscription
        current = now or datetime.now(timezone.utc)
        updated = replace(
            subscription,
            trial_status="expired",
            trial_termination_reason="expired_to_free",
            updated_at=current.isoformat(),
        )
        self._store.put_subscription(updated)
        self._update_trial_history(
            ein=getattr(self._store.get_account(account_id), "ein", None),
            account_id=account_id,
            trial_started_at=getattr(updated, "trial_started_at", None),
            trial_ended_at=current.isoformat(),
            last_status="expired",
            termination_reason="expired_to_free",
        )
        return updated

    def maybe_activate_trial(self, *, account_id: str, trigger_event: str, now: datetime | None = None):
        subscription = self.refresh_subscription(account_id=account_id, now=now)
        if not self._config.enabled or trigger_event not in TRIAL_ACTIVATION_ROUTE_KEYS:
            return subscription
        account = self._store.get_account(account_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            return subscription
        ein = str(getattr(account, "ein", "") or "").strip()
        if not ein:
            return subscription
        if subscription is None:
            return None
        if _subscription_has_paid_plan(subscription):
            return subscription
        trial_status = str(getattr(subscription, "trial_status", "never_started") or "never_started").strip().lower()
        if trial_status == "active":
            return subscription
        history = self._store.get_trial_history(ein)
        if bool(getattr(history, "trial_consumed", False)):
            if trial_status != "ineligible":
                updated = replace(
                    subscription,
                    trial_status="ineligible",
                    trial_consumed=True,
                    trial_termination_reason="already_consumed",
                    updated_at=(now or datetime.now(timezone.utc)).isoformat(),
                )
                self._store.put_subscription(updated)
                return updated
            return subscription
        if trial_status not in {"never_started", "", "ineligible"} and trial_status is not None:
            return subscription
        current = now or datetime.now(timezone.utc)
        ends_at = current + timedelta(days=self._config.duration_days)
        updated = replace(
            subscription,
            trial_status="active",
            trial_started_at=current.isoformat(),
            trial_ends_at=ends_at.isoformat(),
            trial_trigger_event=trigger_event,
            trial_consumed=True,
            trial_termination_reason=None,
            updated_at=current.isoformat(),
        )
        self._store.put_subscription(updated)
        self._update_trial_history(
            ein=ein,
            account_id=account_id,
            trial_started_at=updated.trial_started_at,
            trial_ended_at=None,
            last_status="active",
            termination_reason=None,
        )
        return updated

    def mark_paid_conversion(self, *, account_id: str, now: datetime | None = None):
        subscription = self._store.get_subscription(account_id)
        if subscription is None:
            return None
        if not _subscription_has_paid_plan(subscription):
            return subscription
        if str(getattr(subscription, "trial_status", "") or "").strip().lower() != "active":
            return subscription
        current = now or datetime.now(timezone.utc)
        updated = replace(
            subscription,
            trial_status="converted",
            trial_termination_reason="converted_to_paid",
            updated_at=current.isoformat(),
        )
        self._store.put_subscription(updated)
        self._update_trial_history(
            ein=getattr(self._store.get_account(account_id), "ein", None),
            account_id=account_id,
            trial_started_at=getattr(updated, "trial_started_at", None),
            trial_ended_at=current.isoformat(),
            last_status="converted",
            termination_reason="converted_to_paid",
        )
        return updated

    def trial_summary(self, subscription: object, *, now: datetime | None = None) -> dict[str, object] | None:
        status = str(getattr(subscription, "trial_status", "") or "").strip().lower()
        if not status:
            return None
        effective_status = "expired" if _trial_has_expired(subscription, now=now) else status
        return {
            "active": effective_status == "active",
            "status": effective_status,
            "ends_at": getattr(subscription, "trial_ends_at", None),
        }

    def _update_trial_history(
        self,
        *,
        ein: str | None,
        account_id: str,
        trial_started_at: str | None,
        trial_ended_at: str | None,
        last_status: str,
        termination_reason: str | None,
    ) -> None:
        cleaned_ein = str(ein or "").strip()
        if not cleaned_ein:
            return
        from charity_status.billing.models import TrialHistory

        current = self._store.get_trial_history(cleaned_ein)
        history = TrialHistory(
            ein=cleaned_ein,
            trial_consumed=True,
            first_account_id=getattr(current, "first_account_id", None) or account_id,
            last_account_id=account_id,
            trial_started_at=getattr(current, "trial_started_at", None) or trial_started_at,
            trial_ended_at=trial_ended_at if trial_ended_at is not None else getattr(current, "trial_ended_at", None),
            last_status=last_status,
            last_termination_reason=termination_reason,
            updated_at=(datetime.now(timezone.utc)).isoformat(),
        )
        self._store.put_trial_history(history)


def _subscription_has_paid_plan(subscription: object) -> bool:
    plan_code = str(getattr(subscription, "plan_code", "free") or "free").strip().lower()
    stripe_subscription_id = str(getattr(subscription, "stripe_subscription_id", "") or "").strip()
    return plan_code != "free" and bool(stripe_subscription_id)


def _trial_has_expired(subscription: object, *, now: datetime | None = None) -> bool:
    if str(getattr(subscription, "trial_status", "") or "").strip().lower() != "active":
        return False
    trial_ends_at = _parse_iso_datetime(getattr(subscription, "trial_ends_at", None))
    if trial_ends_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current >= trial_ends_at


def _parse_iso_datetime(value: Any) -> datetime | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    normalized = f"{candidate[:-1]}+00:00" if candidate.endswith("Z") else candidate
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _mapping_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    raw = source.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _positive_int(raw: Any, *, default: int, field_name: str) -> int:
    candidate = str(raw or "").strip()
    if not candidate:
        return default
    value = int(candidate)
    if value < 1:
        raise ValueError(f"{field_name} must be at least 1")
    return value


def _optional_positive_int(raw: Any, *, field_name: str) -> int | None:
    candidate = str(raw or "").strip()
    if not candidate:
        return None
    value = int(candidate)
    if value < 1:
        raise ValueError(f"{field_name} must be at least 1 when set")
    return value
