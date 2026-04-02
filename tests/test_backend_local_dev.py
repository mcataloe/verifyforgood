from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

if str(BACKEND_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SHARED_SRC))


from charity_status_backend.shared.local_dev import backend_env_file, load_backend_local_env, run_db_current, run_db_upgrade


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


def test_backend_local_dev_commands_use_env_file_for_migrations(tmp_path, capsys):
    db_path = tmp_path / "local-dev.sqlite3"
    sqlite_url = f"sqlite+pysqlite:///{db_path}"
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "\n".join(
            [
                "PLATFORM_POSTGRES_ENABLED=true",
                f"PLATFORM_POSTGRES_URL={sqlite_url}",
                "PLATFORM_IDENTITY_STORE_BACKEND=postgres",
                "PLATFORM_NONPROFIT_STORE_BACKEND=postgres",
                "PLATFORM_NONPROFIT_QUERY_BACKEND=postgres",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    run_db_upgrade(root=ROOT, env_path=env_path)
    run_db_current(root=ROOT, env_path=env_path)

    capsys.readouterr()
    assert db_path.exists()
