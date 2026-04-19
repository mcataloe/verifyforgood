from __future__ import annotations

from sqlalchemy.engine import Engine

from charity_status_platform.customer_accounts import CustomerAccountsBase

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


def create_nonprofit_tables(bind: Engine) -> None:
    CustomerAccountsBase.metadata.create_all(bind, tables=list(NONPROFIT_TABLES))
