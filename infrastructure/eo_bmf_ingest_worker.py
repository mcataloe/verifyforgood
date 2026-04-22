"""Compatibility shim for the backend-owned EO/BMF ingest runtime."""

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


from verification_backend.ingest_task.eo_bmf_ecs_runtime import main as _backend_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return _backend_main(list(argv or []))


def handler(_event=None, _context=None) -> int:
    return _backend_main([])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

