"""Local backend ingest-task entrypoint."""

from __future__ import annotations

from charity_status_backend.ingest_task.cli.monthly_ingest_task import main


if __name__ == "__main__":
    raise SystemExit(main())
