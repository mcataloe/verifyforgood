"""ECS wrapper for the local-first Form 990 ingest runtime."""

from __future__ import annotations

import sys
from typing import Mapping

from .local_runner import (
    build_local_ingest_run_config,
    resolve_runtime_environment_aliases,
    run_local_form990_ingest_config,
)
from .orchestration import build_workspace_layout


def main(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None) -> int:
    if argv:
        raise ValueError("ecs runtime entrypoint does not accept positional arguments")
    resolved_env = resolve_runtime_environment_aliases(env)
    config = build_local_ingest_run_config(env=resolved_env)
    build_workspace_layout(resolved_env).ensure()
    return run_local_form990_ingest_config(config=config, env=resolved_env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
