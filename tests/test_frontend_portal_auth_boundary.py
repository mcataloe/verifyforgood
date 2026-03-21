from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_ROOT = ROOT / "frontend" / "portal"


def test_portal_auth_boundary_files_exist():
    assert (PORTAL_ROOT / "src" / "auth" / "portalAuthClient.ts").exists()
    assert (PORTAL_ROOT / "src" / "auth" / "usePortalAuth.ts").exists()
    assert (PORTAL_ROOT / "src" / "components" / "PortalAuthLayout.tsx").exists()
    assert (PORTAL_ROOT / "src" / "pages" / "PortalSignInPage.tsx").exists()


def test_portal_routes_define_public_sign_in_and_protected_areas():
    portal_routes = (PORTAL_ROOT / "src" / "app" / "portalRoutes.ts").read_text(
        encoding="utf-8"
    )

    assert 'key: "sign-in"' in portal_routes
    assert 'access: "public"' in portal_routes
    assert 'access: "protected"' in portal_routes
    assert "rememberPortalReturnTo" in portal_routes
    assert "consumePortalReturnTo" in portal_routes


def test_portal_app_uses_auth_boundary_before_rendering_protected_layout():
    portal_app = (PORTAL_ROOT / "src" / "app" / "PortalApp.tsx").read_text(
        encoding="utf-8"
    )

    assert "usePortalAuth" in portal_app
    assert "PortalAuthLayout" in portal_app
    assert "PortalSignInPage" in portal_app
    assert 'auth.status !== "authenticated"' in portal_app
    assert "portalProtectedRoutes" in portal_app


def test_portal_readme_documents_auth_boundary_and_future_evolution():
    readme = (PORTAL_ROOT / "README.md").read_text(encoding="utf-8").lower()
    frontend_readme = (ROOT / "frontend" / "README.md").read_text(
        encoding="utf-8"
    ).lower()

    assert "auth boundary" in readme
    assert "sign-in" in readme
    assert "mock browser session" in readme
    assert "oauth/token" in readme
    assert "public route" in readme
    assert "protected routes" in readme

    assert "public versus protected surfaces" in frontend_readme
    assert "marketing/" in frontend_readme
    assert "docs/" in frontend_readme
    assert "portal/" in frontend_readme
