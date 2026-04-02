"""Compatibility shim for the backend-owned monthly ingest task CLI."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_INGEST_SRC = ROOT / "backend" / "ingest-task" / "src"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

for path in (BACKEND_INGEST_SRC, PRIVATE_PLATFORM_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from charity_status_backend.ingest_task.cli.monthly_ingest_task import main  # noqa: E402,F401


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
