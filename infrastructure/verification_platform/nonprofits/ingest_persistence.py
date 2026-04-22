from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from verification.ops import ProgressSession

from .sqlalchemy_repository import (
    NonprofitFilingRecord,
    NonprofitRecord,
    NonprofitRawFilingRecord,
    NonprofitSourceRecord,
    SqlAlchemyNonprofitRepository,
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
        canonical_raw_filing_records: list[dict[str, Any]] | None = None,
        persisted_at: datetime | None = None,
        progress_session: ProgressSession | None = None,
    ) -> Form990PersistenceStats:
        written_nonprofits: set[int] = set()
        nonprofits_upserted = 0
        filings_upserted = 0
        sources_upserted = 0
        skipped_records = 0
        persisted_at_iso = _format_timestamp(persisted_at or datetime.now(timezone.utc))
        raw_filing_lookup = {
            _canonical_raw_lookup_key(item): item
            for item in (canonical_raw_filing_records or [])
            if _canonical_raw_lookup_key(item) is not None
        }

        for filing in filing_records:
            ein = _normalize_ein(filing.get("ein"))
            if not ein:
                skipped_records += 1
                if progress_session is not None:
                    progress_session.item_completed({"skipped_records": 1})
                continue

            existing = self._repository.get_nonprofit_by_ein(ein)
            nonprofit_id = existing.nonprofit_id if existing is not None else None
            if nonprofit_id is None or nonprofit_id not in written_nonprofits:
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
                persisted_nonprofit = self._repository.upsert_nonprofit(nonprofit_record)
                nonprofit_id = persisted_nonprofit.nonprofit_id
                if nonprofit_id is None:
                    skipped_records += 1
                    if progress_session is not None:
                        progress_session.item_completed({"skipped_records": 1})
                    continue
                written_nonprofits.add(nonprofit_id)
                nonprofits_upserted += 1
            assert nonprofit_id is not None

            persisted_filing = self._repository.upsert_filing(_to_filing_record(nonprofit_id, filing, persisted_at_iso))
            filings_upserted += 1

            raw_filing_payload = raw_filing_lookup.get(_filing_lookup_key(filing))
            if raw_filing_payload is not None:
                self._repository.upsert_raw_filing(
                    _to_raw_filing_record(
                        nonprofit_id,
                        persisted_filing.filing_id,
                        raw_filing_payload,
                        persisted_at_iso,
                    )
                )

            parse_status = str(filing.get("parse_status") or "").strip().lower()
            if parse_status in IGNORED_PARSE_STATUSES:
                if progress_session is not None:
                    progress_session.item_completed({"filings_upserted": 1})
                continue
            self._repository.upsert_source(_to_source_record(nonprofit_id, filing, persisted_at_iso))
            sources_upserted += 1
            if progress_session is not None:
                progress_session.item_completed({"filings_upserted": 1, "sources_upserted": 1})

        return Form990PersistenceStats(
            nonprofits_upserted=nonprofits_upserted,
            filings_upserted=filings_upserted,
            sources_upserted=sources_upserted,
            skipped_records=skipped_records,
        )


def _to_filing_record(nonprofit_id: int, filing: dict[str, Any], persisted_at_iso: str) -> NonprofitFilingRecord:
    return NonprofitFilingRecord(
        filing_id=None,
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
        raw_file_reference=str(filing.get("raw_file_reference") or "").strip() or None,
        raw_payload=dict(filing),
        created_at=persisted_at_iso,
        updated_at=persisted_at_iso,
    )


def _to_source_record(nonprofit_id: int, filing: dict[str, Any], persisted_at_iso: str) -> NonprofitSourceRecord:
    return NonprofitSourceRecord(
        nonprofit_source_id=None,
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
            "raw_file_reference": filing.get("raw_file_reference"),
            "tax_year": filing.get("tax_year"),
            "filing_date": filing.get("filing_date"),
            "return_type": filing.get("return_type"),
        },
        raw_payload=dict(filing),
        created_at=persisted_at_iso,
        updated_at=persisted_at_iso,
    )


def _to_raw_filing_record(
    nonprofit_id: int,
    filing_id: int | None,
    raw_filing: dict[str, Any],
    persisted_at_iso: str,
) -> NonprofitRawFilingRecord:
    assert filing_id is not None
    return NonprofitRawFilingRecord(
        raw_filing_id=None,
        nonprofit_id=nonprofit_id,
        filing_id=filing_id,
        tax_year=_to_int(raw_filing.get("tax_year")),
        form_type=str(raw_filing.get("form_type") or "unknown").strip() or "unknown",
        filing_date=str(raw_filing.get("filing_date") or "").strip() or None,
        source_name=str(raw_filing.get("source_name") or "").strip() or None,
        source_record_id=str(raw_filing.get("source_record_id") or "").strip() or None,
        source_signature=str(raw_filing.get("source_signature") or "").strip() or None,
        xml_content_hash=str(raw_filing.get("xml_content_hash") or "").strip(),
        xml_artifact_reference=str(raw_filing.get("xml_artifact_reference") or "").strip() or None,
        parse_status=str(raw_filing.get("parse_status") or "").strip() or None,
        parser_version=str(raw_filing.get("parser_version") or "").strip(),
        canonicalization_version=str(raw_filing.get("canonicalization_version") or "").strip(),
        raw_filing_json=dict(raw_filing.get("raw_filing_json") or {}),
        created_at=persisted_at_iso,
        updated_at=persisted_at_iso,
    )


def _filing_lookup_key(filing: dict[str, Any]) -> tuple[str | None, str | None]:
    return (
        str(filing.get("irs_object_id") or "").strip() or None,
        str(filing.get("raw_file_reference") or filing.get("xml_source_reference") or "").strip() or None,
    )


def _canonical_raw_lookup_key(raw_filing: dict[str, Any]) -> tuple[str | None, str | None] | None:
    key = (
        str(raw_filing.get("source_record_id") or "").strip() or None,
        str(raw_filing.get("xml_artifact_reference") or "").strip() or None,
    )
    if key == (None, None):
        return None
    return key
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

