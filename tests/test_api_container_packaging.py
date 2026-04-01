from __future__ import annotations

from pathlib import Path


def test_api_dockerfile_uses_asgi_entrypoint():
    dockerfile = Path("infrastructure/Dockerfile.api").read_text(encoding="utf-8")

    assert "uvicorn" in dockerfile
    assert "charity_status_backend.api.app:app" in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert "private-platform/src" in dockerfile
    assert "backend/api/src" in dockerfile
    assert "backend/shared/src" in dockerfile


def test_api_requirements_and_dockerignore_exist():
    requirements = Path("infrastructure/requirements-api.txt").read_text(encoding="utf-8")
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert "-r requirements.txt" in requirements
    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "infrastructure/build" in dockerignore
    assert ".terraform" in dockerignore
