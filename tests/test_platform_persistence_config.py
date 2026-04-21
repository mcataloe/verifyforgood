import pytest

from verification.platform import (
    PostgresRuntimeConfig,
    build_postgres_sqlalchemy_url,
    load_platform_persistence_config,
    resolve_nonprofit_postgres_sqlalchemy_url,
    resolve_postgres_credentials,
    resolve_postgres_sqlalchemy_url,
)


def test_load_platform_persistence_config_defaults_to_postgres_only_platform_runtime():
    config = load_platform_persistence_config({})

    assert config.nonprofit_store_backend == "disabled"
    assert config.postgres.enabled is False


def test_load_platform_persistence_config_requires_required_postgres_fields_when_enabled():
    with pytest.raises(ValueError, match="PLATFORM_POSTGRES_HOST"):
        load_platform_persistence_config({"PLATFORM_POSTGRES_ENABLED": "true"})


def test_load_platform_persistence_config_requires_enabled_flag_when_postgres_backed_runtime_is_selected():
    with pytest.raises(ValueError, match="PLATFORM_POSTGRES_ENABLED"):
        load_platform_persistence_config({"PLATFORM_NONPROFIT_STORE_BACKEND": "postgres"})


def test_load_platform_persistence_config_accepts_secret_backed_postgres_settings():
    config = load_platform_persistence_config(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_HOST": "db.example.internal",
            "PLATFORM_POSTGRES_PORT": "5432",
            "PLATFORM_POSTGRES_DATABASE": "verification_platform",
            "PLATFORM_POSTGRES_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:platform-postgres",
            "PLATFORM_POSTGRES_SSLMODE": "require",
            "PLATFORM_NONPROFIT_STORE_BACKEND": "postgres",
        }
    )

    assert config.postgres.enabled is True
    assert config.postgres.host == "db.example.internal"
    assert config.postgres.port == 5432
    assert config.postgres.database == "verification_platform"
    assert config.postgres.secret_arn.endswith(":platform-postgres")
    assert config.nonprofit_store_backend == "postgres"


def test_load_platform_persistence_config_accepts_local_url_driven_postgres_settings():
    config = load_platform_persistence_config(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/verification_platform",
            "PLATFORM_NONPROFIT_STORE_BACKEND": "postgres",
        }
    )

    assert config.postgres.enabled is True
    assert config.postgres.url == "postgresql+psycopg://postgres:postgres@localhost:5432/verification_platform"
    assert config.nonprofit_store_backend == "postgres"


def test_load_platform_persistence_config_accepts_dedicated_nonprofit_postgres_settings():
    config = load_platform_persistence_config(
        {
            "PLATFORM_NONPROFIT_POSTGRES_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/verification_nonprofit",
            "PLATFORM_NONPROFIT_STORE_BACKEND": "postgres",
        }
    )

    assert config.postgres.enabled is False
    assert config.nonprofit_postgres.enabled is True
    assert config.nonprofit_postgres.url.endswith("/verification_nonprofit")
    assert config.nonprofit_store_backend == "postgres"


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


def test_resolve_nonprofit_postgres_sqlalchemy_url_prefers_dedicated_nonprofit_config():
    url = resolve_nonprofit_postgres_sqlalchemy_url(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/verification_platform",
            "PLATFORM_NONPROFIT_POSTGRES_URL": "postgresql+psycopg://postgres:postgres@localhost:5432/verification_nonprofit",
        }
    )

    assert url.endswith("/verification_nonprofit")
