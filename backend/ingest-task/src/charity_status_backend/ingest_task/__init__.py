"""Backend-owned ingest-task runtime package."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[5]
INFRASTRUCTURE_SRC = ROOT / "infrastructure"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

for path in (INFRASTRUCTURE_SRC, PRIVATE_PLATFORM_SRC, BACKEND_SHARED_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

RUNTIME_NAME = "ingest_task"
CURRENT_COMPATIBILITY_SOURCES = (
    "infrastructure.lambda_ingest.handler",
    "infrastructure.lambda_form990.handler",
    "infrastructure.lambda_form990_orchestrator.handler",
    "infrastructure.lambda_form990_worker.handler",
)

__all__ = [
    "RUNTIME_NAME",
    "CURRENT_COMPATIBILITY_SOURCES",
]
