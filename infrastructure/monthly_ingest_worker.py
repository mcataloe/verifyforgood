"""Compatibility shim for the backend-owned monthly ECS worker runtime."""

from __future__ import annotations

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


from charity_status_backend.ingest_task.monthly.worker import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
