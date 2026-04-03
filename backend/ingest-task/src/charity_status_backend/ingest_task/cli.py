"""Local CLI for backend-owned ingest-task runtimes."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _load_event(args: argparse.Namespace) -> dict[str, Any]:
    if args.event_json:
        payload = json.loads(args.event_json)
    elif args.event_file:
        with open(args.event_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("event payload must be a JSON object")
    return payload


def _dispatch(command: str, event: dict[str, Any]) -> Any:
    if command == "monthly-worker":
        from .monthly import worker as monthly_worker

        return monthly_worker.main()
    if command == "form990":
        from .form990 import runtime as form990_runtime

        return form990_runtime.handler(event, None)
    if command == "form990-worker":
        from .form990 import worker as form990_worker

        return form990_worker.handler(event, None)
    if command == "form990-orchestrator":
        from .form990 import orchestrator as form990_orchestrator

        return form990_orchestrator.handler(event, None)

    from .monthly import staging as monthly_staging

    return monthly_staging.handler(event, None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="charity_status_backend.ingest_task.cli",
        description="Backend-owned local CLI for Form 990 and monthly ingest runtimes.",
    )
    parser.add_argument(
        "command",
        choices=("form990", "form990-worker", "form990-orchestrator", "monthly-staging", "monthly-worker"),
    )
    parser.add_argument("--event-json")
    parser.add_argument("--event-file")
    args = parser.parse_args(argv)

    event = {} if args.command == "monthly-worker" else _load_event(args)
    result = _dispatch(args.command, event)

    if args.command == "monthly-worker":
        return int(result)

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
