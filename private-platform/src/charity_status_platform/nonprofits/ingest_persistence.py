from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .sqlalchemy_repository import (
    NonprofitFilingRecord,
    NonprofitRecord,
    NonprofitSourceRecord,
    SqlAlchemyNonprofitRepository,
    build_nonprofit_id,
)


IGNORED_PARSE_STATUSES = {"malformed_xml", "parse_error"}


@dataclass(frozen=True)
class Form990PersistenceStats:
    nonprofits_upserted: int
    filings_upserted: int
    sources_upserted: int
    skipped_records: int

    def to_dict(self) -> dict[str, int]:
        return {
            "nonprofits_upserted": self.nonprofits_upserted,
            "filings_upserted": self.filings_upserted,
            "sources_upserted": self.sources_upserted,
            "skipped_records": self.skipped_records,
        }


class Form990NonprofitPersistenceService:
    def __init__(self, repository: SqlAlchemyNonprofitRepository) -> None:
        self._repository = repository

    def persist_normalized_records(
        self,
        filing_records: list[dict[str, Any]],
        *,
        persisted_at: datetime | None = None,
    ) -> Form990PersistenceStats:
        written_nonprofits: set[str] = set()
        nonprofits_upserted = 0
        filings_upserted = 0
        sources_upserted = 0
        skipped_records = 0
        persisted_at_iso = _format_timestamp(persisted_at or datetime.now(timezone.utc))

        for filing in filing_records:
            ein = _normalize_ein(filing.get("ein"))
            if not ein:
                skipped_records += 1
                continue

            nonprofit_id = build_nonprofit_id(ein)
            if nonprofit_id not in written_nonprofits:
                existing = self._repository.get_nonprofit_by_ein(ein)
                nonprofit_record = NonprofitRecord(
                    nonprofit_id=nonprofit_id,
                    ein=ein,
                    canonical_name=(existing.canonical_name if existing else None) or f"EIN {ein}",
                    normalized_name=(existing.normalized_name if existing else None) or f"ein {ein}",
                    subsection_code=existing.subsection_code if existing else None,
                    deductibility_code=existing.deductibility_code if existing else None,
                    tax_deductible=existing.tax_deductible if existing else None,
                    entity_type=existing.entity_type if existing else None,
                    irs_status=existing.irs_status if existing else None,
                    revoked=existing.revoked if existing else False,
                    country=existing.country if existing else "US",
                    state=existing.state if existing else None,
                    ntee_category=existing.ntee_category if existing else None,
                    canonical_source="irs.form990",
                    source_version=str(filing.get("source_signature") or existing.source_version if existing else "") or None,
                    last_seen_at=persisted_at_iso,
                    created_at=existing.created_at if existing else persisted_at_iso,
                    updated_at=persisted_at_iso,
                )
                self._repository.upsert_nonprofit(nonprofit_record)
                written_nonprofits.add(nonprofit_id)
                nonprofits_upserted += 1

            self._repository.upsert_filing(_to_filing_record(nonprofit_id, filing, persisted_at_iso))
            filings_upserted += 1

            parse_status = str(filing.get("parse_status") or "").strip().lower()
            if parse_status in IGNORED_PARSE_STATUSES:
                continue
            self._repository.upsert_source(_to_source_record(nonprofit_id, filing, persisted_at_iso))
            sources_upserted += 1

        return Form990PersistenceStats(
            nonprofits_upserted=nonprofits_upserted,
            filings_upserted=filings_upserted,
            sources_upserted=sources_upserted,
            skipped_records=skipped_records,
        )


def _to_filing_record(nonprofit_id: str, filing: dict[str, Any], persisted_at_iso: str) -> NonprofitFilingRecord:
    return NonprofitFilingRecord(
        filing_id=_filing_id(nonprofit_id, filing),
        nonprofit_id=nonprofit_id,
        tax_year=_to_int(filing.get("tax_year")),
        tax_period=str(filing.get("tax_period_end") or filing.get("tax_period_begin") or "").strip() or None,
        form_type=str(filing.get("return_type") or "unknown").strip() or "unknown",
        filing_date=str(filing.get("filing_date") or "").strip() or None,
        amended=bool(filing.get("amended_return")),
        parse_status=str(filing.get("parse_status") or "").strip() or None,
        total_assets=_to_int(filing.get("total_assets_eoy")),
        total_income=_to_int(filing.get("total_income")),
        total_revenue=_to_int(filing.get("total_revenue")),
        source_name="irs.form990",
        source_record_id=str(filing.get("irs_object_id") or "").strip() or None,
        source_signature=str(filing.get("source_signature") or "").strip() or None,
        xml_source_reference=str(filing.get("xml_source_reference") or "").strip() or None,
        raw_s3_key=str(filing.get("raw_s3_key") or "").strip() or None,
        raw_payload=dict(filing),
        created_at=persisted_at_iso,
        updated_at=persisted_at_iso,
    )


def _to_source_record(nonprofit_id: str, filing: dict[str, Any], persisted_at_iso: str) -> NonprofitSourceRecord:
    return NonprofitSourceRecord(
        nonprofit_source_id=_source_id(nonprofit_id, filing),
        nonprofit_id=nonprofit_id,
        source_id="irs.form990_filing",
        provider_name="irs",
        category="financial",
        record_id=str(filing.get("irs_object_id") or filing.get("source_archive") or "").strip() or None,
        retrieved_at=persisted_at_iso,
        status=str(filing.get("parse_status") or "").strip() or None,
        driver="form990_ingest",
        licensed=False,
        source_signature=str(filing.get("source_signature") or "").strip() or None,
        normalized_data={
            "source_year": filing.get("source_year"),
            "source_archive": filing.get("source_archive"),
            "source_signature": filing.get("source_signature"),
            "xml_source_reference": filing.get("xml_source_reference"),
            "raw_s3_key": filing.get("raw_s3_key"),
            "tax_year": filing.get("tax_year"),
            "filing_date": filing.get("filing_date"),
            "return_type": filing.get("return_type"),
        },
        raw_payload=dict(filing),
        created_at=persisted_at_iso,
        updated_at=persisted_at_iso,
    )


def _filing_id(nonprofit_id: str, filing: dict[str, Any]) -> str:
    irs_object_id = str(filing.get("irs_object_id") or "").strip()
    if irs_object_id:
        payload = f"{nonprofit_id}|irs_object_id|{irs_object_id}"
    else:
        payload = "|".join(
            [
                nonprofit_id,
                str(filing.get("tax_year") or "").strip(),
                str(filing.get("return_type") or "").strip(),
                str(filing.get("filing_date") or "").strip(),
                str(filing.get("source_archive") or "").strip(),
            ]
        )
    return f"fil_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _source_id(nonprofit_id: str, filing: dict[str, Any]) -> str:
    payload = "|".join(
        [
            nonprofit_id,
            "irs.form990_filing",
            str(filing.get("irs_object_id") or "").strip(),
            str(filing.get("source_archive") or "").strip(),
        ]
    )
    return f"src_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _normalize_ein(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())[:9]


def _to_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
