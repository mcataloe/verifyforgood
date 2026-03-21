from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_ROOT = ROOT / "frontend" / "portal"


def test_portal_organization_context_files_exist():
    assert (PORTAL_ROOT / "src" / "app" / "portalApiClient.ts").exists()
    assert (PORTAL_ROOT / "src" / "organization" / "portalOrganization.ts").exists()
    assert (
        PORTAL_ROOT / "src" / "organization" / "PortalOrganizationProvider.tsx"
    ).exists()
    assert (
        PORTAL_ROOT
        / "src"
        / "organization"
        / "PortalOrganizationProvider.test.tsx"
    ).exists()


def test_portal_readme_and_shell_reference_organization_scope():
    readme = (PORTAL_ROOT / "README.md").read_text(encoding="utf-8").lower()
    portal_app = (PORTAL_ROOT / "src" / "app" / "PortalApp.tsx").read_text(
        encoding="utf-8"
    )
    portal_layout = (
        PORTAL_ROOT / "src" / "components" / "PortalLayout.tsx"
    ).read_text(encoding="utf-8")

    assert "organization scope" in readme
    assert "src/organization/" in readme
    assert "get /v1/organization/settings" in readme
    assert "PortalOrganizationProvider" in portal_app
    assert "usePortalOrganization" in portal_layout
