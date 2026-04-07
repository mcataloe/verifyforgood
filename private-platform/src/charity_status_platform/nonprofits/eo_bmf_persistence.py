from __future__ import annotations

from dataclasses import dataclass

from .sqlalchemy_repository import (
    NonprofitBatchUpsertStats,
    NonprofitFilingRecord,
    NonprofitRecord,
    SqlAlchemyNonprofitRepository,
)


DEFAULT_EO_BMF_BATCH_SIZE = 500


@dataclass(frozen=True)
class EoBmfPersistenceStats:
    nonprofits_upserted: int
    filings_upserted: int
    nonprofit_upsert_duration_ms: int
    filing_upsert_duration_ms: int

    @property
    def db_upsert_duration_ms(self) -> int:
        return self.nonprofit_upsert_duration_ms + self.filing_upsert_duration_ms


class EoBmfNonprofitPersistenceService:
    def __init__(self, repository: SqlAlchemyNonprofitRepository) -> None:
        self._repository = repository

    def persist_batch(
        self,
        records: list[tuple[NonprofitRecord, NonprofitFilingRecord]],
    ) -> EoBmfPersistenceStats:
        result: NonprofitBatchUpsertStats = self._repository.upsert_nonprofits_and_filings_batch(records)
        return EoBmfPersistenceStats(
            nonprofits_upserted=result.nonprofits_upserted,
            filings_upserted=result.filings_upserted,
            nonprofit_upsert_duration_ms=result.nonprofit_upsert_duration_ms,
            filing_upsert_duration_ms=result.filing_upsert_duration_ms,
        )


__all__ = [
    "DEFAULT_EO_BMF_BATCH_SIZE",
    "EoBmfNonprofitPersistenceService",
    "EoBmfPersistenceStats",
]
