from __future__ import annotations

from pathlib import Path


def test_backend_runtime_dockerfiles_exist():
    assert Path("backend/customer-api/Dockerfile").exists()
    assert Path("backend/platform-api/Dockerfile").exists()
    assert Path("backend/worker/Dockerfile").exists()
    assert Path("backend/ingest/federal/Dockerfile").exists()


def test_api_dockerfile_uses_asgi_entrypoint():
    dockerfile = Path("backend/customer-api/Dockerfile").read_text(encoding="utf-8")
    platform_dockerfile = Path("backend/platform-api/Dockerfile").read_text(encoding="utf-8")
    legacy_source_root = "/app/" + "private-" + "platform/src"

    assert (
        "PYTHONPATH=/app:/app/backend/customer-api/src:/app/backend/shared/src"
        in dockerfile
    )
    assert "uvicorn" in dockerfile
    assert "verification.backend.customer.api.app:app" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert legacy_source_root not in dockerfile
    assert "backend/customer-api/src" in dockerfile
    assert "backend/shared/src" in dockerfile
    assert "COPY infrastructure /app/infrastructure" not in dockerfile

    assert (
        "PYTHONPATH=/app:/app/backend/customer-api/src:/app/backend/platform-api/src:/app/backend/shared/src"
        in platform_dockerfile
    )
    assert "verification.backend.platform.api.app:app" in platform_dockerfile
    assert "backend/platform-api/src" in platform_dockerfile
    assert "backend/customer-api/src" in platform_dockerfile
    assert "backend/shared/src" in platform_dockerfile
    assert "COPY infrastructure /app/infrastructure" not in platform_dockerfile


def test_worker_and_ingest_dockerfiles_use_backend_runtime_entrypoints():
    worker = Path("backend/worker/Dockerfile").read_text(encoding="utf-8")
    ingest = Path("backend/ingest/federal/Dockerfile").read_text(encoding="utf-8")
    legacy_source_root = "private-" + "platform/src"

    assert 'CMD ["python", "-m", "verification.backend.worker.entrypoint"]' in worker
    assert "backend/worker/src" in worker
    assert "backend/shared/src" in worker

    assert (
        'ENTRYPOINT ["python", "-m", "verification.backend.ingest.federal.cli"]'
        in ingest
    )
    assert 'CMD ["monthly-worker"]' in ingest
    assert "backend/ingest/federal/src" in ingest
    assert "backend/shared/src" in ingest
    assert legacy_source_root not in ingest
    assert "PYTHONPATH=/app:/app/backend/ingest/federal/src:/app/backend/shared/src" in ingest
    assert "COPY infrastructure /app/infrastructure" not in ingest


def test_requirements_and_dockerignore_exist():
    requirements = Path("infrastructure/requirements-api.txt").read_text(
        encoding="utf-8"
    )
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert "-r requirements.txt" in requirements
    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "infrastructure/build" in dockerignore
    assert ".terraform" in dockerignore
    assert ".env" in dockerignore
    assert "frontend/**/dist" in dockerignore

