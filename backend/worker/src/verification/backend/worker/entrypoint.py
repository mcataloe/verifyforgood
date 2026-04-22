"""Scaffold entrypoint for the future backend worker runtime."""

from __future__ import annotations

from verification.backend.shared.cli import scaffold_only_message
from verification.backend.shared.local_dev import load_backend_local_env


def main() -> None:
    load_backend_local_env()
    raise SystemExit(
        scaffold_only_message(
            runtime_name="worker",
            current_source="retired refresh lambda runtime",
            target_directory="backend/worker/",
        )
    )


if __name__ == "__main__":
    main()

