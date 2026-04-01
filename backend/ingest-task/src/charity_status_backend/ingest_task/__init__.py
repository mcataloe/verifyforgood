"""Backend ingest-task runtime scaffold."""

RUNTIME_NAME = "ingest_task"
CURRENT_COMPATIBILITY_SOURCES = (
    "infrastructure.lambda_ingest.handler",
    "infrastructure.lambda_form990.handler",
    "infrastructure.lambda_form990_orchestrator.handler",
    "infrastructure.lambda_form990_worker.handler",
)

