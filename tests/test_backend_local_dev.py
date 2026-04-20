from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect


ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

if str(BACKEND_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SHARED_SRC))


from verification_backend.shared import local_dev
from verification_backend.shared.local_dev import (
    backend_env_file,
    load_backend_local_env,
    run_db_current,
    run_db_upgrade,
)
from verification_platform.nonprofits import (
    NonprofitRecord,
    SqlAlchemyNonprofitRepository,
    build_nonprofit_session_factory,
)
from verification_platform.runtime import cutover_nonprofit_database
from verification_platform.runtime.nonprofit_db_cutover import _sync_identity_sequences


def test_backend_local_env_loader_prefers_existing_shell_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "PLATFORM_POSTGRES_URL=postgresql+psycopg://from-file\nAPI_AUTH_ENABLED=false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PLATFORM_POSTGRES_URL", "postgresql+psycopg://from-shell")

    load_backend_local_env(env_path=env_path)

    assert backend_env_file(root=tmp_path.parent, filename=env_path.name).name == ".env.local"
    assert pathlib.Path(env_path).exists()
    assert sys.modules is not None
    assert __import__("os").environ["PLATFORM_POSTGRES_URL"] == "postgresql+psycopg://from-shell"
    assert __import__("os").environ["API_AUTH_ENABLED"] == "false"


def test_backend_local_env_loader_ignores_inline_recommended_markers(tmp_path, monkeypatch):
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "\n".join(
            [
                "BACKEND_API_HOST=0.0.0.0 ##RECOMMENDED##",
                "BACKEND_API_PORT=8001 ##RECOMMENDED##",
                "PORTAL_AUTH_TOKEN_SECRET='dev-portal-auth-secret # literal'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("BACKEND_API_HOST", raising=False)
    monkeypatch.delenv("BACKEND_API_PORT", raising=False)
    monkeypatch.delenv("PORTAL_AUTH_TOKEN_SECRET", raising=False)

    load_backend_local_env(env_path=env_path, override=True)

    assert __import__("os").environ["BACKEND_API_HOST"] == "0.0.0.0"
    assert __import__("os").environ["BACKEND_API_PORT"] == "8001"
    assert __import__("os").environ["PORTAL_AUTH_TOKEN_SECRET"] == "dev-portal-auth-secret # literal"


def test_backend_local_dev_commands_use_env_file_for_migrations(tmp_path, monkeypatch, capsys):
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "\n".join(
            [
                "PLATFORM_POSTGRES_ENABLED=true",
                "PLATFORM_POSTGRES_URL=sqlite+pysqlite:///local-dev.sqlite3",
                "PLATFORM_NONPROFIT_STORE_BACKEND=postgres",
                "PLATFORM_NONPROFIT_QUERY_BACKEND=postgres",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    recorded: list[tuple[str, object]] = []

    monkeypatch.setattr(
        local_dev.command,
        "upgrade",
        lambda config, revision: recorded.append(("upgrade", revision)),
    )
    monkeypatch.setattr(
        local_dev.command,
        "current",
        lambda config, verbose=False: recorded.append(("current", verbose)),
    )

    run_db_upgrade(root=ROOT, env_path=env_path)
    run_db_current(root=ROOT, env_path=env_path)

    capsys.readouterr()
    assert recorded == [("upgrade", "head"), ("current", False)]


def test_backend_local_dev_can_bootstrap_dedicated_nonprofit_database(tmp_path):
    nonprofit_db_path = tmp_path / "nonprofit.sqlite3"
    nonprofit_url = f"sqlite+pysqlite:///{nonprofit_db_path}"
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "\n".join(
            [
                "PLATFORM_POSTGRES_ENABLED=true",
                "PLATFORM_POSTGRES_URL=sqlite+pysqlite:///platform.sqlite3",
                "PLATFORM_NONPROFIT_STORE_BACKEND=postgres",
                "PLATFORM_NONPROFIT_QUERY_BACKEND=postgres",
                "PLATFORM_NONPROFIT_POSTGRES_ENABLED=true",
                f"PLATFORM_NONPROFIT_POSTGRES_URL={nonprofit_url}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from verification_backend.shared.local_dev import run_db_upgrade_nonprofit

    load_backend_local_env(env_path=env_path, override=True)
    run_db_upgrade_nonprofit()

    nonprofit_tables = set(inspect(create_engine(f"sqlite+pysqlite:///{nonprofit_db_path}")).get_table_names())

    assert "nonprofits" in nonprofit_tables
    assert "nonprofit_filings" in nonprofit_tables


def test_backend_local_dev_module_bootstraps_repo_python_paths():
    module_path = ROOT / "backend" / "shared" / "src"
    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            f"sys.path.insert(0, r'{module_path}'); "
            "import verification_backend.shared.local_dev as local_dev; "
            "print(local_dev.repo_root())"
        ),
    ]

    result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=ROOT)

    assert str(ROOT) in result.stdout.strip()


def test_backend_local_dev_can_reset_dedicated_nonprofit_database(tmp_path, monkeypatch):
    nonprofit_db_path = tmp_path / "nonprofit_reset.sqlite3"
    nonprofit_url = f"sqlite+pysqlite:///{nonprofit_db_path}"
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "\n".join(
            [
                "PLATFORM_POSTGRES_ENABLED=true",
                "PLATFORM_POSTGRES_URL=sqlite+pysqlite:///platform.sqlite3",
                "PLATFORM_NONPROFIT_STORE_BACKEND=postgres",
                "PLATFORM_NONPROFIT_QUERY_BACKEND=postgres",
                "PLATFORM_NONPROFIT_POSTGRES_ENABLED=true",
                f"PLATFORM_NONPROFIT_POSTGRES_URL={nonprofit_url}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    for key in (
        "PLATFORM_NONPROFIT_POSTGRES_ENABLED",
        "PLATFORM_NONPROFIT_POSTGRES_URL",
        "PLATFORM_NONPROFIT_POSTGRES_HOST",
        "PLATFORM_NONPROFIT_POSTGRES_DATABASE",
        "PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN",
    ):
        monkeypatch.delenv(key, raising=False)

    load_backend_local_env(env_path=env_path, override=True)
    local_dev.run_db_upgrade_nonprofit(root=ROOT, env_path=env_path)
    engine = create_engine(nonprofit_url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS alembic_version_nonprofit (version_num VARCHAR(32) NOT NULL)")
        connection.exec_driver_sql("INSERT INTO alembic_version_nonprofit(version_num) VALUES ('stale')")
        connection.exec_driver_sql(
            "INSERT INTO nonprofits (ein, canonical_name, normalized_name, revoked, created_at, updated_at) "
            "VALUES ('999999999', 'Stale Org', 'stale org', 0, '2026-04-19 00:00:00+00:00', '2026-04-19 00:00:00+00:00')"
        )

    local_dev.run_db_reset_nonprofit(root=ROOT, env_path=env_path)

    inspector = inspect(create_engine(nonprofit_url))
    nonprofit_tables = set(inspector.get_table_names())
    assert "alembic_version_nonprofit" in nonprofit_tables
    with create_engine(nonprofit_url).connect() as connection:
        count = connection.exec_driver_sql("SELECT COUNT(*) FROM nonprofits").scalar_one()
    assert count == 0


def test_backend_local_dev_nonprofit_commands_require_dedicated_database(tmp_path, monkeypatch):
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "\n".join(
            [
                "PLATFORM_POSTGRES_ENABLED=true",
                "PLATFORM_POSTGRES_URL=sqlite+pysqlite:///platform.sqlite3",
                "PLATFORM_NONPROFIT_STORE_BACKEND=postgres",
                "PLATFORM_NONPROFIT_QUERY_BACKEND=postgres",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    for key in (
        "PLATFORM_NONPROFIT_POSTGRES_ENABLED",
        "PLATFORM_NONPROFIT_POSTGRES_URL",
        "PLATFORM_NONPROFIT_POSTGRES_HOST",
        "PLATFORM_NONPROFIT_POSTGRES_DATABASE",
        "PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="Dedicated nonprofit PostgreSQL config is required"):
        local_dev.run_db_current_nonprofit(root=ROOT, env_path=env_path)

    with pytest.raises(ValueError, match="Dedicated nonprofit PostgreSQL config is required"):
        local_dev.run_db_reset_nonprofit(root=ROOT, env_path=env_path)


def test_cutover_nonprofit_database_resets_target_and_copies_rows(tmp_path):
    source_url = f"sqlite+pysqlite:///{tmp_path / 'platform_source.sqlite3'}"
    target_url = f"sqlite+pysqlite:///{tmp_path / 'nonprofit_target.sqlite3'}"
    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)
    source_repository = SqlAlchemyNonprofitRepository(build_nonprofit_session_factory(source_engine))
    target_repository = SqlAlchemyNonprofitRepository(build_nonprofit_session_factory(target_engine))
    from verification_platform.nonprofits import create_nonprofit_tables

    create_nonprofit_tables(source_engine)
    create_nonprofit_tables(target_engine)
    source_repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=None,
            ein="123456789",
            canonical_name="Source Org",
            normalized_name="source org",
            created_at="2026-04-19T00:00:00+00:00",
            updated_at="2026-04-19T00:00:00+00:00",
        )
    )
    target_repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=None,
            ein="999999999",
            canonical_name="Stale Org",
            normalized_name="stale org",
            created_at="2026-04-19T00:00:00+00:00",
            updated_at="2026-04-19T00:00:00+00:00",
        )
    )
    with target_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS alembic_version_nonprofit (version_num VARCHAR(32) NOT NULL)")

    report = cutover_nonprofit_database(
        {
            "PLATFORM_POSTGRES_URL": source_url,
            "PLATFORM_NONPROFIT_POSTGRES_URL": target_url,
        },
        source_sqlalchemy_url=source_url,
        target_sqlalchemy_url=target_url,
        reset_target=True,
    )

    assert report.rows_copied_by_table["nonprofits"] == 1
    repository = SqlAlchemyNonprofitRepository(build_nonprofit_session_factory(target_engine))
    assert repository.get_nonprofit_by_ein("123456789") is not None
    assert repository.get_nonprofit_by_ein("999999999") is None
    assert "alembic_version_nonprofit" not in inspect(target_engine).get_table_names()


def test_cutover_nonprofit_database_rejects_identical_urls(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'shared.sqlite3'}"

    with pytest.raises(ValueError, match="Source and target PostgreSQL URLs are identical"):
        cutover_nonprofit_database(
            {
                "PLATFORM_POSTGRES_URL": url,
                "PLATFORM_NONPROFIT_POSTGRES_URL": url,
            },
            source_sqlalchemy_url=url,
            target_sqlalchemy_url=url,
        )


def test_sync_identity_sequences_uses_sequence_start_for_empty_tables():
    table = sa.Table(
        "nonprofit_raw_filings",
        sa.MetaData(),
        sa.Column("raw_filing_id", sa.BigInteger(), primary_key=True),
    )

    class _ScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

        def scalar_one(self):
            return self._value

    class _RecordingConnection:
        def __init__(self):
            self.calls: list[tuple[str, dict[str, object] | None]] = []

        def execute(self, clause, params=None):
            sql = str(clause)
            self.calls.append((sql, params))
            if "pg_get_serial_sequence" in sql:
                return _ScalarResult("public.nonprofit_raw_filings_raw_filing_id_seq")
            if "COALESCE(MAX(raw_filing_id), 0)" in sql:
                return _ScalarResult(0)
            if "setval" in sql:
                return _ScalarResult(None)
            raise AssertionError(f"Unexpected SQL executed: {sql}")

    engine = type("Engine", (), {"dialect": type("Dialect", (), {"name": "postgresql"})()})()
    connection = _RecordingConnection()

    _sync_identity_sequences(connection, engine, [table])

    setval_calls = [params for sql, params in connection.calls if "setval" in sql]
    assert setval_calls == [
        {
            "sequence_name": "public.nonprofit_raw_filings_raw_filing_id_seq",
            "max_value": 1,
            "is_called": False,
        }
    ]

