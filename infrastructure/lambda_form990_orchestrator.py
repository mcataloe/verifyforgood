"""Compatibility shim for the backend-owned Form 990 orchestrator entrypoint."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_INGEST_SRC = ROOT / "backend" / "ingest-task" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

for path in (BACKEND_INGEST_SRC, BACKEND_SHARED_SRC, PRIVATE_PLATFORM_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


_orchestrator = importlib.import_module("charity_status_backend.ingest_task.form990.orchestrator")
_orchestrator = importlib.reload(_orchestrator)

handler = _orchestrator.handler

__all__ = ["handler"]
