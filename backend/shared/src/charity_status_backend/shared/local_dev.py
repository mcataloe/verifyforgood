"""Backend-local environment and migration helpers."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def backend_env_file(*, root: Path | None = None, filename: str = ".env.local") -> Path:
    base_root = Path(root) if root is not None else repo_root()
    return base_root / "backend" / filename


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export ") :].strip()
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def load_backend_local_env(
    *,
    root: Path | None = None,
    env_path: Path | None = None,
    override: bool = False,
) -> Path:
    target = Path(env_path) if env_path is not None else backend_env_file(root=root)
    if not target.exists():
        return target

    for raw_line in target.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value
    return target


def _alembic_config(*, root: Path | None = None) -> Config:
    base_root = Path(root) if root is not None else repo_root()
    config = Config(str(base_root / "alembic.ini"))
    config.set_main_option("script_location", str(base_root / "alembic"))
    return config


def run_db_upgrade(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    command.upgrade(_alembic_config(root=root), "head")


def run_db_current(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    command.current(_alembic_config(root=root), verbose=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="charity_status_backend.shared.local_dev")
    parser.add_argument("command", choices=("db-upgrade", "db-current"))
    args = parser.parse_args(argv)

    if args.command == "db-upgrade":
        run_db_upgrade()
        return 0

    run_db_current()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
