from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETING_ROOT = ROOT / "frontend" / "marketing"


def test_marketing_shell_has_expected_source_structure():
    assert (MARKETING_ROOT / "src" / "app" / "MarketingSite.tsx").exists()
    assert (MARKETING_ROOT / "src" / "app" / "marketingRoutes.ts").exists()
    assert (MARKETING_ROOT / "src" / "app" / "marketingEndpoints.ts").exists()
    assert (MARKETING_ROOT / ".env.example").exists()
    assert (MARKETING_ROOT / "src" / "components" / "MarketingLayout.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "HomePage.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "ProductPage.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "PricingPage.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "TrustPage.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "DevelopersPage.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "ContactPage.tsx").exists()
    assert (MARKETING_ROOT / "src" / "pages" / "LoginPage.tsx").exists()


def test_marketing_package_depends_on_intended_shared_foundations():
    manifest = json.loads((MARKETING_ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = manifest.get("dependencies", {})

    assert "@charity-status/shared-ui" in dependencies
    assert "@charity-status/shared-api" in dependencies
    assert "@charity-status/shared-config" in dependencies
    assert "@charity-status/shared-types" in dependencies
    assert "@charity-status/portal" not in dependencies


def test_marketing_readme_documents_public_ia_and_boundaries():
    readme = (MARKETING_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "home" in readme
    assert "product" in readme
    assert "pricing" in readme
    assert "security and trust" in readme
    assert "developers" in readme
    assert "contact and demo" in readme
    assert "login entry point" in readme
    assert "portal" in readme
    assert "get /v1/plans" in readme
    assert "localhost:5174" in readme
