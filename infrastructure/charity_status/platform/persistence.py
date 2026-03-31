from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import boto3


def _mapping_text(source: Mapping[str, str], key: str, default: str = "") -> str:
    return str(source.get(key, default) or default).strip()


def _mapping_bool(source: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = source.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _mapping_int(source: Mapping[str, str], key: str, default: int) -> int:
    raw = _mapping_text(source, key)
    return default if raw == "" else int(raw)


@dataclass(frozen=True)
class PostgresRuntimeConfig:
    enabled: bool = False
    host: str = ""
    port: int = 5432
    database: str = ""
    sslmode: str = "require"
    secret_arn: str = ""
    url: str = ""


@dataclass(frozen=True)
class PostgresCredentials:
    username: str
    password: str


@dataclass(frozen=True)
class PlatformPersistenceConfig:
    postgres: PostgresRuntimeConfig = PostgresRuntimeConfig()
    identity_store_backend: str = "dynamodb"
    organization_settings_store_backend: str = "dynamodb"
    control_plane_store_backend: str = "dynamodb"


def load_platform_persistence_config(env: Mapping[str, str] | None = None) -> PlatformPersistenceConfig:
    source = env or {}
    postgres = PostgresRuntimeConfig(
        enabled=_mapping_bool(source, "PLATFORM_POSTGRES_ENABLED"),
        host=_mapping_text(source, "PLATFORM_POSTGRES_HOST"),
        port=_mapping_int(source, "PLATFORM_POSTGRES_PORT", 5432),
        database=_mapping_text(source, "PLATFORM_POSTGRES_DATABASE"),
        sslmode=_mapping_text(source, "PLATFORM_POSTGRES_SSLMODE", "require") or "require",
        secret_arn=_mapping_text(source, "PLATFORM_POSTGRES_SECRET_ARN"),
        url=_mapping_text(source, "PLATFORM_POSTGRES_URL"),
    )
    config = PlatformPersistenceConfig(
        postgres=postgres,
        identity_store_backend=_mapping_text(source, "PLATFORM_IDENTITY_STORE_BACKEND", "dynamodb") or "dynamodb",
        organization_settings_store_backend=_mapping_text(source, "PLATFORM_ORGANIZATION_SETTINGS_STORE_BACKEND", "dynamodb") or "dynamodb",
        control_plane_store_backend=_mapping_text(source, "PLATFORM_CONTROL_PLANE_STORE_BACKEND", "dynamodb") or "dynamodb",
    )
    _validate_platform_persistence_config(config)
    return config


def resolve_postgres_credentials(
    config: PostgresRuntimeConfig,
    *,
    secrets_client: Any | None = None,
) -> PostgresCredentials:
    if not config.enabled:
        raise ValueError("PostgreSQL runtime config is disabled")
    if not config.secret_arn:
        raise ValueError("PLATFORM_POSTGRES_SECRET_ARN is required when resolving PostgreSQL credentials")
    client = secrets_client or boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=config.secret_arn)
    secret_string = str(response.get("SecretString") or "").strip()
    if not secret_string:
        raise ValueError("PostgreSQL secret did not contain SecretString")
    payload = json.loads(secret_string)
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "").strip()
    if not username or not password:
        raise ValueError("PostgreSQL secret must contain username and password")
    return PostgresCredentials(username=username, password=password)


def _validate_platform_persistence_config(config: PlatformPersistenceConfig) -> None:
    valid_backends = {"dynamodb", "postgres"}
    selected = {
        "PLATFORM_IDENTITY_STORE_BACKEND": config.identity_store_backend,
        "PLATFORM_ORGANIZATION_SETTINGS_STORE_BACKEND": config.organization_settings_store_backend,
        "PLATFORM_CONTROL_PLANE_STORE_BACKEND": config.control_plane_store_backend,
    }
    for key, value in selected.items():
        if value not in valid_backends:
            raise ValueError(f"{key} must be either dynamodb or postgres")

    any_postgres_backend = any(value == "postgres" for value in selected.values())
    if any_postgres_backend and not config.postgres.enabled:
        raise ValueError("PLATFORM_POSTGRES_ENABLED must be true when any platform store backend is postgres")

    if not config.postgres.enabled:
        return

    if config.postgres.url:
        return

    if not config.postgres.host:
        raise ValueError("PLATFORM_POSTGRES_HOST is required when PLATFORM_POSTGRES_ENABLED=true")
    if not config.postgres.database:
        raise ValueError("PLATFORM_POSTGRES_DATABASE is required when PLATFORM_POSTGRES_ENABLED=true")
    if not config.postgres.secret_arn:
        raise ValueError("PLATFORM_POSTGRES_SECRET_ARN is required when PLATFORM_POSTGRES_ENABLED=true")
