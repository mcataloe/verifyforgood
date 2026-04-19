from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy import text

from verification_platform.customer_accounts import CustomerAccountsBase

from .sqlalchemy_models import (
    ComplianceCheckModel,
    Form990ArchiveModel,
    Form990ExtractedFileModel,
    NonprofitFilingModel,
    NonprofitModel,
    NonprofitRawFilingModel,
    NonprofitSourceModel,
)


NONPROFIT_TABLES = (
    NonprofitModel.__table__,
    NonprofitFilingModel.__table__,
    NonprofitRawFilingModel.__table__,
    NonprofitSourceModel.__table__,
    ComplianceCheckModel.__table__,
    Form990ArchiveModel.__table__,
    Form990ExtractedFileModel.__table__,
)

NONPROFIT_TABLE_NAMES = tuple(table.name for table in NONPROFIT_TABLES)


def create_nonprofit_tables(bind: Engine) -> None:
    CustomerAccountsBase.metadata.create_all(bind, tables=list(NONPROFIT_TABLES))


def drop_nonprofit_tables(bind: Engine, *, include_version_table: bool = False) -> None:
    CustomerAccountsBase.metadata.drop_all(bind, tables=list(reversed(NONPROFIT_TABLES)))
    if include_version_table:
        with bind.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version_nonprofit"))

