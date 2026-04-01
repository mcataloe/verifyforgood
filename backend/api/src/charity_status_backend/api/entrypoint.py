"""Scaffold entrypoint for the future backend API runtime."""

from __future__ import annotations

from charity_status_backend.shared.cli import scaffold_only_message


def main() -> None:
    raise SystemExit(
        scaffold_only_message(
            runtime_name="api",
            current_source="infrastructure.lambda_query.handler",
            target_directory="backend/api/",
        )
    )


if __name__ == "__main__":
    main()
