"""Compatibility shim for the backend-owned monthly staging runtime."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_INGEST_SRC = ROOT / "backend" / "ingest-task" / "src"

path_str = str(BACKEND_INGEST_SRC)
if path_str not in sys.path:
    sys.path.insert(0, path_str)


from charity_status_backend.ingest_task.entrypoints.monthly_staging_lambda import handler  # noqa: E402,F401


__all__ = ["handler"]
