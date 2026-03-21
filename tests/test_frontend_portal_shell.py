from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_ROOT = ROOT / "frontend" / "portal"


def test_portal_shell_has_expected_source_structure():
    assert (PORTAL_ROOT / "src" / "app" / "PortalApp.tsx").exists()
    assert (PORTAL_ROOT / "src" / "app" / "portalApiClient.ts").exists()
    assert (PORTAL_ROOT / "src" / "app" / "portalRoutes.ts").exists()
    assert (PORTAL_ROOT / "src" / "app" / "portalSession.ts").exists()
    assert (PORTAL_ROOT / "src" / "app" / "portalEndpoints.ts").exists()
    assert (PORTAL_ROOT / "src" / "nonprofits" / "NonprofitSearchPanel.tsx").exists()
    assert (PORTAL_ROOT / "src" / "nonprofits" / "nonprofitSearch.ts").exists()
    assert (
        PORTAL_ROOT / "src" / "organization" / "PortalOrganizationProvider.tsx"
    ).exists()
    assert (PORTAL_ROOT / "src" / "organization" / "portalOrganization.ts").exists()
    assert (PORTAL_ROOT / "src" / "components" / "PortalLayout.tsx").exists()
    assert (
        PORTAL_ROOT / "src" / "components" / "feedback" / "PortalNotice.tsx"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "components" / "feedback" / "PortalLoadingState.tsx"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "components" / "feedback" / "PortalErrorState.tsx"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "components" / "feedback" / "PortalEmptyState.tsx"
    ).exists()
    assert (PORTAL_ROOT / "src" / "pages" / "DashboardPage.tsx").exists()
    assert (PORTAL_ROOT / "src" / "pages" / "WorkspacePage.tsx").exists()
    assert (PORTAL_ROOT / "src" / "pages" / "ApiAccessPage.tsx").exists()
    assert (PORTAL_ROOT / "src" / "pages" / "BillingPage.tsx").exists()
    assert (PORTAL_ROOT / "src" / "pages" / "SettingsPage.tsx").exists()
    assert (PORTAL_ROOT / "src" / "billing" / "portalUsageBilling.ts").exists()
    assert (PORTAL_ROOT / "src" / "billing" / "usePortalUsageBilling.ts").exists()
    assert (PORTAL_ROOT / "src" / "billing" / "UsageBillingPanel.tsx").exists()


def test_portal_package_depends_on_intended_shared_foundations():
    manifest = json.loads((PORTAL_ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = manifest.get("dependencies", {})

    assert "@charity-status/shared-ui" in dependencies
    assert "@charity-status/shared-api" in dependencies
    assert "@charity-status/shared-config" in dependencies
    assert "@charity-status/shared-types" in dependencies


def test_portal_readme_documents_shell_and_extension_guidance():
    readme = (PORTAL_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "dashboard" in readme
    assert "workspace" in readme
    assert "api access" in readme
    assert "usage and billing" in readme
    assert "settings" in readme
    assert "auth" in readme
    assert "nonprofit search" in readme
    assert "usage and billing visibility" in readme
    assert "feedback" in readme
    assert "organization scope" in readme
    assert "extending the portal" in readme
