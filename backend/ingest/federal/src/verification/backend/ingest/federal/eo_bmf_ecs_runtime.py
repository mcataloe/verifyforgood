"""ECS wrapper for the local-first EO/BMF ingest runtime."""

from __future__ import annotations

import sys
from typing import Mapping

from .eo_bmf_runner import (
    build_eo_bmf_run_config,
    resolve_eo_bmf_runtime_environment_aliases,
    run_local_eo_bmf_ingest_config,
)
from .orchestration.eo_bmf_workspace import build_eo_bmf_workspace_layout


def main(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None) -> int:
    if argv:
        raise ValueError("eo_bmf ecs runtime entrypoint does not accept positional arguments")
    resolved_env = resolve_eo_bmf_runtime_environment_aliases(env)
    config = build_eo_bmf_run_config(env=resolved_env)
    build_eo_bmf_workspace_layout(resolved_env).ensure()
    return run_local_eo_bmf_ingest_config(config=config, env=resolved_env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
