"""Entry module for backend ingest-task local execution."""

from __future__ import annotations

from charity_status_backend.shared.local_dev import load_backend_local_env
from .cli import main

if __name__ == "__main__":
    load_backend_local_env()
    raise SystemExit(main())
