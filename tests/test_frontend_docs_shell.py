from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "frontend" / "docs"


def test_docs_shell_has_expected_source_structure():
    assert (DOCS_ROOT / "src" / "app" / "DocsSite.tsx").exists()
    assert (DOCS_ROOT / "src" / "app" / "docsRoutes.ts").exists()
    assert (DOCS_ROOT / "src" / "app" / "docsEndpoints.ts").exists()
    assert (DOCS_ROOT / "src" / "components" / "DocsLayout.tsx").exists()
    assert (DOCS_ROOT / "src" / "pages" / "GettingStartedPage.tsx").exists()
    assert (DOCS_ROOT / "src" / "pages" / "ProductOverviewPage.tsx").exists()
    assert (DOCS_ROOT / "src" / "pages" / "ApiUsagePage.tsx").exists()
    assert (DOCS_ROOT / "src" / "pages" / "IntegrationsPage.tsx").exists()
    assert (DOCS_ROOT / "src" / "pages" / "FaqPage.tsx").exists()


def test_docs_package_depends_on_intended_shared_foundations_only():
    manifest = json.loads((DOCS_ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = manifest.get("dependencies", {})

    assert "@charity-status/shared-ui" in dependencies
    assert "@charity-status/shared-api" in dependencies
    assert "@charity-status/shared-config" in dependencies
    assert "@charity-status/shared-types" in dependencies
    assert "@charity-status/portal" not in dependencies
    assert "@charity-status/marketing" not in dependencies


def test_docs_readme_documents_structure_and_extension_guidance():
    readme = (DOCS_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "getting started" in readme
    assert "product overview" in readme
    assert "api usage" in readme
    assert "integrations" in readme
    assert "faq" in readme
    assert "markdown" in readme
    assert "cms" in readme
