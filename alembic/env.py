from __future__ import annotations

import os
import pathlib
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

ROOT = pathlib.Path(__file__).resolve().parents[1]
INFRA_PATH = ROOT / "infrastructure"

for path in (ROOT, INFRA_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from verification.backend.shared.platform import resolve_postgres_sqlalchemy_url  # noqa: E402
from verification.backend.shared.customer_accounts import CustomerAccountsBase  # noqa: E402
from verification.backend.shared.nonprofits import (  # noqa: F401,E402
    ComplianceCheckModel,
    NonprofitFilingModel,
    NonprofitModel,
    NonprofitSourceModel,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = CustomerAccountsBase.metadata


def _resolve_sqlalchemy_url() -> str:
    configured = str(config.get_main_option("sqlalchemy.url") or "").strip()
    if configured:
        return configured
    return resolve_postgres_sqlalchemy_url(os.environ)


def run_migrations_offline() -> None:
    url = _resolve_sqlalchemy_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _resolve_sqlalchemy_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

