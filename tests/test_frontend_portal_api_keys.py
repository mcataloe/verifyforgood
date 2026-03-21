from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_ROOT = ROOT / "frontend" / "portal"


def test_portal_api_key_files_exist():
    assert (PORTAL_ROOT / "src" / "api-access" / "apiKeys.ts").exists()
    assert (PORTAL_ROOT / "src" / "api-access" / "usePortalApiKeys.ts").exists()
    assert (PORTAL_ROOT / "src" / "api-access" / "ApiKeyManager.tsx").exists()
    assert (PORTAL_ROOT / "src" / "api-access" / "apiKeys.test.ts").exists()
    assert (
        PORTAL_ROOT / "src" / "api-access" / "ApiKeyManager.test.tsx"
    ).exists()


def test_portal_api_key_docs_explain_mock_backend_gap_and_secret_handling():
    readme = (PORTAL_ROOT / "README.md").read_text(encoding="utf-8").lower()
    api_key_manager = (
        PORTAL_ROOT / "src" / "api-access" / "ApiKeyManager.tsx"
    ).read_text(encoding="utf-8").lower()

    assert "api key management" in readme
    assert "shown once" in readme
    assert "admin control-plane routes" in readme
    assert "customer-facing api credential endpoints" in readme
    assert "one-time secret" in api_key_manager or "shown once" in api_key_manager
