from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from verification.backend.shared.billing.runtime import call_with_retries
from verification.backend.shared.billing.service import DEFAULT_PLANS, EntitlementService, PLAN_CODE_ALIASES, PLAN_CODES
from verification.backend.shared.branding import DEFAULT_PUBLIC_BRAND_NAME, load_branding_config

logger = logging.getLogger(__name__)


class BillingCheckoutError(ValueError):
    status_code = 400
    code = "billing_checkout_error"


class BillingNotEnabledError(BillingCheckoutError):
    status_code = 404
    code = "not_found"


class BillingEligibilityError(BillingCheckoutError):
    status_code = 403
    code = "organization_ineligible"


class BillingConflictError(BillingCheckoutError):
    status_code = 409
    code = "billing_conflict"


class BillingProviderError(BillingCheckoutError):
    status_code = 502
    code = "billing_provider_error"

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class StripeCheckoutConfig:
    enabled: bool = False
    secret_key: str | None = None
    price_ids: dict[str, str] = field(default_factory=dict)
    public_brand_name: str = DEFAULT_PUBLIC_BRAND_NAME

    def price_id_for_plan(self, plan_code: str) -> str | None:
        return self.price_ids.get(plan_code)


@dataclass(frozen=True)
class BillingCheckoutRequest:
    plan_code: str
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class CheckoutSessionResult:
    session_id: str
    url: str
    expires_at: str | None = None


class StripeCheckoutClient(Protocol):
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

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        plan_code: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
    ) -> CheckoutSessionResult:
        ...


class BillingPlanCatalogProvider(Protocol):
    def get_mapping_for_plan(self, internal_plan_id: str):
        ...


class BillingCustomerBootstrapper(Protocol):
    def bootstrap_customer(
        self,
        *,
        organization_id: str,
        created_by_user_id: str | None,
    ):
        ...


class ControlPlaneBillingStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...

    def put_subscription(self, subscription: Any) -> None:
        ...


def load_stripe_checkout_config(env: Mapping[str, str] | None = None) -> StripeCheckoutConfig:
    source = env or {}
    branding = load_branding_config(source)
    enabled = _mapping_bool(source, "STRIPE_BILLING_ENABLED", False)
    secret_key = _clean_text(source.get("STRIPE_SECRET_KEY"))
    if not enabled:
        return StripeCheckoutConfig(
            enabled=False,
            secret_key=secret_key,
            price_ids={},
            public_brand_name=branding.public_brand_name,
        )
    price_ids = _parse_price_ids(source.get("STRIPE_PRICE_IDS"))
    if not secret_key:
        raise ValueError("STRIPE_SECRET_KEY is required when STRIPE_BILLING_ENABLED=true")
    if not price_ids:
        raise ValueError("STRIPE_PRICE_IDS is required when STRIPE_BILLING_ENABLED=true")
    return StripeCheckoutConfig(
        enabled=True,
        secret_key=secret_key,
        price_ids=price_ids,
        public_brand_name=branding.public_brand_name,
    )


class BillingCheckoutService:
    def __init__(
        self,
        *,
        store: ControlPlaneBillingStore,
        config: StripeCheckoutConfig,
        stripe_client: StripeCheckoutClient | None = None,
        plan_catalog_provider: BillingPlanCatalogProvider | None = None,
        customer_bootstrapper: BillingCustomerBootstrapper | None = None,
    ) -> None:
        self._store = store
        self._config = config
        self._stripe_client = stripe_client or HttpStripeCheckoutClient(
            secret_key=config.secret_key or "",
            public_brand_name=config.public_brand_name,
        )
        self._entitlement_service = EntitlementService()
        self._plan_catalog_provider = plan_catalog_provider
        self._customer_bootstrapper = customer_bootstrapper

    def create_checkout_session(self, *, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            raise BillingNotEnabledError("Billing checkout is not enabled")
        request = self._parse_request(payload)
        account = self._store.get_account(account_id)
        if account is None:
            raise BillingEligibilityError("Organization is not eligible for checkout")
        if str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            raise BillingEligibilityError("Organization is not eligible for checkout")
        subscription = self._get_subscription(account_id)
        if self._is_active_paid_plan(subscription, request.plan_code):
            raise BillingConflictError("Organization is already enrolled in the requested plan")
        pending = self._pending_session_for_plan(subscription, request.plan_code)
        if pending is not None:
            logger.info(
                "billing_checkout_reused",
                extra={"account_id": account_id, "plan_code": request.plan_code},
            )
            return pending

        customer_id = str(getattr(subscription, "stripe_customer_id", "") or "").strip()
        if not customer_id:
            customer_id = self._ensure_customer_id(
                account_id=account_id,
                account_name=str(getattr(account, "name", "") or account_id),
                ein=getattr(account, "ein", None),
            )
            subscription = self._store_subscription(
                subscription,
                stripe_customer_id=customer_id,
                updated_at=_utcnow(),
            )

        price_id = self._resolve_price_id(request.plan_code)
        if not price_id:
            raise BillingCheckoutError("Checkout is not available for the requested plan")
        session = self._stripe_client.create_checkout_session(
            customer_id=customer_id,
            account_id=account_id,
            plan_code=request.plan_code,
            price_id=price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            idempotency_key=f"checkout:{account_id}:{request.plan_code}",
        )
        self._store_subscription(
            subscription,
            stripe_customer_id=customer_id,
            billing_status="checkout_pending",
            pending_plan_code=request.plan_code,
            pending_checkout_session_id=session.session_id,
            pending_checkout_session_url=session.url,
            pending_checkout_expires_at=session.expires_at,
            updated_at=_utcnow(),
        )
        logger.info(
            "billing_checkout_created",
            extra={
                "account_id": account_id,
                "plan_code": request.plan_code,
                "stripe_customer_id": customer_id,
                "checkout_session_id": session.session_id,
            },
        )
        return {
            "plan_code": request.plan_code,
            "checkout_url": session.url,
            "checkout_session_id": session.session_id,
            "expires_at": session.expires_at,
            "reused": False,
        }

    def _parse_request(self, payload: dict[str, Any]) -> BillingCheckoutRequest:
        if not isinstance(payload, dict):
            raise BillingCheckoutError("Request body must be a JSON object")
        plan_code = self._normalize_requested_plan(payload.get("plan_code") or payload.get("plan"))
        success_url = _validated_redirect_url(payload.get("success_url"), "success_url")
        cancel_url = _validated_redirect_url(payload.get("cancel_url"), "cancel_url")
        return BillingCheckoutRequest(
            plan_code=plan_code,
            success_url=success_url,
            cancel_url=cancel_url,
        )

    def _normalize_requested_plan(self, value: Any) -> str:
        candidate = str(value or "").strip().lower()
        if not candidate:
            raise BillingCheckoutError("plan_code is required")
        if candidate not in PLAN_CODES and candidate not in PLAN_CODE_ALIASES:
            raise BillingCheckoutError("plan_code is invalid")
        normalized = self._entitlement_service.normalize_plan_code(candidate)
        if normalized == "free":
            raise BillingCheckoutError("Checkout is only available for paid plans")
        return normalized

    def _is_active_paid_plan(self, subscription: Any, requested_plan_code: str) -> bool:
        current_plan = str(getattr(subscription, "plan_code", "free") or "free").strip().lower()
        stripe_subscription_id = str(getattr(subscription, "stripe_subscription_id", "") or "").strip()
        status = str(getattr(subscription, "billing_status", getattr(subscription, "status", "active")) or "active").strip().lower()
        return current_plan == requested_plan_code and bool(stripe_subscription_id) and status in {"active", "trialing"}

    def _pending_session_for_plan(self, subscription: Any, requested_plan_code: str) -> dict[str, Any] | None:
        pending_plan_code = str(getattr(subscription, "pending_plan_code", "") or "").strip().lower()
        session_url = str(getattr(subscription, "pending_checkout_session_url", "") or "").strip()
        expires_at = _parse_iso_datetime(getattr(subscription, "pending_checkout_expires_at", None))
        if pending_plan_code != requested_plan_code or not session_url:
            return None
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            return None
        return {
            "plan_code": requested_plan_code,
            "checkout_url": session_url,
            "expires_at": getattr(subscription, "pending_checkout_expires_at", None),
            "reused": True,
        }

    def _get_subscription(self, account_id: str) -> Any:
        current = self._store.get_subscription(account_id)
        if current is not None:
            return current
        from verification.backend.shared.control_plane.models import ManagedSubscription

        return ManagedSubscription(
            account_id=account_id,
            plan_code="free",
            status="active",
            created_at=_utcnow(),
        )

    def _store_subscription(self, subscription: Any, **changes: Any) -> Any:
        updated = replace(subscription, **changes)
        self._store.put_subscription(updated)
        return updated

    def _resolve_price_id(self, plan_code: str) -> str | None:
        if self._plan_catalog_provider is not None:
            mapping = self._plan_catalog_provider.get_mapping_for_plan(plan_code)
            return str(getattr(mapping, "stripe_price_id", "") or "").strip() or None
        return self._config.price_id_for_plan(plan_code)

    def _ensure_customer_id(
        self,
        *,
        account_id: str,
        account_name: str,
        ein: str | None,
    ) -> str:
        if self._customer_bootstrapper is not None:
            bootstrap = self._customer_bootstrapper.bootstrap_customer(
                organization_id=account_id,
                created_by_user_id=None,
            )
            customer_id = str(getattr(bootstrap, "stripe_customer_id", "") or "").strip()
            if customer_id:
                logger.info(
                    "billing_customer_bootstrap_reused_for_checkout",
                    extra={"account_id": account_id, "stripe_customer_id": customer_id},
                )
                return customer_id
            raise BillingProviderError("Billing customer bootstrap did not return a Stripe customer id")
        customer_id = self._stripe_client.create_customer(
            account_id=account_id,
            account_name=account_name,
            ein=ein,
        )
        logger.info(
            "billing_customer_created_for_checkout",
            extra={"account_id": account_id, "stripe_customer_id": customer_id},
        )
        return customer_id


class HttpStripeCheckoutClient:
    _base_url = "https://api.stripe.com/v1"

    def __init__(self, *, secret_key: str, public_brand_name: str = DEFAULT_PUBLIC_BRAND_NAME) -> None:
        self._secret_key = secret_key.strip()
        self._public_brand_name = str(public_brand_name or DEFAULT_PUBLIC_BRAND_NAME).strip() or DEFAULT_PUBLIC_BRAND_NAME

    def create_customer(
        self,
        *,
        account_id: str,
        account_name: str,
        ein: str | None,
        metadata: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        payload = {
            "name": account_name,
            "description": f"{self._public_brand_name} account {account_id}",
            "metadata[account_id]": account_id,
        }
        if ein:
            payload["metadata[ein]"] = str(ein)
        for key, value in (metadata or {}).items():
            normalized_key = str(key or "").strip()
            normalized_value = _clean_text(value)
            if normalized_key and normalized_value:
                payload[f"metadata[{normalized_key}]"] = normalized_value
        response = self._post_form(
            "/customers",
            payload,
            idempotency_key=idempotency_key or f"customer:{account_id}",
            operation_name="customer creation",
        )
        customer_id = str(response.get("id") or "").strip()
        if not customer_id:
            raise BillingProviderError("Stripe customer creation did not return a customer id")
        return customer_id

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        plan_code: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
    ) -> CheckoutSessionResult:
        response = self._post_form(
            "/checkout/sessions",
            {
                "mode": "subscription",
                "customer": customer_id,
                "client_reference_id": account_id,
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "automatic_tax[enabled]": "true",
                "customer_update[address]": "auto",
                "billing_address_collection": "auto",
                "metadata[account_id]": account_id,
                "metadata[requested_plan_code]": plan_code,
                "subscription_data[metadata][account_id]": account_id,
                "subscription_data[metadata][requested_plan_code]": plan_code,
                "success_url": success_url,
                "cancel_url": cancel_url,
            },
            idempotency_key=idempotency_key,
            operation_name="checkout session creation",
        )
        session_id = str(response.get("id") or "").strip()
        session_url = str(response.get("url") or "").strip()
        if not session_id or not session_url:
            raise BillingProviderError("Stripe checkout session creation did not return a session url")
        expires_at = _stripe_epoch_to_iso(response.get("expires_at"))
        return CheckoutSessionResult(session_id=session_id, url=session_url, expires_at=expires_at)

    def _post_form(
        self,
        path: str,
        payload: dict[str, str],
        *,
        idempotency_key: str,
        operation_name: str,
    ) -> dict[str, Any]:
        def _request() -> dict[str, Any]:
            body = urlencode(payload).encode("utf-8")
            request = Request(
                url=f"{self._base_url}{path}",
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Basic {_basic_auth_token(self._secret_key)}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Idempotency-Key": idempotency_key,
                },
            )
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
            extra={"stripe_path": path, "idempotency_key": idempotency_key},
        )


def _parse_price_ids(raw: str | None) -> dict[str, str]:
    candidate = _clean_text(raw)
    if not candidate:
        return {}
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("STRIPE_PRICE_IDS must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("STRIPE_PRICE_IDS must be a JSON object")
    price_ids: dict[str, str] = {}
    for key, value in payload.items():
        plan_key = str(key or "").strip().lower()
        if plan_key not in PLAN_CODES and plan_key not in PLAN_CODE_ALIASES:
            raise ValueError(f"STRIPE_PRICE_IDS contains unsupported plan key '{key}'")
        normalized_plan = EntitlementService().normalize_plan_code(plan_key)
        if normalized_plan == "free":
            raise ValueError("STRIPE_PRICE_IDS should not define a checkout price for the free plan")
        price_id = _clean_text(value)
        if not price_id:
            raise ValueError(f"STRIPE_PRICE_IDS entry for '{key}' must be a non-empty string")
        price_ids[normalized_plan] = price_id
    return price_ids


def _validated_redirect_url(value: Any, field_name: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        raise BillingCheckoutError(f"{field_name} is required")
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise BillingCheckoutError(f"{field_name} must be a valid absolute URL")
    return candidate


def _mapping_bool(source: Mapping[str, str], key: str, default: bool) -> bool:
    raw = source.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _clean_text(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _stripe_epoch_to_iso(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    try:
        epoch = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _parse_iso_datetime(value: Any) -> datetime | None:
    candidate = _clean_text(value)
    if not candidate:
        return None
    normalized = f"{candidate[:-1]}+00:00" if candidate.endswith("Z") else candidate
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _stripe_error_message(exc: HTTPError, operation_name: str) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
    except Exception:
        return f"Stripe rejected the request during {operation_name}"
    error_payload = payload.get("error") if isinstance(payload, dict) else None
    message = str((error_payload or {}).get("message") or "").strip()
    if not message:
        return f"Stripe rejected the request during {operation_name}"
    return f"Stripe rejected the request during {operation_name}: {message}"


def _basic_auth_token(secret_key: str) -> str:
    return base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("ascii")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

