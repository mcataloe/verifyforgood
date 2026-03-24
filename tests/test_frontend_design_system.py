from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED_UI_ROOT = ROOT / "frontend" / "shared" / "ui"


def test_shared_ui_design_foundation_files_exist():
    assert (SHARED_UI_ROOT / "src" / "theme.css").exists()
    assert (SHARED_UI_ROOT / "src" / "layout.css").exists()
    assert (SHARED_UI_ROOT / "src" / "components.css").exists()
    assert (SHARED_UI_ROOT / "src" / "components" / "ThemeRoot.tsx").exists()
    assert (SHARED_UI_ROOT / "src" / "components" / "layout" / "Container.tsx").exists()
    assert (SHARED_UI_ROOT / "src" / "components" / "layout" / "Page.tsx").exists()
    assert (SHARED_UI_ROOT / "src" / "components" / "layout" / "Section.tsx").exists()
    assert (SHARED_UI_ROOT / "src" / "components" / "layout" / "Grid.tsx").exists()
    assert (SHARED_UI_ROOT / "src" / "components" / "layout" / "Inline.tsx").exists()


def test_design_tokens_cover_foundational_groups():
    theme_css = (SHARED_UI_ROOT / "src" / "theme.css").read_text(encoding="utf-8")

    assert "--vf-color-forest-950" in theme_css
    assert "--vf-space-4" in theme_css
    assert "--vf-font-sans" in theme_css
    assert "--vf-radius-sm" in theme_css
    assert "--vf-shadow-sm" in theme_css
    assert '[data-theme="inverse"]' in theme_css


def test_shared_ui_readme_documents_tokens_and_primitives():
    readme = (SHARED_UI_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "design tokens" in readme
    assert "container" in readme
    assert "page" in readme
    assert "section" in readme
    assert "grid" in readme
    assert "inline" in readme
    assert "what stays app-local" in readme


def test_apps_consume_shared_layout_primitives():
    marketing_layout = (ROOT / "frontend" / "marketing" / "src" / "components" / "MarketingLayout.tsx").read_text(encoding="utf-8")
    portal_layout = (ROOT / "frontend" / "portal" / "src" / "components" / "PortalLayout.tsx").read_text(encoding="utf-8")
    docs_layout = (ROOT / "frontend" / "docs" / "src" / "components" / "DocsLayout.tsx").read_text(encoding="utf-8")

    assert "Container" in marketing_layout
    assert "Inline" in marketing_layout
    assert "Section" in marketing_layout
    assert "Page" in marketing_layout
    assert "Inline" in portal_layout
    assert "ThemeRoot" in portal_layout
    assert "Page" in portal_layout
    assert "Page" in docs_layout
