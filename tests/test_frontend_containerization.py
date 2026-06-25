from __future__ import annotations

from pathlib import Path


def test_frontend_runtime_dockerfiles_and_env_examples_exist():
    assert Path("frontend/marketing/Dockerfile").exists()
    assert Path("frontend/portal/Dockerfile").exists()
    assert Path("frontend/marketing/.env.example").exists()
    assert Path("frontend/portal/.env.example").exists()


def test_marketing_containerization_wires_platform_handoff():
    marketing_env = Path("frontend/marketing/.env.example").read_text(encoding="utf-8")
    marketing_site = Path("frontend/marketing/src/app/MarketingSite.tsx").read_text(encoding="utf-8")
    shared_config = Path("frontend/shared/config/src/index.ts").read_text(encoding="utf-8")

    assert "VITE_PLATFORM_BASE_URL" in marketing_env
    assert "platformLoginUrl" in marketing_site
    assert "VITE_PLATFORM_BASE_URL" in shared_config


def test_frontend_readmes_document_platform_app_naming_and_compose_hosts():
    frontend_readme = Path("frontend/README.md").read_text(encoding="utf-8")
    marketing_readme = Path("frontend/marketing/README.md").read_text(encoding="utf-8")
    portal_readme = Path("frontend/portal/README.md").read_text(encoding="utf-8")

    assert "platform.verifyforgood.com" in frontend_readme
    assert "platformapi.verifyforgood.com" in frontend_readme
    assert "VITE_PLATFORM_BASE_URL" in marketing_readme
    assert "http://localhost:5174" in marketing_readme
    assert "platform app surface" in portal_readme
    assert "http://localhost:3953" in portal_readme
