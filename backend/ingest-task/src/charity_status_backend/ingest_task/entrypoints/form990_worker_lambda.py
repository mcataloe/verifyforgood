"""Lambda-compatible entrypoint for the backend-owned Form 990 worker runtime."""

from charity_status_backend.ingest_task.orchestration.form990_worker_runtime import handler

__all__ = ["handler"]
