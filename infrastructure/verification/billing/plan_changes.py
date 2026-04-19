from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from verification.billing.checkout import (
    BillingCheckoutError,
    BillingConflictError,
    BillingEligibilityError,
    BillingNotEnabledError,
    BillingProviderError,
    StripeCheckoutConfig,
    _basic_auth_token,
    _clean_text,
    _stripe_epoch_to_iso,
    _stripe_error_message,
)
from verification.billing.runtime import call_with_retries
from verification.billing.service import EntitlementService, PLAN_CODE_ALIASES, PLAN_CODES

logger = logging.getLogger(__name__)


PLAN_CHANGE_SEQUENCE: tuple[str, ...] = ("free", "starter", "growth", "pro", "enterprise")


class BillingPlanChangeError(BillingCheckoutError):
    code = "billing_plan_change_error"


@dataclass(frozen=True)
class BillingPlanChangeRequest:
    plan_code: str


@dataclass(frozen=True)
class StripePriceSnapshot:
    price_id: str
    interval: str
    interval_count: int


@dataclass(frozen=True)
class StripeSubscriptionSnapshot:
    subscription_id: str
    customer_id: str | None
    item_id: str
    price_id: str
    status: str
    current_period_start: str | None
    current_period_end: str | None
    current_period_start_epoch: int | None
    current_period_end_epoch: int | None
    quantity: int
    cancel_at_period_end: bool
    schedule_id: str | None


class StripePlanChangeClient(Protocol):
    def retrieve_subscription(self, *, subscription_id: str) -> StripeSubscriptionSnapshot:
        ...

    def retrieve_price(self, *, price_id: str) -> StripePriceSnapshot:
        ...

    def apply_immediate_plan_change(
        self,
        *,
        subscription: StripeSubscriptionSnapshot,
        account_id: str,
        plan_code: str,
        price_id: str,
        idempotency_key: str,
    ) -> StripeSubscriptionSnapshot:
        ...

    def set_cancel_at_period_end(
        self,
        *,
        subscription_id: str,
        cancel_at_period_end: bool,
        idempotency_key: str,
    ) -> StripeSubscriptionSnapshot:
        ...

    def create_schedule_from_subscription(self, *, subscription_id: str, idempotency_key: str) -> str:
        ...

    def update_schedule_for_downgrade(
        self,
        *,
        schedule_id: str,
        subscription: StripeSubscriptionSnapshot,
        requested_price: StripePriceSnapshot,
        account_id: str,
        requested_plan_code: str,
        idempotency_key: str,
    ) -> str:
        ...

    def release_schedule(self, *, schedule_id: str, idempotency_key: str) -> None:
        ...


class ControlPlanePlanChangeStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...

    def put_subscription(self, subscription: Any) -> None:
        ...


class BillingPlanChangeService:
    def __init__(
        self,
        *,
        store: ControlPlanePlanChangeStore,
        config: StripeCheckoutConfig,
        stripe_client: StripePlanChangeClient | None = None,
    ) -> None:
        self._store = store
        self._config = config
        self._stripe_client = stripe_client or HttpStripePlanChangeClient(secret_key=config.secret_key or "")
        self._entitlement_service = EntitlementService()

    def change_plan(self, *, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            raise BillingNotEnabledError("Billing plan changes are not enabled")
        request = self._parse_request(payload)
        account = self._store.get_account(account_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            raise BillingEligibilityError("Organization is not eligible for plan changes")

        subscription = self._get_subscription(account_id)
        current_plan_code = self._entitlement_service.normalize_plan_code(getattr(subscription, "plan_code", "free"))
        pending_plan_code = self._entitlement_service.normalize_plan_code(getattr(subscription, "pending_plan_code", None) or current_plan_code)
        pending_plan_is_set = bool(getattr(subscription, "pending_plan_code", None))
        if request.plan_code == current_plan_code and pending_plan_is_set and pending_plan_code == request.plan_code:
            updated = self._clear_pending_change(subscription)
            return self._response_payload(updated, change_type="pending_change_cleared", reused=False)
        if request.plan_code == current_plan_code and not pending_plan_is_set:
            raise BillingConflictError("Organization is already enrolled in the requested plan")
        if request.plan_code == pending_plan_code and pending_plan_is_set:
            return self._response_payload(subscription, change_type=_scheduled_change_type(request.plan_code), reused=True)

        stripe_subscription_id = _clean_text(getattr(subscription, "stripe_subscription_id", None))
        if not stripe_subscription_id:
            raise BillingConflictError("Organization does not have an active Stripe subscription; use checkout to enroll first")

        stripe_subscription = self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription_id)
        if stripe_subscription.status not in {"active", "trialing"}:
            raise BillingConflictError("Organization does not have an active Stripe subscription")

        current_rank = _plan_rank(current_plan_code)
        requested_rank = _plan_rank(request.plan_code)

        if requested_rank >= current_rank:
            if pending_plan_is_set or stripe_subscription.schedule_id or stripe_subscription.cancel_at_period_end:
                self._clear_pending_change(subscription, stripe_subscription=stripe_subscription)
                subscription = self._get_subscription(account_id)
                stripe_subscription = self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription_id)
            if request.plan_code == current_plan_code:
                return self._response_payload(subscription, change_type="pending_change_cleared", reused=False)
            return self._apply_upgrade(
                subscription=subscription,
                stripe_subscription=stripe_subscription,
                requested_plan_code=request.plan_code,
            )

        return self._schedule_downgrade(
            subscription=subscription,
            stripe_subscription=stripe_subscription,
            requested_plan_code=request.plan_code,
        )

    def _parse_request(self, payload: dict[str, Any]) -> BillingPlanChangeRequest:
        if not isinstance(payload, dict):
            raise BillingPlanChangeError("Request body must be a JSON object")
        plan_code = self._normalize_requested_plan(payload.get("plan_code") or payload.get("plan"))
        return BillingPlanChangeRequest(plan_code=plan_code)

    def _normalize_requested_plan(self, value: Any) -> str:
        candidate = str(value or "").strip().lower()
        if not candidate:
            raise BillingPlanChangeError("plan_code is required")
        if candidate not in PLAN_CODES and candidate not in PLAN_CODE_ALIASES:
            raise BillingPlanChangeError("plan_code is invalid")
        return self._entitlement_service.normalize_plan_code(candidate)

    def _apply_upgrade(
        self,
        *,
        subscription: Any,
        stripe_subscription: StripeSubscriptionSnapshot,
        requested_plan_code: str,
    ) -> dict[str, Any]:
        price_id = self._config.price_id_for_plan(requested_plan_code)
        if not price_id:
            raise BillingPlanChangeError("Plan changes are not available for the requested plan")
        updated_remote = self._stripe_client.apply_immediate_plan_change(
            subscription=stripe_subscription,
            account_id=str(subscription.account_id),
            plan_code=requested_plan_code,
            price_id=price_id,
            idempotency_key=f"plan-change:{subscription.account_id}:upgrade:{requested_plan_code}",
        )
        updated = replace(
            subscription,
            plan_code=requested_plan_code,
            status="active",
            effective_from=_utcnow(),
            effective_to=None,
            stripe_customer_id=updated_remote.customer_id or getattr(subscription, "stripe_customer_id", None),
            stripe_subscription_id=updated_remote.subscription_id,
            stripe_subscription_schedule_id=updated_remote.schedule_id,
            billing_status=updated_remote.status,
            billing_period_start=updated_remote.current_period_start or getattr(subscription, "billing_period_start", None),
            billing_period_end=updated_remote.current_period_end or getattr(subscription, "billing_period_end", None),
            cancel_at_period_end=False,
            pending_plan_code=None,
            pending_plan_effective_at=None,
            pending_checkout_session_id=None,
            pending_checkout_session_url=None,
            pending_checkout_expires_at=None,
            updated_at=_utcnow(),
        )
        self._store.put_subscription(updated)
        logger.info(
            "billing_plan_change_applied",
            extra={
                "account_id": subscription.account_id,
                "change_type": "upgrade",
                "current_plan_code": getattr(subscription, "plan_code", None),
                "requested_plan_code": requested_plan_code,
                "stripe_subscription_id": updated_remote.subscription_id,
            },
        )
        return self._response_payload(updated, change_type="upgrade", reused=False)

    def _schedule_downgrade(
        self,
        *,
        subscription: Any,
        stripe_subscription: StripeSubscriptionSnapshot,
        requested_plan_code: str,
    ) -> dict[str, Any]:
        current_period_end = stripe_subscription.current_period_end
        if not current_period_end:
            raise BillingConflictError("Stripe subscription is missing a current billing period end")
        if requested_plan_code == "free":
            existing_schedule_id = stripe_subscription.schedule_id or _clean_text(getattr(subscription, "stripe_subscription_schedule_id", None))
            if existing_schedule_id:
                self._stripe_client.release_schedule(
                    schedule_id=existing_schedule_id,
                    idempotency_key=f"plan-change:{subscription.account_id}:release:{existing_schedule_id}",
                )
                stripe_subscription = self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription.subscription_id)
            if not stripe_subscription.cancel_at_period_end:
                updated_remote = self._stripe_client.set_cancel_at_period_end(
                    subscription_id=stripe_subscription.subscription_id,
                    cancel_at_period_end=True,
                    idempotency_key=f"plan-change:{subscription.account_id}:cancel",
                )
            else:
                updated_remote = stripe_subscription
            schedule_id = None
        else:
            price_id = self._config.price_id_for_plan(requested_plan_code)
            if not price_id:
                raise BillingPlanChangeError("Plan changes are not available for the requested plan")
            if stripe_subscription.cancel_at_period_end:
                stripe_subscription = self._stripe_client.set_cancel_at_period_end(
                    subscription_id=stripe_subscription.subscription_id,
                    cancel_at_period_end=False,
                    idempotency_key=f"plan-change:{subscription.account_id}:uncancel:{requested_plan_code}",
                )
            schedule_id = stripe_subscription.schedule_id or _clean_text(getattr(subscription, "stripe_subscription_schedule_id", None))
            if schedule_id:
                self._stripe_client.release_schedule(
                    schedule_id=schedule_id,
                    idempotency_key=f"plan-change:{subscription.account_id}:release:{schedule_id}",
                )
                stripe_subscription = self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription.subscription_id)
            requested_price = self._stripe_client.retrieve_price(price_id=price_id)
            schedule_id = self._stripe_client.create_schedule_from_subscription(
                subscription_id=stripe_subscription.subscription_id,
                idempotency_key=f"plan-change:{subscription.account_id}:schedule:{requested_plan_code}",
            )
            schedule_id = self._stripe_client.update_schedule_for_downgrade(
                schedule_id=schedule_id,
                subscription=stripe_subscription,
                requested_price=requested_price,
                account_id=str(subscription.account_id),
                requested_plan_code=requested_plan_code,
                idempotency_key=f"plan-change:{subscription.account_id}:schedule-update:{requested_plan_code}",
            )
            updated_remote = self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription.subscription_id)

        updated = replace(
            subscription,
            stripe_customer_id=updated_remote.customer_id or getattr(subscription, "stripe_customer_id", None),
            stripe_subscription_id=updated_remote.subscription_id,
            stripe_subscription_schedule_id=schedule_id,
            billing_status=updated_remote.status,
            billing_period_start=updated_remote.current_period_start or getattr(subscription, "billing_period_start", None),
            billing_period_end=updated_remote.current_period_end or current_period_end,
            cancel_at_period_end=(requested_plan_code == "free"),
            pending_plan_code=requested_plan_code,
            pending_plan_effective_at=current_period_end,
            updated_at=_utcnow(),
        )
        self._store.put_subscription(updated)
        logger.info(
            "billing_plan_change_applied",
            extra={
                "account_id": subscription.account_id,
                "change_type": _scheduled_change_type(requested_plan_code),
                "current_plan_code": getattr(subscription, "plan_code", None),
                "requested_plan_code": requested_plan_code,
                "stripe_subscription_id": updated_remote.subscription_id,
                "schedule_id": schedule_id,
                "cancel_at_period_end": requested_plan_code == "free",
            },
        )
        return self._response_payload(updated, change_type=_scheduled_change_type(requested_plan_code), reused=False)

    def _clear_pending_change(
        self,
        subscription: Any,
        *,
        stripe_subscription: StripeSubscriptionSnapshot | None = None,
    ) -> Any:
        stripe_subscription_id = _clean_text(getattr(subscription, "stripe_subscription_id", None))
        current_remote = stripe_subscription or (
            self._stripe_client.retrieve_subscription(subscription_id=stripe_subscription_id) if stripe_subscription_id else None
        )
        schedule_id = _clean_text(getattr(subscription, "stripe_subscription_schedule_id", None)) or (current_remote.schedule_id if current_remote else None)
        if schedule_id:
            self._stripe_client.release_schedule(
                schedule_id=schedule_id,
                idempotency_key=f"plan-change:{subscription.account_id}:release:{schedule_id}",
            )
        if current_remote is not None and current_remote.cancel_at_period_end:
            current_remote = self._stripe_client.set_cancel_at_period_end(
                subscription_id=current_remote.subscription_id,
                cancel_at_period_end=False,
                idempotency_key=f"plan-change:{subscription.account_id}:uncancel",
            )
        updated = replace(
            subscription,
            stripe_subscription_schedule_id=None,
            billing_status=(current_remote.status if current_remote is not None else getattr(subscription, "billing_status", None)),
            billing_period_start=(current_remote.current_period_start if current_remote is not None else getattr(subscription, "billing_period_start", None)),
            billing_period_end=(current_remote.current_period_end if current_remote is not None else getattr(subscription, "billing_period_end", None)),
            cancel_at_period_end=False,
            pending_plan_code=None,
            pending_plan_effective_at=None,
            updated_at=_utcnow(),
        )
        self._store.put_subscription(updated)
        logger.info(
            "billing_plan_change_cleared",
            extra={
                "account_id": subscription.account_id,
                "stripe_subscription_id": getattr(subscription, "stripe_subscription_id", None),
            },
        )
        return updated

    def _get_subscription(self, account_id: str) -> Any:
        current = self._store.get_subscription(account_id)
        if current is None:
            from verification.control_plane.models import ManagedSubscription

            return ManagedSubscription(account_id=account_id, plan_code="free", status="active", created_at=_utcnow())
        return current

    def _response_payload(self, subscription: Any, *, change_type: str, reused: bool) -> dict[str, Any]:
        return {
            "account_id": str(getattr(subscription, "account_id", "") or ""),
            "current_plan_code": str(getattr(subscription, "plan_code", "free") or "free"),
            "pending_plan_code": getattr(subscription, "pending_plan_code", None),
            "effective_from": getattr(subscription, "effective_from", None),
            "effective_to": getattr(subscription, "effective_to", None),
            "billing_period_start": getattr(subscription, "billing_period_start", None),
            "billing_period_end": getattr(subscription, "billing_period_end", None),
            "pending_plan_effective_at": getattr(subscription, "pending_plan_effective_at", None),
            "billing_status": getattr(subscription, "billing_status", None),
            "change_type": change_type,
            "reused": reused,
        }


class HttpStripePlanChangeClient:
    _base_url = "https://api.stripe.com/v1"

    def __init__(self, *, secret_key: str) -> None:
        self._secret_key = secret_key.strip()

    def retrieve_subscription(self, *, subscription_id: str) -> StripeSubscriptionSnapshot:
        response = self._request_json("GET", f"/subscriptions/{subscription_id}", operation_name="subscription retrieval")
        return _subscription_snapshot_from_response(response)

    def retrieve_price(self, *, price_id: str) -> StripePriceSnapshot:
        response = self._request_json("GET", f"/prices/{price_id}", operation_name="price retrieval")
        recurring = response.get("recurring") if isinstance(response, dict) else None
        interval = _clean_text((recurring or {}).get("interval"))
        if not interval:
            raise BillingProviderError("Stripe price retrieval did not return recurring interval metadata")
        interval_count = int((recurring or {}).get("interval_count") or 1)
        return StripePriceSnapshot(price_id=price_id, interval=interval, interval_count=max(1, interval_count))

    def apply_immediate_plan_change(
        self,
        *,
        subscription: StripeSubscriptionSnapshot,
        account_id: str,
        plan_code: str,
        price_id: str,
        idempotency_key: str,
    ) -> StripeSubscriptionSnapshot:
        response = self._request_json(
            "POST",
            f"/subscriptions/{subscription.subscription_id}",
            payload={
                "items[0][id]": subscription.item_id,
                "items[0][price]": price_id,
                "proration_behavior": "always_invoice",
                "payment_behavior": "error_if_incomplete",
                "metadata[account_id]": account_id,
                "metadata[requested_plan_code]": plan_code,
            },
            idempotency_key=idempotency_key,
            operation_name="subscription upgrade",
        )
        return _subscription_snapshot_from_response(response)

    def set_cancel_at_period_end(
        self,
        *,
        subscription_id: str,
        cancel_at_period_end: bool,
        idempotency_key: str,
    ) -> StripeSubscriptionSnapshot:
        response = self._request_json(
            "POST",
            f"/subscriptions/{subscription_id}",
            payload={"cancel_at_period_end": "true" if cancel_at_period_end else "false"},
            idempotency_key=idempotency_key,
            operation_name="subscription cancellation update",
        )
        return _subscription_snapshot_from_response(response)

    def create_schedule_from_subscription(self, *, subscription_id: str, idempotency_key: str) -> str:
        response = self._request_json(
            "POST",
            "/subscription_schedules",
            payload={"from_subscription": subscription_id},
            idempotency_key=idempotency_key,
            operation_name="subscription schedule creation",
        )
        schedule_id = _clean_text(response.get("id")) if isinstance(response, dict) else None
        if not schedule_id:
            raise BillingProviderError("Stripe schedule creation did not return a schedule id")
        return schedule_id

    def update_schedule_for_downgrade(
        self,
        *,
        schedule_id: str,
        subscription: StripeSubscriptionSnapshot,
        requested_price: StripePriceSnapshot,
        account_id: str,
        requested_plan_code: str,
        idempotency_key: str,
    ) -> str:
        if subscription.current_period_start_epoch is None or subscription.current_period_end_epoch is None:
            raise BillingProviderError("Stripe subscription is missing billing period boundaries required for downgrade scheduling")
        response = self._request_json(
            "POST",
            f"/subscription_schedules/{schedule_id}",
            payload={
                "end_behavior": "release",
                "proration_behavior": "none",
                "default_settings[automatic_tax][enabled]": "true",
                "phases[0][items][0][price]": subscription.price_id,
                "phases[0][items][0][quantity]": str(max(1, subscription.quantity)),
                "phases[0][start_date]": str(subscription.current_period_start_epoch),
                "phases[0][end_date]": str(subscription.current_period_end_epoch),
                "phases[0][proration_behavior]": "none",
                "phases[0][metadata][account_id]": account_id,
                "phases[1][items][0][price]": requested_price.price_id,
                "phases[1][items][0][quantity]": str(max(1, subscription.quantity)),
                "phases[1][start_date]": str(subscription.current_period_end_epoch),
                "phases[1][duration][interval]": requested_price.interval,
                "phases[1][duration][interval_count]": str(max(1, requested_price.interval_count)),
                "phases[1][proration_behavior]": "none",
                "phases[1][metadata][account_id]": account_id,
                "phases[1][metadata][requested_plan_code]": requested_plan_code,
                "phases[1][automatic_tax][enabled]": "true",
            },
            idempotency_key=idempotency_key,
            operation_name="subscription downgrade scheduling",
        )
        updated_schedule_id = _clean_text(response.get("id")) if isinstance(response, dict) else None
        if not updated_schedule_id:
            raise BillingProviderError("Stripe schedule update did not return a schedule id")
        return updated_schedule_id

    def release_schedule(self, *, schedule_id: str, idempotency_key: str) -> None:
        self._request_json(
            "POST",
            f"/subscription_schedules/{schedule_id}/release",
            payload={"preserve_cancel_date": "false"},
            idempotency_key=idempotency_key,
            operation_name="subscription schedule release",
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, str] | None = None,
        idempotency_key: str | None = None,
        operation_name: str,
    ) -> dict[str, Any]:
        def _request() -> dict[str, Any]:
            data = urlencode(payload or {}).encode("utf-8") if payload is not None else None
            headers = {
                "Authorization": f"Basic {_basic_auth_token(self._secret_key)}",
            }
            if data is not None:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
            request = Request(url=f"{self._base_url}{path}", data=data, method=method, headers=headers)
            try:
                with urlopen(request, timeout=15) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise BillingProviderError(
                    _stripe_error_message(exc, operation_name),
                    retryable=exc.code >= 500 or exc.code == 429,
                ) from exc
            except URLError as exc:
                raise BillingProviderError(f"Unable to reach Stripe during {operation_name}", retryable=True) from exc
            except json.JSONDecodeError as exc:
                raise BillingProviderError(f"Stripe returned an invalid response during {operation_name}") from exc

        return call_with_retries(
            operation_name,
            _request,
            should_retry=lambda exc: isinstance(exc, BillingProviderError) and bool(getattr(exc, "retryable", False)),
            logger=logger,
            extra={"stripe_path": path, "idempotency_key": idempotency_key or ""},
        )


def _plan_rank(plan_code: str) -> int:
    try:
        return PLAN_CHANGE_SEQUENCE.index(plan_code)
    except ValueError:
        return 0


def _scheduled_change_type(plan_code: str) -> str:
    return "cancellation_scheduled" if plan_code == "free" else "downgrade_scheduled"


def _subscription_snapshot_from_response(payload: dict[str, Any]) -> StripeSubscriptionSnapshot:
    subscription_id = _clean_text(payload.get("id"))
    items = (((payload.get("items") or {}).get("data")) or [])
    if not subscription_id or not items or not isinstance(items[0], dict):
        raise BillingProviderError("Stripe subscription response did not include subscription items")
    item = items[0]
    price = item.get("price") or {}
    item_id = _clean_text(item.get("id"))
    price_id = _clean_text(price.get("id"))
    if not item_id or not price_id:
        raise BillingProviderError("Stripe subscription response did not include subscription price details")
    current_period_start_epoch = _optional_int(payload.get("current_period_start"))
    current_period_end_epoch = _optional_int(payload.get("current_period_end"))
    return StripeSubscriptionSnapshot(
        subscription_id=subscription_id,
        customer_id=_clean_text(payload.get("customer")),
        item_id=item_id,
        price_id=price_id,
        status=str(payload.get("status") or "").strip().lower(),
        current_period_start=_stripe_epoch_to_iso(current_period_start_epoch),
        current_period_end=_stripe_epoch_to_iso(current_period_end_epoch),
        current_period_start_epoch=current_period_start_epoch,
        current_period_end_epoch=current_period_end_epoch,
        quantity=max(1, _optional_int(item.get("quantity")) or 1),
        cancel_at_period_end=bool(payload.get("cancel_at_period_end")),
        schedule_id=_clean_text(payload.get("schedule")),
    )


def _optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

