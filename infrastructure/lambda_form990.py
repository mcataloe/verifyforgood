"""Compatibility shim for the backend-owned Form 990 runtime."""

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


_runtime = importlib.import_module("charity_status_backend.ingest_task.form990.runtime")
_runtime = importlib.reload(_runtime)


_runtime.__name__ = __name__
_runtime.__package__ = __package__
sys.modules[__name__] = _runtime
