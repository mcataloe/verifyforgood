from __future__ import annotations

from urllib.error import URLError

from verification.billing.checkout import (
    BillingCheckoutError,
    BillingCheckoutService,
    BillingProviderError,
    HttpStripeCheckoutClient,
    StripeCheckoutConfig,
    CheckoutSessionResult,
    load_stripe_checkout_config,
)
from verification.billing.runtime import validate_stripe_billing_environment
from verification.control_plane import ControlPlaneService, InMemoryControlPlaneStore


class _StripeClient:
    def __init__(self, *, expected_price_id: str = "price_growth", expected_customer_id: str = "cus_test_123") -> None:
        self.customer_calls = 0
        self.session_calls = 0
        self.expected_price_id = expected_price_id
        self.expected_customer_id = expected_customer_id

    def create_customer(self, *, account_id: str, account_name: str, ein: str | None) -> str:
        self.customer_calls += 1
        assert account_id.startswith("acct_")
        assert account_name
        return "cus_test_123"

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
        self.session_calls += 1
        assert customer_id == self.expected_customer_id
        assert account_id.startswith("acct_")
        assert plan_code == "growth"
        assert price_id == self.expected_price_id
        assert success_url == "https://example.com/success"
        assert cancel_url == "https://example.com/cancel"
        assert idempotency_key == f"checkout:{account_id}:growth"
        return CheckoutSessionResult(
            session_id="cs_test_123",
            url="https://checkout.stripe.com/c/pay/cs_test_123",
            expires_at="2099-03-20T00:00:00+00:00",
        )


class _FailingStripeClient:
    def create_customer(self, *, account_id: str, account_name: str, ein: str | None) -> str:
        return "cus_test_123"

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
        raise BillingProviderError("Stripe rejected the request during checkout session creation")


class _PlanCatalogProvider:
    class _Mapping:
        def __init__(self, stripe_price_id: str) -> None:
            self.stripe_price_id = stripe_price_id

    def __init__(self, stripe_price_id: str) -> None:
        self.calls: list[str] = []
        self._stripe_price_id = stripe_price_id

    def get_mapping_for_plan(self, internal_plan_id: str):
        self.calls.append(internal_plan_id)
        return self._Mapping(self._stripe_price_id)


class _Bootstrapper:
    class _Result:
        def __init__(self, stripe_customer_id: str) -> None:
            self.stripe_customer_id = stripe_customer_id

    def __init__(self, stripe_customer_id: str = "cus_bootstrap_123") -> None:
        self.calls: list[tuple[str, str | None]] = []
        self._stripe_customer_id = stripe_customer_id

    def bootstrap_customer(self, *, organization_id: str, created_by_user_id: str | None):
        self.calls.append((organization_id, created_by_user_id))
        return self._Result(self._stripe_customer_id)


def test_load_stripe_checkout_config_defaults_disabled():
    config = load_stripe_checkout_config({})

    assert config.enabled is False
    assert config.price_ids == {}


def test_load_stripe_checkout_config_requires_key_when_enabled():
    try:
        load_stripe_checkout_config(
            {
                "STRIPE_BILLING_ENABLED": "true",
                "STRIPE_PRICE_IDS": '{"growth":"price_growth"}',
            }
        )
    except ValueError as exc:
        assert str(exc) == "STRIPE_SECRET_KEY is required when STRIPE_BILLING_ENABLED=true"
    else:
        assert False, "Expected Stripe secret key validation error"


def test_validate_stripe_billing_environment_requires_webhook_secret_when_enabled():
    try:
        validate_stripe_billing_environment(
            {
                "STRIPE_BILLING_ENABLED": "true",
                "STRIPE_SECRET_KEY": "sk_test_123",
                "STRIPE_PRICE_IDS": '{"growth":"price_growth"}',
            }
        )
    except ValueError as exc:
        assert str(exc) == "STRIPE_WEBHOOK_SECRET is required when STRIPE_BILLING_ENABLED=true"
    else:
        assert False, "Expected Stripe webhook secret validation error"


def test_billing_checkout_creates_customer_and_session_and_persists_linkage():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Checkout Account", "ein": "12-3456789"})
    stripe = _StripeClient()
    service = BillingCheckoutService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=stripe,
    )

    payload = service.create_checkout_session(
        account_id=account["id"],
        payload={
            "plan_code": "growth",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )
    subscription = control_plane.store.get_subscription(account["id"])

    assert payload["plan_code"] == "growth"
    assert payload["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_123"
    assert payload["reused"] is False
    assert stripe.customer_calls == 1
    assert stripe.session_calls == 1
    assert subscription is not None
    assert subscription.stripe_customer_id == "cus_test_123"
    assert subscription.billing_status == "checkout_pending"
    assert subscription.pending_plan_code == "growth"
    assert subscription.pending_checkout_session_id == "cs_test_123"


def test_billing_checkout_reuses_pending_session_for_duplicate_request():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Checkout Account", "ein": "123456789"})
    stripe = _StripeClient()
    service = BillingCheckoutService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=stripe,
    )
    request_payload = {
        "plan_code": "growth",
        "success_url": "https://example.com/success",
        "cancel_url": "https://example.com/cancel",
    }

    first = service.create_checkout_session(account_id=account["id"], payload=request_payload)
    second = service.create_checkout_session(account_id=account["id"], payload=request_payload)

    assert first["checkout_url"] == second["checkout_url"]
    assert second["reused"] is True
    assert stripe.customer_calls == 1
    assert stripe.session_calls == 1


def test_billing_checkout_uses_authoritative_plan_mapping_and_customer_bootstrap():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Checkout Account", "ein": "123456789"})
    stripe = _StripeClient(
        expected_price_id="price_growth_authoritative",
        expected_customer_id="cus_bootstrap_123",
    )
    plan_catalog = _PlanCatalogProvider("price_growth_authoritative")
    bootstrapper = _Bootstrapper("cus_bootstrap_123")
    service = BillingCheckoutService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth_config"},
        ),
        stripe_client=stripe,
        plan_catalog_provider=plan_catalog,
        customer_bootstrapper=bootstrapper,
    )

    payload = service.create_checkout_session(
        account_id=account["id"],
        payload={
            "plan_code": "growth",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        },
    )

    subscription = control_plane.store.get_subscription(account["id"])
    assert payload["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_123"
    assert payload["checkout_session_id"] == "cs_test_123"
    assert plan_catalog.calls == ["growth"]
    assert bootstrapper.calls == [(account["id"], None)]
    assert stripe.customer_calls == 0
    assert stripe.session_calls == 1
    assert subscription is not None
    assert subscription.stripe_customer_id == "cus_bootstrap_123"


def test_billing_checkout_rejects_invalid_plan():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Checkout Account", "ein": "123456789"})
    service = BillingCheckoutService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=_StripeClient(),
    )

    try:
        service.create_checkout_session(
            account_id=account["id"],
            payload={
                "plan_code": "unknown",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        )
    except BillingCheckoutError as exc:
        assert exc.status_code == 400
        assert str(exc) == "plan_code is invalid"
    else:
        assert False, "Expected invalid plan error"


def test_billing_checkout_rejects_free_plan_cleanly():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Checkout Account", "ein": "123456789"})
    service = BillingCheckoutService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=_StripeClient(),
    )

    try:
        service.create_checkout_session(
            account_id=account["id"],
            payload={
                "plan_code": "free",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        )
    except BillingCheckoutError as exc:
        assert exc.status_code == 400
        assert str(exc) == "Checkout is only available for paid plans"
    else:
        assert False, "Expected free-plan rejection"


def test_billing_checkout_surfaces_stripe_provider_failures():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Checkout Account", "ein": "123456789"})
    service = BillingCheckoutService(
        store=control_plane.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=_FailingStripeClient(),
    )

    try:
        service.create_checkout_session(
            account_id=account["id"],
            payload={
                "plan_code": "growth",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
        )
    except BillingProviderError as exc:
        assert exc.status_code == 502
        assert "Stripe rejected the request" in str(exc)
    else:
        assert False, "Expected Stripe provider error"


def test_http_stripe_checkout_client_retries_transient_url_errors(monkeypatch):
    attempts = {"count": 0}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"id":"cs_test_123","url":"https://checkout.stripe.com/c/pay/cs_test_123"}'

    def _fake_urlopen(request, timeout=15):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise URLError("temporary outage")
        return _Response()

    monkeypatch.setattr("verification.billing.checkout.urlopen", _fake_urlopen)
    client = HttpStripeCheckoutClient(secret_key="sk_test_123")

    session = client.create_checkout_session(
        customer_id="cus_test_123",
        account_id="acct_1",
        plan_code="growth",
        price_id="price_growth",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        idempotency_key="checkout:acct_1:growth",
    )

    assert session.session_id == "cs_test_123"
    assert attempts["count"] == 2

