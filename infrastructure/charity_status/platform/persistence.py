from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import quote_plus

import boto3
from charity_status.control_plane.sqlalchemy_store import SqlAlchemyControlPlaneStore, build_control_plane_session_factory
from charity_status.enrichments.organization_store import SqlAlchemyOrganizationIntegrationSettingsStore
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine


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
    nonprofit_postgres: PostgresRuntimeConfig = PostgresRuntimeConfig()
    nonprofit_store_backend: str = "disabled"
    nonprofit_query_backend: str = "athena"


def load_platform_persistence_config(env: Mapping[str, str] | None = None) -> PlatformPersistenceConfig:
    source = env or {}
    postgres = _load_postgres_runtime_config(source, prefix="PLATFORM_POSTGRES")
    nonprofit_postgres = _load_postgres_runtime_config(
        source,
        prefix="PLATFORM_NONPROFIT_POSTGRES",
    )
    config = PlatformPersistenceConfig(
        postgres=postgres,
        nonprofit_postgres=nonprofit_postgres,
        nonprofit_store_backend=_mapping_text(source, "PLATFORM_NONPROFIT_STORE_BACKEND", "disabled") or "disabled",
        nonprofit_query_backend=_mapping_text(source, "PLATFORM_NONPROFIT_QUERY_BACKEND", "athena") or "athena",
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


def build_postgres_sqlalchemy_url(
    config: PostgresRuntimeConfig,
    *,
    credentials: PostgresCredentials | None = None,
) -> str:
    if not config.enabled:
        raise ValueError("PostgreSQL runtime config is disabled")
    if config.url:
        return config.url
    if credentials is None:
        raise ValueError("PostgreSQL credentials are required when PLATFORM_POSTGRES_URL is not set")
    sslmode = quote_plus(config.sslmode or "require")
    return (
        "postgresql+psycopg://"
        f"{quote_plus(credentials.username)}:{quote_plus(credentials.password)}"
        f"@{config.host}:{config.port}/{config.database}?sslmode={sslmode}"
    )


def resolve_postgres_sqlalchemy_url(
    env: Mapping[str, str] | None = None,
    *,
    secrets_client: Any | None = None,
) -> str:
    config = load_platform_persistence_config(env)
    if config.postgres.url:
        return config.postgres.url
    credentials = resolve_postgres_credentials(config.postgres, secrets_client=secrets_client)
    return build_postgres_sqlalchemy_url(config.postgres, credentials=credentials)


def resolve_nonprofit_postgres_sqlalchemy_url(
    env: Mapping[str, str] | None = None,
    *,
    secrets_client: Any | None = None,
) -> str:
    config = load_platform_persistence_config(env)
    runtime_config = (
        config.nonprofit_postgres
        if _postgres_runtime_config_is_configured(config.nonprofit_postgres)
        else config.postgres
    )
    if runtime_config.url:
        return runtime_config.url
    credentials = resolve_postgres_credentials(runtime_config, secrets_client=secrets_client)
    return build_postgres_sqlalchemy_url(runtime_config, credentials=credentials)


def has_dedicated_nonprofit_postgres_config(
    env: Mapping[str, str] | None = None,
) -> bool:
    config = load_platform_persistence_config(env)
    return _postgres_runtime_config_is_configured(config.nonprofit_postgres)


def build_control_plane_store(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> SqlAlchemyControlPlaneStore:
    source = env or {}
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    session_factory = build_control_plane_session_factory(resolved_url)
    return SqlAlchemyControlPlaneStore(session_factory)


def build_organization_settings_store(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> SqlAlchemyOrganizationIntegrationSettingsStore:
    source = env or {}
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    session_factory = _build_sqlalchemy_session_factory(resolved_url)
    return SqlAlchemyOrganizationIntegrationSettingsStore(session_factory)


def _validate_platform_persistence_config(config: PlatformPersistenceConfig) -> None:
    if config.nonprofit_store_backend not in {"disabled", "postgres"}:
        raise ValueError("PLATFORM_NONPROFIT_STORE_BACKEND must be either disabled or postgres")
    if config.nonprofit_query_backend not in {"athena", "postgres"}:
        raise ValueError("PLATFORM_NONPROFIT_QUERY_BACKEND must be either athena or postgres")

    nonprofit_uses_postgres = (
        config.nonprofit_store_backend == "postgres"
        or config.nonprofit_query_backend == "postgres"
    )
    nonprofit_has_dedicated_postgres = _postgres_runtime_config_is_configured(config.nonprofit_postgres)

    if nonprofit_has_dedicated_postgres:
        _validate_postgres_runtime_config(
            config.nonprofit_postgres,
            enabled_key="PLATFORM_NONPROFIT_POSTGRES_ENABLED",
            host_key="PLATFORM_NONPROFIT_POSTGRES_HOST",
            database_key="PLATFORM_NONPROFIT_POSTGRES_DATABASE",
            secret_key="PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN",
        )
    if config.postgres.enabled or not nonprofit_has_dedicated_postgres or not nonprofit_uses_postgres:
        _validate_postgres_runtime_config(
            config.postgres,
            enabled_key="PLATFORM_POSTGRES_ENABLED",
            host_key="PLATFORM_POSTGRES_HOST",
            database_key="PLATFORM_POSTGRES_DATABASE",
            secret_key="PLATFORM_POSTGRES_SECRET_ARN",
        )
    if nonprofit_uses_postgres and not (config.postgres.enabled or nonprofit_has_dedicated_postgres):
        raise ValueError("PLATFORM_POSTGRES_ENABLED must be true when any platform store backend is postgres")


def _load_postgres_runtime_config(
    source: Mapping[str, str],
    *,
    prefix: str,
) -> PostgresRuntimeConfig:
    prefixed_values_present = _postgres_runtime_env_present(source, prefix=prefix)
    return PostgresRuntimeConfig(
        enabled=_mapping_bool(source, f"{prefix}_ENABLED", prefixed_values_present),
        host=_mapping_text(source, f"{prefix}_HOST"),
        port=_mapping_int(source, f"{prefix}_PORT", 5432),
        database=_mapping_text(source, f"{prefix}_DATABASE"),
        sslmode=_mapping_text(source, f"{prefix}_SSLMODE", "require") or "require",
        secret_arn=_mapping_text(source, f"{prefix}_SECRET_ARN"),
        url=_mapping_text(source, f"{prefix}_URL"),
    )


def _postgres_runtime_env_present(source: Mapping[str, str], *, prefix: str) -> bool:
    for suffix in ("HOST", "PORT", "DATABASE", "SSLMODE", "SECRET_ARN", "URL"):
        if _mapping_text(source, f"{prefix}_{suffix}"):
            return True
    return False


def _postgres_runtime_config_is_configured(config: PostgresRuntimeConfig) -> bool:
    return bool(
        config.enabled
        or config.host
        or config.database
        or config.secret_arn
        or config.url
    )


def _validate_postgres_runtime_config(
    config: PostgresRuntimeConfig,
    *,
    enabled_key: str,
    host_key: str,
    database_key: str,
    secret_key: str,
) -> None:
    if not config.enabled:
        return
    if config.url:
        return
    if not config.host:
        raise ValueError(f"{host_key} is required when {enabled_key}=true")
    if not config.database:
        raise ValueError(f"{database_key} is required when {enabled_key}=true")
    if not config.secret_arn:
        raise ValueError(f"{secret_key} is required when {enabled_key}=true")


def _build_sqlalchemy_session_factory(bind: Engine | str) -> sessionmaker[Session]:
    engine = bind if isinstance(bind, Engine) else create_engine(bind, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
