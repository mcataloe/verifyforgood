"""Scaffold entrypoint for the future backend ingest-task runtime."""

from __future__ import annotations

from charity_status_backend.shared.cli import scaffold_only_message


def main() -> None:
    raise SystemExit(
        scaffold_only_message(
            runtime_name="ingest-task",
            current_source=(
                "infrastructure.lambda_ingest.handler, "
                "infrastructure.lambda_form990.handler, "
                "infrastructure.lambda_form990_orchestrator.handler, "
                "and infrastructure.lambda_form990_worker.handler"
            ),
            target_directory="backend/ingest-task/",
        )
    )


if __name__ == "__main__":
    main()
