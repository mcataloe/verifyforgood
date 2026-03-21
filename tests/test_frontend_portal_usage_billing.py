from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_ROOT = ROOT / "frontend" / "portal"


def test_portal_usage_billing_files_exist():
    assert (PORTAL_ROOT / "src" / "billing" / "portalUsageBilling.ts").exists()
    assert (PORTAL_ROOT / "src" / "billing" / "usePortalUsageBilling.ts").exists()
    assert (PORTAL_ROOT / "src" / "billing" / "UsageBillingPanel.tsx").exists()
    assert (
        PORTAL_ROOT / "src" / "billing" / "portalUsageBilling.test.ts"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "billing" / "UsageBillingPanel.test.tsx"
    ).exists()


def test_portal_usage_billing_readme_mentions_backend_and_mock_boundaries():
    readme = (PORTAL_ROOT / "README.md").read_text(encoding="utf-8").lower()
    billing_page = (
        PORTAL_ROOT / "src" / "pages" / "BillingPage.tsx"
    ).read_text(encoding="utf-8").lower()

    assert "usage and billing visibility" in readme
    assert "get /v1/organization/billing/subscription" in readme
    assert "customer-facing usage visibility endpoint" in readme
    assert "usagebillingpanel" in billing_page
