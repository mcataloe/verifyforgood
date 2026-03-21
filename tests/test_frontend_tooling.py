from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frontend_tooling_files_exist():
    assert (FRONTEND_ROOT / "eslint.config.js").exists()
    assert (FRONTEND_ROOT / ".prettierrc.json").exists()
    assert (FRONTEND_ROOT / ".prettierignore").exists()
    assert (FRONTEND_ROOT / "vitest.config.ts").exists()
    assert (FRONTEND_ROOT / "vitest.setup.ts").exists()
    assert (FRONTEND_ROOT / "tsconfig.tooling.json").exists()


def test_workspace_manifest_defines_tooling_scripts_and_dependencies():
    manifest = _load_json(FRONTEND_ROOT / "package.json")

    scripts = manifest["scripts"]
    assert "format" in scripts
    assert "format:check" in scripts
    assert "lint" in scripts
    assert "test" in scripts
    assert "test:watch" in scripts
    assert "typecheck" in scripts
    assert "typecheck:packages" in scripts
    assert "typecheck:tooling" in scripts

    dev_dependencies = manifest["devDependencies"]
    assert "eslint" in dev_dependencies
    assert "prettier" in dev_dependencies
    assert "vitest" in dev_dependencies
    assert "@testing-library/react" in dev_dependencies


def test_app_and_shared_package_manifests_expose_consistent_tooling_scripts():
    marketing = _load_json(FRONTEND_ROOT / "marketing" / "package.json")
    portal = _load_json(FRONTEND_ROOT / "portal" / "package.json")
    docs = _load_json(FRONTEND_ROOT / "docs" / "package.json")
    shared_api = _load_json(FRONTEND_ROOT / "shared" / "api" / "package.json")
    shared_config = _load_json(FRONTEND_ROOT / "shared" / "config" / "package.json")
    shared_types = _load_json(FRONTEND_ROOT / "shared" / "types" / "package.json")
    shared_ui = _load_json(FRONTEND_ROOT / "shared" / "ui" / "package.json")
    shared_utils = _load_json(FRONTEND_ROOT / "shared" / "utils" / "package.json")

    for manifest in [marketing, portal, docs]:
        assert "dev" in manifest["scripts"]
        assert "build" in manifest["scripts"]
        assert "lint" in manifest["scripts"]
        assert "test" in manifest["scripts"]
        assert "typecheck" in manifest["scripts"]

    for manifest in [shared_api, shared_config, shared_ui, shared_utils]:
        assert "lint" in manifest["scripts"]
        assert "test" in manifest["scripts"]
        assert "typecheck" in manifest["scripts"]

    assert "lint" in shared_types["scripts"]
    assert "typecheck" in shared_types["scripts"]
    assert "test" not in shared_types["scripts"]


def test_frontend_docs_cover_tooling_and_extension_guidance():
    frontend_readme = (FRONTEND_ROOT / "README.md").read_text(encoding="utf-8").lower()
    marketing_readme = (FRONTEND_ROOT / "marketing" / "README.md").read_text(encoding="utf-8").lower()
    portal_readme = (FRONTEND_ROOT / "portal" / "README.md").read_text(encoding="utf-8").lower()
    docs_readme = (FRONTEND_ROOT / "docs" / "README.md").read_text(encoding="utf-8").lower()
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "npm run lint" in frontend_readme
    assert "npm run test" in frontend_readme
    assert "npm run format:check" in frontend_readme
    assert "adding apps and packages" in frontend_readme
    assert "eslint" in frontend_readme
    assert "vitest" in frontend_readme

    assert "npm run lint" in marketing_readme
    assert "npm run test" in marketing_readme
    assert "npm run lint" in portal_readme
    assert "npm run test" in portal_readme
    assert "npm run lint" in docs_readme
    assert "npm run test" in docs_readme

    assert "npm run lint" in root_readme
    assert "npm run test" in root_readme


def test_frontend_smoke_tests_exist_for_apps_and_shared_runtime_packages():
    assert (FRONTEND_ROOT / "marketing" / "src" / "app" / "MarketingSite.test.tsx").exists()
    assert (FRONTEND_ROOT / "portal" / "src" / "app" / "PortalApp.test.tsx").exists()
    assert (FRONTEND_ROOT / "portal" / "src" / "app" / "portalApiClient.test.ts").exists()
    assert (FRONTEND_ROOT / "portal" / "src" / "api-access" / "apiKeys.test.ts").exists()
    assert (
        FRONTEND_ROOT / "portal" / "src" / "api-access" / "ApiKeyManager.test.tsx"
    ).exists()
    assert (FRONTEND_ROOT / "docs" / "src" / "app" / "DocsSite.test.tsx").exists()
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "routes.test.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "api" / "src" / "request.test.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "config" / "src" / "index.test.ts").exists()
    assert (FRONTEND_ROOT / "shared" / "ui" / "src" / "index.test.tsx").exists()
    assert (FRONTEND_ROOT / "shared" / "utils" / "src" / "index.test.ts").exists()
