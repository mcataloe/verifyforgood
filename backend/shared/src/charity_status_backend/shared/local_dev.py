"""Backend-local environment and migration helpers."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[5]
for _path in (
    _REPO_ROOT / "public-core" / "src",
    _REPO_ROOT / "private-platform" / "src",
    _REPO_ROOT / "infrastructure",
):
    if _path.exists():
        resolved = str(_path.resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)

from alembic import command
from alembic.config import Config
from charity_status.platform import (
    has_dedicated_nonprofit_postgres_config,
    load_platform_persistence_config,
    resolve_nonprofit_postgres_sqlalchemy_url,
    resolve_postgres_sqlalchemy_url,
)
from charity_status_platform.nonprofits import build_nonprofit_engine, drop_nonprofit_tables
from charity_status_platform.runtime import cutover_nonprofit_database


def repo_root() -> Path:
    return _REPO_ROOT


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


def _nonprofit_alembic_config(*, root: Path | None = None) -> Config:
    base_root = Path(root) if root is not None else repo_root()
    config = Config(str(base_root / "alembic_nonprofit.ini"))
    config.set_main_option("script_location", str(base_root / "alembic_nonprofit"))
    return config


def _require_dedicated_nonprofit_database(env: dict[str, str]) -> None:
    if not has_dedicated_nonprofit_postgres_config(env):
        raise ValueError(
            "Dedicated nonprofit PostgreSQL config is required; set PLATFORM_NONPROFIT_POSTGRES_* before running nonprofit DB commands"
        )


def run_db_upgrade(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    command.upgrade(_alembic_config(root=root), "head")


def run_db_current(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    command.current(_alembic_config(root=root), verbose=False)


def run_db_upgrade_nonprofit(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    source_env = dict(os.environ)
    persistence_config = load_platform_persistence_config(source_env)
    if (
        persistence_config.nonprofit_store_backend != "postgres"
        and persistence_config.nonprofit_query_backend != "postgres"
    ):
        return
    _require_dedicated_nonprofit_database(source_env)
    command.upgrade(_nonprofit_alembic_config(root=root), "head")


def run_db_current_nonprofit(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    source_env = dict(os.environ)
    _require_dedicated_nonprofit_database(source_env)
    command.current(_nonprofit_alembic_config(root=root), verbose=False)


def run_db_reset_nonprofit(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    source_env = dict(os.environ)
    _require_dedicated_nonprofit_database(source_env)
    resolved_url = resolve_nonprofit_postgres_sqlalchemy_url(source_env)
    drop_nonprofit_tables(build_nonprofit_engine(resolved_url), include_version_table=True)
    run_db_upgrade_nonprofit(root=root, env_path=env_path)


def run_db_cutover_nonprofit(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path, override=True)
    source_env = dict(os.environ)
    _require_dedicated_nonprofit_database(source_env)
    cutover_nonprofit_database(
        source_env,
        source_sqlalchemy_url=resolve_postgres_sqlalchemy_url(source_env),
        target_sqlalchemy_url=resolve_nonprofit_postgres_sqlalchemy_url(source_env),
        reset_target=True,
    )
    command.stamp(_nonprofit_alembic_config(root=root), "head")


def run_db_upgrade_all(*, root: Path | None = None, env_path: Path | None = None) -> None:
    load_backend_local_env(root=root, env_path=env_path)
    run_db_upgrade(root=root, env_path=env_path)
    if has_dedicated_nonprofit_postgres_config(dict(os.environ)):
        run_db_upgrade_nonprofit(root=root, env_path=env_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="charity_status_backend.shared.local_dev")
    parser.add_argument(
        "command",
        choices=(
            "db-upgrade",
            "db-upgrade-nonprofit",
            "db-upgrade-all",
            "db-current",
            "db-current-nonprofit",
            "db-reset-nonprofit",
            "db-cutover-nonprofit",
        ),
    )
    args = parser.parse_args(argv)

    if args.command == "db-upgrade":
        run_db_upgrade()
        return 0
    if args.command == "db-upgrade-nonprofit":
        run_db_upgrade_nonprofit()
        return 0
    if args.command == "db-upgrade-all":
        run_db_upgrade_all()
        return 0
    if args.command == "db-current-nonprofit":
        run_db_current_nonprofit()
        return 0
    if args.command == "db-reset-nonprofit":
        run_db_reset_nonprofit()
        return 0
    if args.command == "db-cutover-nonprofit":
        run_db_cutover_nonprofit()
        return 0

    run_db_current()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
