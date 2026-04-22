from __future__ import annotations

from pathlib import Path


def test_local_docker_compose_defines_only_the_expected_services():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "marketing:" in compose
    assert "platform:" in compose
    assert "api:" in compose
    assert "platformapi:" in compose
    assert "ingest-task:" not in compose


def test_local_docker_compose_uses_expected_ports_and_host_database_overrides():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert '"5174:80"' in compose
    assert '"3953:80"' in compose
    assert '"5621:8000"' in compose
    assert '"5622:8000"' in compose
    assert "host.docker.internal" in compose
    assert "backend/.env.local" in compose
