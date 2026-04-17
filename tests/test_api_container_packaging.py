from __future__ import annotations

from pathlib import Path


def test_backend_runtime_dockerfiles_exist():
    assert Path("backend/api/Dockerfile").exists()
    assert Path("backend/worker/Dockerfile").exists()
    assert Path("backend/ingest-task/Dockerfile").exists()


def test_api_dockerfile_uses_asgi_entrypoint():
    dockerfile = Path("backend/api/Dockerfile").read_text(encoding="utf-8")

    assert (
        "PYTHONPATH=/app:/app/infrastructure:/app/private-platform/src:/app/backend/api/src:/app/backend/shared/src"
        in dockerfile
    )
    assert "uvicorn" in dockerfile
    assert "charity_status_backend.api.app:app" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "private-platform/src" in dockerfile
    assert "backend/api/src" in dockerfile
    assert "backend/shared/src" in dockerfile


def test_worker_and_ingest_dockerfiles_use_backend_runtime_entrypoints():
    worker = Path("backend/worker/Dockerfile").read_text(encoding="utf-8")
    ingest = Path("backend/ingest-task/Dockerfile").read_text(encoding="utf-8")

    assert 'CMD ["python", "-m", "charity_status_backend.worker.entrypoint"]' in worker
    assert "backend/worker/src" in worker
    assert "backend/shared/src" in worker

    assert (
        'ENTRYPOINT ["python", "-m", "charity_status_backend.ingest_task.cli"]'
        in ingest
    )
    assert 'CMD ["monthly-worker"]' in ingest
    assert "backend/ingest-task/src" in ingest
    assert "backend/shared/src" in ingest
    assert "private-platform/src" in ingest


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
