"""Backend-owned ingest-task runtime package."""

RUNTIME_NAME = "ingest_task"
CURRENT_COMPATIBILITY_SOURCES = (
    "infrastructure.lambda_ingest.handler",
    "infrastructure.lambda_form990.handler",
    "infrastructure.lambda_form990_orchestrator.handler",
    "infrastructure.lambda_form990_worker.handler",
    "infrastructure.lambda_monthly_ingest_staging.handler",
    "infrastructure.monthly_ingest_worker.main",
)
CANONICAL_LOCAL_ENTRYPOINT = "python -m charity_status_backend.ingest_task.cli.monthly_ingest_task"

__all__ = [
    "RUNTIME_NAME",
    "CURRENT_COMPATIBILITY_SOURCES",
    "CANONICAL_LOCAL_ENTRYPOINT",
]

