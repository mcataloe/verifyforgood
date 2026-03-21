from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"


def test_shared_api_client_files_and_tests_exist():
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "endpoints.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "request.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "routes.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "request.test.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "routes.test.ts").exists()
    assert (FRONTEND_ROOT / "portal" / "src" / "app" / "portalApiClient.test.ts").exists()


def test_shared_api_docs_describe_client_usage_and_boundaries():
    shared_api_readme = (
        FRONTEND_ROOT / "shared" / "api" / "README.md"
    ).read_text(encoding="utf-8").lower()
    frontend_readme = (FRONTEND_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "requestenvelope" in shared_api_readme
    assert "requestdata" in shared_api_readme
    assert "createapiclient" in shared_api_readme
    assert "headersprovider" in shared_api_readme
    assert "what belongs here" in shared_api_readme
    assert "what stays app-local" in shared_api_readme
    assert "@charity-status/shared-api" in frontend_readme
    assert "all backend http interaction should flow through" in frontend_readme


def test_app_endpoint_maps_use_shared_endpoint_catalog_without_raw_paths():
    marketing_endpoints = (
        FRONTEND_ROOT / "marketing" / "src" / "app" / "marketingEndpoints.ts"
    ).read_text(encoding="utf-8")
    docs_endpoints = (
        FRONTEND_ROOT / "docs" / "src" / "app" / "docsEndpoints.ts"
    ).read_text(encoding="utf-8")
    portal_endpoints = (
        FRONTEND_ROOT / "portal" / "src" / "app" / "portalEndpoints.ts"
    ).read_text(encoding="utf-8")

    for source in [marketing_endpoints, docs_endpoints, portal_endpoints]:
        assert "apiEndpoints." in source

    duplicated_paths = [
        "/oauth/token",
        "/organization/settings",
        "/organization/billing/subscription",
        "/organization/billing/checkout-session",
        "/organization/billing/plan-change",
        "/organization/billing/portal-session",
        "/nonprofits/search",
        "/nonprofit/{ein}",
        "/nonprofit/{ein}/filings",
        "/nonprofits/{ein}/sources",
        "/verify",
        "/verify/batch",
    ]

    for source in [marketing_endpoints, docs_endpoints, portal_endpoints]:
        for duplicated_path in duplicated_paths:
            assert duplicated_path not in source
