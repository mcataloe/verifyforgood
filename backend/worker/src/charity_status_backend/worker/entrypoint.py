"""Scaffold entrypoint for the future backend worker runtime."""

from __future__ import annotations

from charity_status_backend.shared.cli import scaffold_only_message


def main() -> None:
    raise SystemExit(
        scaffold_only_message(
            runtime_name="worker",
            current_source="infrastructure.lambda_refresh.handler",
            target_directory="backend/worker/",
        )
    )


if __name__ == "__main__":
    main()
