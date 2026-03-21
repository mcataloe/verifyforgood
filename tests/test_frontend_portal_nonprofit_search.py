from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_ROOT = ROOT / "frontend" / "portal"


def test_portal_nonprofit_search_files_exist():
    assert (PORTAL_ROOT / "src" / "nonprofits" / "nonprofitSearch.ts").exists()
    assert (
        PORTAL_ROOT / "src" / "nonprofits" / "usePortalNonprofitSearch.ts"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "nonprofits" / "NonprofitSearchPanel.tsx"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "nonprofits" / "nonprofitSearch.test.ts"
    ).exists()
    assert (
        PORTAL_ROOT / "src" / "nonprofits" / "NonprofitSearchPanel.test.tsx"
    ).exists()


def test_dashboard_and_readme_reference_nonprofit_search():
    readme = (PORTAL_ROOT / "README.md").read_text(encoding="utf-8").lower()
    dashboard = (
        PORTAL_ROOT / "src" / "pages" / "DashboardPage.tsx"
    ).read_text(encoding="utf-8").lower()

    assert "nonprofit search" in readme
    assert "get /v1/nonprofit/{ein}" in readme
    assert "get /v1/nonprofits/search" in readme
    assert "get /v1/nonprofit/{ein}/filings" in readme
    assert "nonprofitsearchpanel" in dashboard
    assert "nonprofitlookup" in dashboard
