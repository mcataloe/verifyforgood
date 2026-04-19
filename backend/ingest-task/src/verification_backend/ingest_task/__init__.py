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
    "infrastructure.eo_bmf_ingest_worker.handler",
    "infrastructure.monthly_ingest_worker.main",
    "infrastructure.nonprofit_ingest_persistence.build_form990_nonprofit_persistence_service",
)
CANONICAL_LOCAL_ENTRYPOINT = "python -m verification_backend.ingest_task.cli.monthly_ingest_task"

FORM990_WORKSPACE_MODULES = (
    "verification_backend.ingest_task.discovery",
    "verification_backend.ingest_task.metadata",
    "verification_backend.ingest_task.download",
    "verification_backend.ingest_task.extract",
    "verification_backend.ingest_task.hashing",
    "verification_backend.ingest_task.parse",
    "verification_backend.ingest_task.persist",
    "verification_backend.ingest_task.cleanup",
    "verification_backend.ingest_task.orchestration",
)

__all__ = [
    "RUNTIME_NAME",
    "CURRENT_COMPATIBILITY_SOURCES",
    "CANONICAL_LOCAL_ENTRYPOINT",
    "FORM990_WORKSPACE_MODULES",
]

