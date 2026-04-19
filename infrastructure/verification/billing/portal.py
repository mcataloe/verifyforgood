from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from verification.billing.checkout import (
    BillingCheckoutError,
    BillingEligibilityError,
    BillingNotEnabledError,
    BillingProviderError,
    StripeCheckoutConfig,
    _basic_auth_token,
    _clean_text,
    _stripe_error_message,
    _validated_redirect_url,
)
from verification.billing.runtime import call_with_retries

logger = logging.getLogger(__name__)


class BillingPortalError(BillingCheckoutError):
    code = "billing_portal_error"


@dataclass(frozen=True)
class BillingPortalRequest:
    return_url: str


@dataclass(frozen=True)
class PortalSessionResult:
    session_id: str
    url: str


class StripePortalClient(Protocol):
    def create_portal_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        return_url: str,
        idempotency_key: str,
    ) -> PortalSessionResult:
        ...


class ControlPlaneBillingPortalStore(Protocol):
    def get_account(self, account_id: str):
        ...

    def get_subscription(self, account_id: str):
        ...


class BillingPortalService:
    def __init__(
        self,
        *,
        store: ControlPlaneBillingPortalStore,
        config: StripeCheckoutConfig,
        stripe_client: StripePortalClient | None = None,
    ) -> None:
        self._store = store
        self._config = config
        self._stripe_client = stripe_client or HttpStripePortalClient(secret_key=config.secret_key or "")

    def create_portal_session(self, *, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._config.enabled:
            raise BillingNotEnabledError("Billing portal is not enabled")
        request = self._parse_request(payload)
        account = self._store.get_account(account_id)
        if account is None or str(getattr(account, "status", "active") or "active").strip().lower() != "active":
            raise BillingEligibilityError("Organization is not eligible for portal access")
        subscription = self._store.get_subscription(account_id)
        customer_id = _clean_text(getattr(subscription, "stripe_customer_id", None) if subscription is not None else None)
        if not customer_id:
            raise BillingPortalError("Organization does not have an active Stripe billing profile")
        session = self._stripe_client.create_portal_session(
            customer_id=customer_id,
            account_id=account_id,
            return_url=request.return_url,
            idempotency_key=f"portal:{account_id}:{customer_id}",
        )
        logger.info(
            "billing_portal_created",
            extra={"account_id": account_id, "stripe_customer_id": customer_id, "portal_session_id": session.session_id},
        )
        return {"portal_url": session.url}

    def _parse_request(self, payload: dict[str, Any]) -> BillingPortalRequest:
        if not isinstance(payload, dict):
            raise BillingPortalError("Request body must be a JSON object")
        return BillingPortalRequest(return_url=_validated_redirect_url(payload.get("return_url"), "return_url"))


class HttpStripePortalClient:
    _base_url = "https://api.stripe.com/v1"

    def __init__(self, *, secret_key: str) -> None:
        self._secret_key = secret_key.strip()

    def create_portal_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        return_url: str,
        idempotency_key: str,
    ) -> PortalSessionResult:
        def _request() -> dict[str, Any]:
            request = Request(
                url=f"{self._base_url}/billing_portal/sessions",
                data=urlencode(
                    {
                        "customer": customer_id,
                        "return_url": return_url,
                    }
                ).encode("utf-8"),
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
                    _stripe_error_message(exc, "portal session creation"),
                    retryable=exc.code >= 500 or exc.code == 429,
                ) from exc
            except URLError as exc:
                raise BillingProviderError("Unable to reach Stripe during portal session creation", retryable=True) from exc
            except json.JSONDecodeError as exc:
                raise BillingProviderError("Stripe returned an invalid response during portal session creation") from exc

        payload = call_with_retries(
            "portal session creation",
            _request,
            should_retry=lambda exc: isinstance(exc, BillingProviderError) and bool(getattr(exc, "retryable", False)),
            logger=logger,
            extra={"account_id": account_id, "stripe_customer_id": customer_id, "idempotency_key": idempotency_key},
        )
        session_id = str(payload.get("id") or "").strip()
        url = str(payload.get("url") or "").strip()
        if not session_id or not url:
            raise BillingProviderError("Stripe portal session creation did not return a session url")
        return PortalSessionResult(session_id=session_id, url=url)

