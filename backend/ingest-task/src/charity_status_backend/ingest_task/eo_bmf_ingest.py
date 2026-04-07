"""EO/BMF CSV ingestion helpers for the backend-owned runtime."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Iterable, Mapping

from charity_status.normalization import map_deductibility, map_entity_type, map_irs_status, map_ntee_category
from charity_status.runtime_logging import configure_runtime_logging, log_structured
from charity_status_platform.nonprofits import NonprofitFilingRecord, NonprofitRecord, SqlAlchemyNonprofitRepository


EO_BMF_COLUMNS = (
    "ein",
    "name",
    "ico",
    "street",
    "city",
    "state",
    "zip",
    "group_name",
    "subsection",
    "affiliation",
    "classification",
    "ruling",
    "deductibility",
    "foundation",
    "activity",
    "organization",
    "status",
    "tax_period",
    "asset_cd",
    "income_cd",
    "filing_req_cd",
    "pf_filing_req_cd",
    "acct_pd",
    "asset_amt",
    "income_amt",
    "revenue_amt",
    "ntee_cd",
    "sort_name",
)
EO_BMF_CANONICAL_SOURCE = "irs.eo_bmf"
EO_BMF_FILING_FORM_TYPE = "EO_BMF"
EO_BMF_RECORD_LOG_UPDATE_EVERY = 10
LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(logger=LOGGER)


@dataclass(frozen=True)
class EoBmfFileIngestStats:
    filename: str
    status: str
    rows_seen: int
    nonprofits_upserted: int
    filings_upserted: int
    invalid_rows: int
    map_duration_ms: int
    nonprofit_upsert_duration_ms: int
    filing_upsert_duration_ms: int
    db_upsert_duration_ms: int
    rows_per_second: float
    nonprofit_upserts_per_second: float
    filing_upserts_per_second: float
    invalid_row_rate: float
    db_time_share: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "filename": self.filename,
            "status": self.status,
            "rows_seen": self.rows_seen,
            "nonprofits_upserted": self.nonprofits_upserted,
            "filings_upserted": self.filings_upserted,
            "invalid_rows": self.invalid_rows,
            "map_duration_ms": self.map_duration_ms,
            "nonprofit_upsert_duration_ms": self.nonprofit_upsert_duration_ms,
            "filing_upsert_duration_ms": self.filing_upsert_duration_ms,
            "db_upsert_duration_ms": self.db_upsert_duration_ms,
            "rows_per_second": self.rows_per_second,
            "nonprofit_upserts_per_second": self.nonprofit_upserts_per_second,
            "filing_upserts_per_second": self.filing_upserts_per_second,
            "invalid_row_rate": self.invalid_row_rate,
            "db_time_share": self.db_time_share,
        }
        if self.error:
            payload["error"] = self.error
        return payload


def ingest_eo_bmf_csv(
    *,
    path: str,
    filename: str,
    repository: SqlAlchemyNonprofitRepository,
    processed_at: datetime | None = None,
) -> EoBmfFileIngestStats:
    perf_counter = time.perf_counter
    upsert_nonprofit = repository.upsert_nonprofit
    upsert_filing = repository.upsert_filing
    processed = processed_at or datetime.now(timezone.utc)
    processed_at_iso = processed.replace(microsecond=0).isoformat()
    total_rows = _count_eo_bmf_rows(path) if LOGGER.isEnabledFor(logging.DEBUG) else None
    rows_seen = 0
    nonprofits_upserted = 0
    filings_upserted = 0
    invalid_rows = 0
    map_duration_ms = 0
    nonprofit_upsert_duration_ms = 0
    filing_upsert_duration_ms = 0

    for row in iter_eo_bmf_rows(path):
        rows_seen += 1
        map_started_at = perf_counter()
        mapped = _map_row_to_records(row=row, filename=filename, processed_at_iso=processed_at_iso)
        map_duration_ms += _elapsed_ms(map_started_at)
        if mapped is None:
            invalid_rows += 1
            continue
        nonprofit_upsert_started_at = perf_counter()
        nonprofit = upsert_nonprofit(mapped["nonprofit"])
        nonprofit_upsert_duration_ms += _elapsed_ms(nonprofit_upsert_started_at)
        filing_upsert_started_at = perf_counter()
        upsert_filing(
            NonprofitFilingRecord(
                filing_id=None,
                nonprofit_id=nonprofit.nonprofit_id,
                tax_year=mapped["tax_year"],
                tax_period=mapped["tax_period"],
                form_type=EO_BMF_FILING_FORM_TYPE,
                filing_date=None,
                amended=False,
                parse_status="parsed",
                total_assets=mapped["total_assets"],
                total_income=mapped["total_income"],
                total_revenue=mapped["total_revenue"],
                source_name=EO_BMF_CANONICAL_SOURCE,
                source_record_id=mapped["source_record_id"],
                raw_payload=mapped["raw_payload"],
                created_at=processed_at_iso,
                updated_at=processed_at_iso,
            )
        )
        _log_record_progress(filename=filename, rows_seen=rows_seen, total_rows=total_rows)
        filing_upsert_duration_ms += _elapsed_ms(filing_upsert_started_at)
        nonprofits_upserted += 1
        filings_upserted += 1

    status = "success" if nonprofits_upserted or rows_seen == 0 else "partial_success"
    if nonprofits_upserted == 0 and invalid_rows == rows_seen and rows_seen > 0:
        status = "failed"
    db_upsert_duration_ms = nonprofit_upsert_duration_ms + filing_upsert_duration_ms
    return EoBmfFileIngestStats(
        filename=filename,
        status=status,
        rows_seen=rows_seen,
        nonprofits_upserted=nonprofits_upserted,
        filings_upserted=filings_upserted,
        invalid_rows=invalid_rows,
        map_duration_ms=map_duration_ms,
        nonprofit_upsert_duration_ms=nonprofit_upsert_duration_ms,
        filing_upsert_duration_ms=filing_upsert_duration_ms,
        db_upsert_duration_ms=db_upsert_duration_ms,
        rows_per_second=_items_per_second(rows_seen, map_duration_ms + db_upsert_duration_ms),
        nonprofit_upserts_per_second=_items_per_second(nonprofits_upserted, nonprofit_upsert_duration_ms),
        filing_upserts_per_second=_items_per_second(filings_upserted, filing_upsert_duration_ms),
        invalid_row_rate=_ratio(invalid_rows, rows_seen),
        db_time_share=_ratio(db_upsert_duration_ms, map_duration_ms + db_upsert_duration_ms),
    )


def iter_eo_bmf_rows(path: str) -> Iterable[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            if not raw_row:
                continue
            if not any(str(value or "").strip() for value in raw_row):
                continue
            padded = list(raw_row[: len(EO_BMF_COLUMNS)])
            if len(padded) < len(EO_BMF_COLUMNS):
                padded.extend([""] * (len(EO_BMF_COLUMNS) - len(padded)))
            yield {
                column: str(value or "").strip()
                for column, value in zip(EO_BMF_COLUMNS, padded)
            }


def _count_eo_bmf_rows(path: str) -> int:
    return sum(1 for _ in iter_eo_bmf_rows(path))


def _map_row_to_records(
    *,
    row: Mapping[str, str],
    filename: str,
    processed_at_iso: str,
) -> dict[str, Any] | None:
    ein = _normalize_ein(row.get("ein"))
    if len(ein) != 9:
        return None

    canonical_name = _text(row.get("name")) or f"EIN {ein}"
    subsection = _text(row.get("subsection"))
    deductibility = _text(row.get("deductibility"))
    tax_period = _text(row.get("tax_period"))
    tax_year = _tax_year_from_period(tax_period)
    total_assets = _to_int(row.get("asset_amt"))
    total_income = _to_int(row.get("income_amt"))
    total_revenue = _to_int(row.get("revenue_amt"))
    irs_status = map_irs_status(row.get("status"))

    nonprofit = NonprofitRecord(
        nonprofit_id=None,
        ein=ein,
        canonical_name=canonical_name,
        normalized_name=canonical_name.lower(),
        subsection_code=subsection,
        deductibility_code=deductibility,
        tax_deductible=map_deductibility(deductibility),
        entity_type=map_entity_type(subsection),
        irs_status=irs_status,
        revoked=irs_status == "inactive",
        country="US",
        state=_text(row.get("state")),
        ntee_category=map_ntee_category(_text(row.get("ntee_cd"))),
        canonical_source=EO_BMF_CANONICAL_SOURCE,
        source_version=filename,
        last_seen_at=processed_at_iso,
        created_at=processed_at_iso,
        updated_at=processed_at_iso,
    )
    return {
        "nonprofit": nonprofit,
        "tax_year": tax_year,
        "tax_period": tax_period,
        "total_assets": total_assets,
        "total_income": total_income,
        "total_revenue": total_revenue,
        "source_record_id": f"{ein}:{filename}:{tax_period or ''}",
        "raw_payload": dict(row),
    }


def _normalize_ein(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())[:9]


def _tax_year_from_period(value: str | None) -> int | None:
    text = _text(value)
    if text is None or len(text) < 4:
        return None
    try:
        return int(text[:4])
    except ValueError:
        return None


def _to_int(value: str | None) -> int | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _text(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))


def _log_record_progress(*, filename: str, rows_seen: int, total_rows: int | None) -> None:
    if not LOGGER.isEnabledFor(logging.DEBUG):
        return
    if rows_seen % EO_BMF_RECORD_LOG_UPDATE_EVERY != 0 and (total_rows is None or rows_seen != total_rows):
        return
    log_structured(
        LOGGER,
        "eo_bmf.ingest.record_progress",
        level=logging.DEBUG,
        filename=filename,
        records_processed=rows_seen,
        total_records=total_rows,
    )


def _items_per_second(count: int, duration_ms: int) -> float:
    if count <= 0 or duration_ms <= 0:
        return 0.0
    return round(count / (duration_ms / 1000.0), 2)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


__all__ = [
    "EO_BMF_CANONICAL_SOURCE",
    "EO_BMF_COLUMNS",
    "EO_BMF_FILING_FORM_TYPE",
    "EoBmfFileIngestStats",
    "ingest_eo_bmf_csv",
    "iter_eo_bmf_rows",
]
