"""Backend-owned runtime import root for nonprofit ingest persistence."""

from __future__ import annotations

import os
from typing import Any, Mapping

from verification_platform.nonprofits import Form990NonprofitPersistenceService
from verification_platform.nonprofits import EoBmfNonprofitPersistenceService
from verification_platform.runtime import build_nonprofit_postgres_repository

from .persist.archive_metadata import Form990ArchiveMetadataService


def build_form990_nonprofit_persistence_service(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> Form990NonprofitPersistenceService | None:
    repository = build_nonprofit_postgres_repository(
        env or os.environ,
        sqlalchemy_url=sqlalchemy_url,
        secrets_client=secrets_client,
    )
    if repository is None:
        return None
    return Form990NonprofitPersistenceService(repository)


def build_eo_bmf_nonprofit_persistence_service(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> EoBmfNonprofitPersistenceService | None:
    repository = build_nonprofit_postgres_repository(
        env or os.environ,
        sqlalchemy_url=sqlalchemy_url,
        secrets_client=secrets_client,
    )
    if repository is None:
        return None
    return EoBmfNonprofitPersistenceService(repository)

def build_form990_archive_metadata_service(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> Form990ArchiveMetadataService:
    repository = build_nonprofit_postgres_repository(
        env or os.environ,
        sqlalchemy_url=sqlalchemy_url,
        secrets_client=secrets_client,
    )
    if repository is None:
        raise ValueError("PostgreSQL nonprofit repository is required for Form 990 archive metadata tracking")
    return Form990ArchiveMetadataService(repository)


__all__ = [
    "build_eo_bmf_nonprofit_persistence_service",
    "build_form990_archive_metadata_service",
    "build_form990_nonprofit_persistence_service",
]


