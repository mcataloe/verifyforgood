from __future__ import annotations

from charity_status_backend.ingest_task import ecs_runtime, local_runner


def test_runtime_environment_aliases_map_only_when_repo_native_values_are_absent():
    resolved = local_runner.resolve_runtime_environment_aliases(
        {
            "DATABASE_URL": "postgresql+psycopg://alias",
            "WORKSPACE_PATH": "/tmp/from-alias",
        }
    )

    assert resolved["PLATFORM_POSTGRES_URL"] == "postgresql+psycopg://alias"
    assert resolved["PLATFORM_POSTGRES_ENABLED"] == "true"
    assert resolved["FORM990_WORKSPACE_DIR"] == "/tmp/from-alias"

    preserved = local_runner.resolve_runtime_environment_aliases(
        {
            "DATABASE_URL": "postgresql+psycopg://alias",
            "PLATFORM_POSTGRES_URL": "postgresql+psycopg://native",
            "WORKSPACE_PATH": "/tmp/from-alias",
            "FORM990_WORKSPACE_DIR": "/tmp/native",
        }
    )

    assert preserved["PLATFORM_POSTGRES_URL"] == "postgresql+psycopg://native"
    assert preserved["FORM990_WORKSPACE_DIR"] == "/tmp/native"


def test_build_local_ingest_run_config_reads_ecs_alias_envs():
    config = local_runner.build_local_ingest_run_config(
        env={
            "STRICT_MODE": "true",
            "MAX_ARCHIVES": "7",
            "WORKSPACE_PATH": "/tmp/ecs-workspace",
            "LOG_LEVEL": "ERROR",
        }
    )

    assert config.strict is True
    assert config.limit == 7
    assert config.workspace == "/tmp/ecs-workspace"
    assert config.log_level == "ERROR"


def test_ecs_runtime_creates_workspace_and_calls_shared_local_runner(monkeypatch, tmp_path):
    captured: dict[str, object] = {}

    def fake_run_local_form990_ingest_config(*, config, env):
        captured["config"] = config
        captured["env"] = dict(env)
        return 17

    monkeypatch.setattr(ecs_runtime, "run_local_form990_ingest_config", fake_run_local_form990_ingest_config)

    workspace = tmp_path / "ecs-workspace"
    exit_code = ecs_runtime.main(
        env={
            "WORKSPACE_PATH": str(workspace),
            "STRICT_MODE": "true",
            "MAX_ARCHIVES": "3",
            "LOG_LEVEL": "WARNING",
            "DATABASE_URL": "postgresql+psycopg://ecs",
        }
    )

    assert exit_code == 17
    assert workspace.exists()
    assert captured["config"].strict is True
    assert captured["config"].limit == 3
    assert captured["config"].workspace == str(workspace)
    assert captured["config"].log_level == "WARNING"
    assert captured["env"]["PLATFORM_POSTGRES_URL"] == "postgresql+psycopg://ecs"


def test_ecs_runtime_rejects_positional_arguments():
    try:
        ecs_runtime.main(["unexpected"], env={"BUCKET": "test-bucket"})
    except ValueError as exc:
        assert "does not accept positional arguments" in str(exc)
    else:
        raise AssertionError("expected ecs runtime to reject positional arguments")
