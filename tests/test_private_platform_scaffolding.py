from __future__ import annotations

import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


def test_private_platform_service_area_packages_import():
    import charity_status_platform.admin_operations as admin_operations
    import charity_status_platform.billing_usage as billing_usage
    import charity_status_platform.customer_accounts as customer_accounts
    import charity_status_platform.identity_access as identity_access
    import charity_status_platform.notifications as notifications
    import charity_status_platform.runtime as runtime

    assert hasattr(identity_access, "authenticate_api_key")
    assert hasattr(identity_access, "ApiKeyAuthContextProvider")
    assert hasattr(identity_access, "IdentityProviderType")
    assert hasattr(identity_access, "IdentityProviderService")
    assert hasattr(identity_access, "LocalPasswordIdentityProviderService")
    assert hasattr(customer_accounts, "ControlPlaneService")
    assert hasattr(customer_accounts, "OrganizationIntegrationSettingsService")
    assert hasattr(billing_usage, "EntitlementService")
    assert hasattr(billing_usage, "enforce_quota_and_scope")
    assert hasattr(admin_operations, "S3RunStore")
    assert hasattr(runtime, "build_athena_client")
    assert notifications.__all__ == []


def test_private_platform_docs_define_service_areas():
    root_readme = (ROOT / "private-platform" / "README.md").read_text(encoding="utf-8")
    package_readme = (ROOT / "private-platform" / "src" / "charity_status_platform" / "README.md").read_text(encoding="utf-8")
    service_areas_doc = (ROOT / "docs" / "private-platform-service-areas.md").read_text(encoding="utf-8")

    assert "identity_access" in root_readme
    assert "billing_usage" in root_readme
    assert "public-core must not depend on private-platform" in root_readme

    assert "compatibility boundary first" in package_readme
    assert "customer_accounts/" in package_readme
    assert "notifications/" in package_readme

    assert "Identity Access" in service_areas_doc
    assert "Billing Usage" in service_areas_doc
    assert "must not depend on any `charity_status_platform` package" in service_areas_doc


def test_split_plan_defines_private_service_areas():
    payload = json.loads((ROOT / "split-plan.json").read_text(encoding="utf-8"))
    service_areas = payload["private_repo"].get("service_areas", {})

    assert set(service_areas) == {
        "identity_access",
        "customer_accounts",
        "billing_usage",
        "admin_operations",
        "runtime",
        "notifications",
    }
    assert "infrastructure/charity_status/billing/" in service_areas["billing_usage"]
    assert "infrastructure/charity_status/control_plane/" in service_areas["customer_accounts"]
