from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "frontend"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frontend_workspace_roots_exist():
    assert FRONTEND_ROOT.exists()
    assert (FRONTEND_ROOT / "package.json").exists()
    assert (FRONTEND_ROOT / "tsconfig.base.json").exists()
    assert (FRONTEND_ROOT / "README.md").exists()

    assert (FRONTEND_ROOT / "marketing").exists()
    assert (FRONTEND_ROOT / "portal").exists()
    assert (FRONTEND_ROOT / "shared" / "ui").exists()
    assert (FRONTEND_ROOT / "shared" / "types").exists()
    assert (FRONTEND_ROOT / "shared" / "utils").exists()
    assert (FRONTEND_ROOT / "shared" / "config").exists()
    assert (FRONTEND_ROOT / "docs").exists()


def test_workspace_manifest_defines_expected_workspaces_and_scripts():
    manifest = _load_json(FRONTEND_ROOT / "package.json")

    assert manifest["private"] is True
    assert manifest["workspaces"] == ["marketing", "portal", "shared/*"]

    scripts = manifest["scripts"]
    assert "dev:marketing" in scripts
    assert "dev:portal" in scripts
    assert "build" in scripts
    assert "typecheck" in scripts


def test_frontend_package_manifests_define_expected_names_and_boundaries():
    marketing = _load_json(FRONTEND_ROOT / "marketing" / "package.json")
    portal = _load_json(FRONTEND_ROOT / "portal" / "package.json")
    shared_ui = _load_json(FRONTEND_ROOT / "shared" / "ui" / "package.json")
    shared_types = _load_json(FRONTEND_ROOT / "shared" / "types" / "package.json")
    shared_utils = _load_json(FRONTEND_ROOT / "shared" / "utils" / "package.json")

    assert marketing["name"] == "@charity-status/marketing"
    assert portal["name"] == "@charity-status/portal"
    assert shared_ui["name"] == "@charity-status/shared-ui"
    assert shared_types["name"] == "@charity-status/shared-types"
    assert shared_utils["name"] == "@charity-status/shared-utils"

    marketing_deps = set(marketing.get("dependencies", {}))
    portal_deps = set(portal.get("dependencies", {}))

    assert "@charity-status/portal" not in marketing_deps
    assert "@charity-status/marketing" not in portal_deps
    assert "@charity-status/shared-ui" in marketing_deps
    assert "@charity-status/shared-ui" in portal_deps


def test_placeholder_only_directories_do_not_define_packages():
    assert (FRONTEND_ROOT / "docs" / "README.md").exists()
    assert not (FRONTEND_ROOT / "docs" / "package.json").exists()

    assert (FRONTEND_ROOT / "shared" / "config" / "README.md").exists()
    assert not (FRONTEND_ROOT / "shared" / "config" / "package.json").exists()


def test_frontend_and_root_docs_describe_boundaries():
    frontend_readme = (FRONTEND_ROOT / "README.md").read_text(encoding="utf-8")
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    normalized_frontend = frontend_readme.lower().replace("`", "")

    assert "marketing must not depend on portal" in normalized_frontend
    assert "portal must not depend on marketing" in normalized_frontend
    assert "docs/" in frontend_readme

    assert "Frontend Workspace" in root_readme
    assert "frontend/docs/" in root_readme
    assert "backend workflows remain unchanged" in root_readme.lower()
