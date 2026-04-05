"""EO/BMF CSV ingestion helpers for the backend-owned runtime."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from charity_status.normalization import map_deductibility, map_entity_type, map_irs_status, map_ntee_category
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


@dataclass(frozen=True)
class EoBmfFileIngestStats:
    filename: str
    status: str
    rows_seen: int
    nonprofits_upserted: int
    filings_upserted: int
    invalid_rows: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "filename": self.filename,
            "status": self.status,
            "rows_seen": self.rows_seen,
            "nonprofits_upserted": self.nonprofits_upserted,
            "filings_upserted": self.filings_upserted,
            "invalid_rows": self.invalid_rows,
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
    processed = processed_at or datetime.now(timezone.utc)
    processed_at_iso = processed.replace(microsecond=0).isoformat()
    rows_seen = 0
    nonprofits_upserted = 0
    filings_upserted = 0
    invalid_rows = 0

    for row in iter_eo_bmf_rows(path):
        rows_seen += 1
        mapped = _map_row_to_records(row=row, filename=filename, processed_at_iso=processed_at_iso)
        if mapped is None:
            invalid_rows += 1
            continue
        nonprofit = repository.upsert_nonprofit(mapped["nonprofit"])
        repository.upsert_filing(
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
        nonprofits_upserted += 1
        filings_upserted += 1

    status = "success" if nonprofits_upserted or rows_seen == 0 else "partial_success"
    if nonprofits_upserted == 0 and invalid_rows == rows_seen and rows_seen > 0:
        status = "failed"
    return EoBmfFileIngestStats(
        filename=filename,
        status=status,
        rows_seen=rows_seen,
        nonprofits_upserted=nonprofits_upserted,
        filings_upserted=filings_upserted,
        invalid_rows=invalid_rows,
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

    nonprofit = NonprofitRecord(
        nonprofit_id=None,
        ein=ein,
        canonical_name=canonical_name,
        normalized_name=canonical_name.lower(),
        subsection_code=subsection,
        deductibility_code=deductibility,
        tax_deductible=map_deductibility(deductibility),
        entity_type=map_entity_type(subsection),
        irs_status=map_irs_status(row.get("status")),
        revoked=map_irs_status(row.get("status")) == "inactive",
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


__all__ = [
    "EO_BMF_CANONICAL_SOURCE",
    "EO_BMF_COLUMNS",
    "EO_BMF_FILING_FORM_TYPE",
    "EoBmfFileIngestStats",
    "ingest_eo_bmf_csv",
    "iter_eo_bmf_rows",
]
