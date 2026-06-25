"""Entry module for backend federal ingest local execution."""

from __future__ import annotations

from verification.backend.shared.local_dev import load_backend_local_env


def main(argv: list[str] | None = None) -> int:
    load_backend_local_env()
    from .cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
