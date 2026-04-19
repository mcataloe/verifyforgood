"""Compatibility CLI surface for local ingest-task execution."""

from __future__ import annotations

import sys

from verification_backend.shared.local_dev import load_backend_local_env


def main(argv: list[str] | None = None) -> int:
    load_backend_local_env()
    from verification_backend.ingest_task.cli import main as backend_main

    return backend_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

