from __future__ import annotations

import importlib
from pathlib import Path
import re
import sys

import pytest
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]
FILTERED_SYS_PATH = [
    entry for entry in sys.path if Path(entry or ".").resolve() != ROOT
]
ORIGINAL_SYS_PATH = sys.path[:]
sys.modules.pop("alembic", None)
try:
    sys.path[:] = FILTERED_SYS_PATH
    command = importlib.import_module("alembic.command")
    Config = importlib.import_module("alembic.config").Config
except ModuleNotFoundError:
    pytest.skip("Alembic package is not installed in this environment.", allow_module_level=True)
finally:
    sys.path[:] = ORIGINAL_SYS_PATH


def test_alembic_upgrade_creates_customer_account_and_nonprofit_foundation_tables(tmp_path: Path):
    db_path = tmp_path / "alembic.sqlite3"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")

    command.upgrade(config, "head")

    inspector = inspect(create_engine(f"sqlite+pysqlite:///{db_path}"))
    table_names = set(inspector.get_table_names())
    subscription_columns = {column["name"] for column in inspector.get_columns("organization_subscriptions")}

    assert "users" in table_names
    assert "organizations" in table_names
    assert "organization_memberships" in table_names
    assert "plans" in table_names
    assert "organization_subscriptions" in table_names
    assert "pending_plan_id" in subscription_columns
    assert "pending_plan_effective_at" in subscription_columns
    assert "cancel_at_period_end" in subscription_columns
    assert "updated_at" in subscription_columns
    assert "grace_period_ends_at" in subscription_columns
    assert "billing_status" in subscription_columns
    assert "organization_api_keys" in table_names
    assert "organization_audit_logs" in table_names
    assert "organization_support_tickets" in table_names
    assert "nonprofits" in table_names
    assert "nonprofit_filings" in table_names
    assert "nonprofit_raw_filings" in table_names
    assert "nonprofit_sources" in table_names
    assert "compliance_checks" in table_names


def test_phase28_migration_uses_postgres_safe_explicit_identifier_names():
    migration_path = (
        Path("alembic")
        / "versions"
        / "20260417_000015_phase28_postgres_only_persistence.py"
    )
    contents = migration_path.read_text(encoding="utf-8")
    identifiers = re.findall(r'name="([^"]+)"', contents)

    assert [name for name in identifiers if len(name) > 63] == []
