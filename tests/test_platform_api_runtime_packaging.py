from __future__ import annotations

import importlib
from pathlib import Path


def test_platform_api_runtime_package_imports_successfully():
    module = importlib.import_module("verification.backend.platform.api")

    assert module.RUNTIME_NAME == "platform-api"
    assert callable(module.create_app)
    assert callable(module.handle_api_event)


def test_platform_api_runtime_host_is_documented_and_backend_owned():
    readme = Path("backend/platform-api/README.md").read_text(encoding="utf-8")
    source = Path("backend/platform-api/src/verification/backend/platform/api/__init__.py").read_text(
        encoding="utf-8"
    )

    assert "Backend Platform API Runtime" in readme
    assert "platform/control-plane HTTP runtime host" in readme
    assert "verification.backend.platform.api.app:app" in readme
    assert 'RUNTIME_NAME = "platform-api"' in source


def test_platform_api_routes_are_split_from_customer_api_routes():
    transport = importlib.import_module("verification.backend.customer.api.transport")

    customer_resources = {spec.resource for spec in transport.CUSTOMER_API_ROUTE_SPECS}
    platform_resources = {spec.resource for spec in transport.PLATFORM_API_ROUTE_SPECS}

    assert customer_resources.isdisjoint(platform_resources)
    assert "/v1/admin/accounts" in platform_resources
    assert "/v1/ops/form990/runs" in platform_resources
    assert "/v1/oauth/token" in platform_resources
    assert "/v1/webhooks/stripe" in platform_resources
    assert "/v1/nonprofits/search" in customer_resources
    assert "/v1/organization/billing/subscription" in customer_resources
