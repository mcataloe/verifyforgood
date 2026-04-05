"""CLI entrypoints for backend-owned ingest-task runtimes."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from charity_status_backend.shared.local_dev import load_backend_local_env


def _build_run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="charity_status_backend.ingest_task.cli run",
        description="Run local archive-at-a-time Form 990 ingest on the ECS worker path.",
    )
    parser.add_argument("--archive-url")
    parser.add_argument("--single-archive", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--workspace")
    parser.add_argument("--limit", type=int)
    return parser


def _build_eo_bmf_run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="charity_status_backend.ingest_task.cli run-eo-bmf",
        description="Run local EO/BMF ingest on the backend-owned ECS-style path.",
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument("--workspace")
    return parser


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
        from ..monthly import worker as monthly_worker

        return monthly_worker.main()
    raise ValueError(f"unsupported ingest-task command: {command}")


def main(argv: list[str] | None = None) -> int:
    load_backend_local_env()
    args_list = list(argv or sys.argv[1:])
    if args_list and args_list[0] == "run":
        from ..local_runner import run_local_form990_ingest

        run_args = _build_run_parser().parse_args(args_list[1:])
        return run_local_form990_ingest(
            archive_url=run_args.archive_url,
            single_archive=bool(run_args.single_archive),
            strict=bool(run_args.strict),
            keep_temp=bool(run_args.keep_temp),
            workspace=run_args.workspace,
            limit=run_args.limit,
        )
    if args_list and args_list[0] == "ecs-run":
        from ..ecs_runtime import main as ecs_main

        return ecs_main(args_list[1:])
    if args_list and args_list[0] == "run-eo-bmf":
        from ..eo_bmf_runner import run_local_eo_bmf_ingest

        run_args = _build_eo_bmf_run_parser().parse_args(args_list[1:])
        return run_local_eo_bmf_ingest(
            strict=bool(run_args.strict),
            keep_temp=bool(run_args.keep_temp),
            workspace=run_args.workspace,
        )
    if args_list and args_list[0] == "ecs-run-eo-bmf":
        from ..eo_bmf_ecs_runtime import main as eo_bmf_ecs_main

        return eo_bmf_ecs_main(args_list[1:])

    parser = argparse.ArgumentParser(
        prog="charity_status_backend.ingest_task.cli",
        description="Backend-owned local CLI for EO/BMF, Form 990, and monthly ingest runtimes.",
    )
    parser.add_argument(
        "command",
        choices=("ecs-run", "ecs-run-eo-bmf", "monthly-worker"),
    )
    parser.add_argument("--event-json")
    parser.add_argument("--event-file")
    args = parser.parse_args(args_list)

    event = {} if args.command == "monthly-worker" else _load_event(args)
    result = _dispatch(args.command, event)

    if args.command == "monthly-worker":
        return int(result)

    print(json.dumps(result, sort_keys=True))
    return 0


__all__ = ["main"]
