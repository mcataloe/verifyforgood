import pytest

from charity_status.platform import (
    build_postgres_sqlalchemy_url,
    PostgresRuntimeConfig,
    load_platform_persistence_config,
    resolve_postgres_sqlalchemy_url,
    resolve_postgres_credentials,
)


def test_load_platform_persistence_config_defaults_to_dynamodb_backends():
    config = load_platform_persistence_config({})

    assert config.identity_store_backend == "dynamodb"
    assert config.organization_settings_store_backend == "dynamodb"
    assert config.control_plane_store_backend == "dynamodb"
    assert config.postgres.enabled is False


def test_load_platform_persistence_config_requires_required_postgres_fields_when_enabled():
    with pytest.raises(ValueError, match="PLATFORM_POSTGRES_HOST"):
        load_platform_persistence_config({"PLATFORM_POSTGRES_ENABLED": "true"})


def test_load_platform_persistence_config_requires_enabled_flag_when_backend_switches_to_postgres():
    with pytest.raises(ValueError, match="PLATFORM_POSTGRES_ENABLED"):
        load_platform_persistence_config({"PLATFORM_IDENTITY_STORE_BACKEND": "postgres"})


def test_load_platform_persistence_config_accepts_secret_backed_postgres_settings():
    config = load_platform_persistence_config(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_HOST": "db.example.internal",
            "PLATFORM_POSTGRES_PORT": "5432",
            "PLATFORM_POSTGRES_DATABASE": "verification_platform",
            "PLATFORM_POSTGRES_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:platform-postgres",
            "PLATFORM_POSTGRES_SSLMODE": "require",
        }
    )

    assert config.postgres.enabled is True
    assert config.postgres.host == "db.example.internal"
    assert config.postgres.port == 5432
    assert config.postgres.database == "verification_platform"
    assert config.postgres.secret_arn.endswith(":platform-postgres")


def test_resolve_postgres_credentials_reads_secret_backed_username_and_password():
    class _SecretsClient:
        def get_secret_value(self, *, SecretId):
            assert SecretId == "arn:secret"
            return {"SecretString": '{"username":"platform_app","password":"super-secret"}'}

    credentials = resolve_postgres_credentials(
        PostgresRuntimeConfig(
            enabled=True,
            host="db.example.internal",
            database="verification_platform",
            secret_arn="arn:secret",
        ),
        secrets_client=_SecretsClient(),
    )

    assert credentials.username == "platform_app"
    assert credentials.password == "super-secret"


def test_build_postgres_sqlalchemy_url_uses_psycopg_driver_and_sslmode():
    url = build_postgres_sqlalchemy_url(
        PostgresRuntimeConfig(
            enabled=True,
            host="db.example.internal",
            port=5432,
            database="verification_platform",
            sslmode="require",
        ),
        credentials=type("Creds", (), {"username": "platform_app", "password": "super-secret"})(),
    )

    assert url.startswith("postgresql+psycopg://platform_app:super-secret@db.example.internal:5432/verification_platform")
    assert "sslmode=require" in url


def test_resolve_postgres_sqlalchemy_url_uses_secret_when_raw_url_absent():
    class _SecretsClient:
        def get_secret_value(self, *, SecretId):
            assert SecretId == "arn:secret"
            return {"SecretString": '{"username":"platform_app","password":"super-secret"}'}

    url = resolve_postgres_sqlalchemy_url(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_HOST": "db.example.internal",
            "PLATFORM_POSTGRES_PORT": "5432",
            "PLATFORM_POSTGRES_DATABASE": "verification_platform",
            "PLATFORM_POSTGRES_SECRET_ARN": "arn:secret",
            "PLATFORM_POSTGRES_SSLMODE": "require",
        },
        secrets_client=_SecretsClient(),
    )

    assert url.startswith("postgresql+psycopg://platform_app:super-secret@db.example.internal:5432/verification_platform")
