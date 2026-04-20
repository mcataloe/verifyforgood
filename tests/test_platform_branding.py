from __future__ import annotations

from pathlib import Path

from verification.branding import default_runtime_user_agent, load_branding_config
from verification.billing.checkout import HttpStripeCheckoutClient, load_stripe_checkout_config
from verification.platform import DEFAULT_APP_NAME, DEFAULT_DOMAIN, DEFAULT_PUBLIC_BRAND_NAME, DEFAULT_SUPPORT_EMAIL
from verification.state_registry.adapters.colorado.client import ColoradoRegistryClient


def test_load_branding_config_defaults_to_capability_based_names():
    config = load_branding_config({})

    assert config.app_name == "verification-platform"
    assert config.public_brand_name == "VerifyForGood"
    assert config.support_email == "support@verifyforgood.com"
    assert config.domain == "verifyforgood.com"
    assert config.homepage_url() == "https://verifyforgood.com"
    assert config.user_agent() == "verification-platform/1.0"
    assert DEFAULT_APP_NAME == "verification-platform"
    assert DEFAULT_PUBLIC_BRAND_NAME == "VerifyForGood"
    assert DEFAULT_SUPPORT_EMAIL == "support@verifyforgood.com"
    assert DEFAULT_DOMAIN == "verifyforgood.com"


def test_load_branding_config_accepts_overrides_and_normalizes_user_agent():
    config = load_branding_config(
        {
            "APP_NAME": "Verify For Good Runtime",
            "PUBLIC_BRAND_NAME": "VerifyForGood",
            "SUPPORT_EMAIL": "help@verifyforgood.org",
            "DOMAIN": "https://app.verifyforgood.org/",
        }
    )

    assert config.app_name == "Verify For Good Runtime"
    assert config.public_brand_name == "VerifyForGood"
    assert config.support_email == "help@verifyforgood.org"
    assert config.domain == "app.verifyforgood.org"
    assert config.support_details()["homepage_url"] == "https://app.verifyforgood.org"
    assert config.user_agent() == "verify-for-good-runtime/1.0"
    assert default_runtime_user_agent({"APP_NAME": "Verification Engine"}) == "verification-engine/1.0"


def test_load_stripe_checkout_config_uses_public_brand_name_override():
    config = load_stripe_checkout_config(
        {
            "STRIPE_BILLING_ENABLED": "true",
            "STRIPE_SECRET_KEY": "sk_test_123",
            "STRIPE_PRICE_IDS": '{"growth":"price_growth"}',
            "PUBLIC_BRAND_NAME": "VerifyForGood",
        }
    )

    assert config.public_brand_name == "VerifyForGood"


def test_http_stripe_checkout_client_uses_configured_public_brand_name():
    client = HttpStripeCheckoutClient(secret_key="sk_test_123", public_brand_name="VerifyForGood")
    captured: dict[str, object] = {}

    def _fake_post_form(path, payload, *, idempotency_key, operation_name):
        captured["path"] = path
        captured["payload"] = payload
        captured["idempotency_key"] = idempotency_key
        captured["operation_name"] = operation_name
        return {"id": "cus_test_123"}

    client._post_form = _fake_post_form  # type: ignore[method-assign]

    customer_id = client.create_customer(account_id="acct_123", account_name="Example Org", ein="123456789")

    assert customer_id == "cus_test_123"
    assert captured["path"] == "/customers"
    assert captured["payload"]["description"] == "VerifyForGood account acct_123"


def test_state_registry_clients_default_to_neutral_runtime_user_agent():
    client = ColoradoRegistryClient()

    assert client._headers()["User-Agent"] == "verification-platform/1.0"


def test_runtime_source_files_no_longer_embed_legacy_brand_identifier():
    files = [
        "infrastructure/verification/billing/checkout.py",
        "infrastructure/verification/state_registry/adapters/colorado/client.py",
        "infrastructure/verification/state_registry/adapters/kentucky/client.py",
        "infrastructure/verification/state_registry/adapters/nevada/client.py",
        "infrastructure/verification/state_registry/adapters/new_york/client.py",
        "infrastructure/verification/state_registry/adapters/ohio/client.py",
        "infrastructure/verification/state_registry/adapters/south_dakota/client.py",
        "infrastructure/verification/state_registry/adapters/utah/client.py",
    ]

    for relative_path in files:
        content = Path(relative_path).read_text(encoding="utf-8")
        assert "CharityStatusAPI" not in content


def test_infrastructure_wires_runtime_branding_configuration():
    variables_tf = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    api_ecs_tf = Path("infrastructure/aws_api_ecs.tf").read_text(encoding="utf-8")
    worker_ecs_tf = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    shared_example = Path("infrastructure/terraform.shared.tfvars.example").read_text(encoding="utf-8")
    tfvars_example = Path("infrastructure/terraform.tfvars.example").read_text(encoding="utf-8")

    assert 'variable "app_name"' in variables_tf
    assert 'variable "public_brand_name"' in variables_tf
    assert 'variable "support_email"' in variables_tf
    assert 'variable "domain"' in variables_tf
    assert "APP_NAME" in api_ecs_tf or "APP_NAME" in worker_ecs_tf
    assert "PUBLIC_BRAND_NAME" in api_ecs_tf
    assert "SUPPORT_EMAIL" in api_ecs_tf or "SUPPORT_EMAIL" in worker_ecs_tf
    assert "DOMAIN" in api_ecs_tf or "DOMAIN" in worker_ecs_tf
    assert "APP_NAME=verification-platform" in readme
    assert "PUBLIC_BRAND_NAME=VerifyForGood" in readme
    assert "SUPPORT_EMAIL=support@verifyforgood.com" in readme
    assert "DOMAIN=verifyforgood.com" in readme
    assert 'base_name            = "verification-platform"' in shared_example
    assert 'root_domain_name          = "verification.example.com"' in shared_example
    assert 'base_name                 = "verification-platform"' in tfvars_example
    assert 'root_domain_name           = "verification.example.com"' in tfvars_example

