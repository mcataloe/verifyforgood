"""Compatibility shim for backend-owned nonprofit ingest persistence."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_INGEST_SRC = ROOT / "backend" / "ingest-task" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

for path in (BACKEND_INGEST_SRC, BACKEND_SHARED_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from verification_backend.ingest_task.persistence import build_form990_nonprofit_persistence_service  # noqa: E402


__all__ = ["build_form990_nonprofit_persistence_service"]

