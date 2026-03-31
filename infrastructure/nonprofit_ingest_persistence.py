from __future__ import annotations

import os
from typing import Any, Mapping

from charity_status_platform.nonprofits import Form990NonprofitPersistenceService
from charity_status_platform.runtime import build_nonprofit_postgres_repository


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
