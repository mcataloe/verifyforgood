"""Local CLI for backend-owned ingest-task runtimes."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .form990 import orchestrator as form990_orchestrator
from .form990 import runtime as form990_runtime
from .form990 import worker as form990_worker
from .monthly import staging as monthly_staging
from .monthly import worker as monthly_worker


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="charity_status_backend.ingest_task.cli")
    parser.add_argument(
        "command",
        choices=("form990", "form990-worker", "form990-orchestrator", "monthly-staging", "monthly-worker"),
    )
    parser.add_argument("--event-json")
    parser.add_argument("--event-file")
    args = parser.parse_args(argv)

    if args.command == "monthly-worker":
        return int(monthly_worker.main())

    event = _load_event(args)
    if args.command == "form990":
        result = form990_runtime.handler(event, None)
    elif args.command == "form990-worker":
        result = form990_worker.handler(event, None)
    elif args.command == "form990-orchestrator":
        result = form990_orchestrator.handler(event, None)
    else:
        result = monthly_staging.handler(event, None)

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

