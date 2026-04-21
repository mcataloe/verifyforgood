from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
import time
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from .sqlalchemy_db import nonprofit_session_scope

from .sqlalchemy_models import (
    ComplianceCheckModel,
    Form990ArchiveModel,
    Form990ExtractedFileModel,
    NonprofitFilingModel,
    NonprofitModel,
    NonprofitRawFilingModel,
    NonprofitSourceModel,
)


@dataclass(frozen=True)
class NonprofitRecord:
    nonprofit_id: int | None
    ein: str
    canonical_name: str
    normalized_name: str
    subsection_code: str | None = None
    deductibility_code: str | None = None
    tax_deductible: bool | None = None
    entity_type: str | None = None
    irs_status: str | None = None
    revoked: bool = False
    country: str | None = None
    state: str | None = None
    ntee_category: str | None = None
    canonical_source: str | None = None
    source_version: str | None = None
    last_seen_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NonprofitFilingRecord:
    filing_id: int | None
    nonprofit_id: int
    tax_year: int | None
    tax_period: str | None
    form_type: str
    filing_date: str | None
    amended: bool
    parse_status: str | None
    total_assets: int | None = None
    total_income: int | None = None
    total_revenue: int | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    source_signature: str | None = None
    xml_source_reference: str | None = None
    raw_file_reference: str | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NonprofitSourceRecord:
    nonprofit_source_id: int | None
    nonprofit_id: int
    source_id: str
    provider_name: str
    category: str
    record_id: str | None
    retrieved_at: str
    valid_as_of: str | None = None
    expires_at: str | None = None
    status: str | None = None
    driver: str | None = None
    integration_id: str | None = None
    tenant_enabled: bool | None = None
    required_for_eligibility: bool | None = None
    evaluation_effect: str | None = None
    explanation_code: str | None = None
    explanation: str | None = None
    licensed: bool | None = None
    notes: str | None = None
    source_signature: str | None = None
    normalized_data: dict[str, Any] | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NonprofitRawFilingRecord:
    raw_filing_id: int | None
    nonprofit_id: int
    filing_id: int
    tax_year: int | None
    form_type: str
    filing_date: str | None
    source_name: str | None
    source_record_id: str | None
    source_signature: str | None
    xml_content_hash: str
    xml_artifact_reference: str | None
    parse_status: str | None
    parser_version: str
    canonicalization_version: str
    raw_filing_json: dict[str, Any]
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ComplianceCheckRecord:
    compliance_check_id: int | None
    nonprofit_id: int
    check_type: str
    status: str
    evaluated_at: str
    policy_version: str | None = None
    model_version: str | None = None
    source_hash: str | None = None
    environment: str | None = None
    registration_status: str | None = None
    registration_jurisdiction: str | None = None
    registration_expiration_date: str | None = None
    solicitation_permitted: bool | None = None
    state_business_status: str | None = None
    state_business_good_standing: bool | None = None
    final_recommendation: str | None = None
    flags_json: dict[str, Any] | list[Any] | None = None
    reasons_json: dict[str, Any] | list[Any] | None = None
    evidence_json: dict[str, Any] | list[Any] | None = None
    summary_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: str = ""


@dataclass(frozen=True)
class Form990ArchiveRecord:
    archive_id: int | None
    source_url: str
    filename: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    content_length: int | None = None
    response_status: int | None = None
    last_checked_at: str | None = None
    last_processed_at: str | None = None
    status: str | None = None
    created_at: str = ""
    update_started_at: str = ""
    update_ended_at: str | None = None
    processing_duration_ms: int | None = None


@dataclass(frozen=True)
class Form990ExtractedFileRecord:
    file_id: int | None
    archive_id: int
    filename: str
    content_hash: str | None = None
    parse_status: str | None = None
    parsed_at: str | None = None
    error_message: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NonprofitBatchUpsertStats:
    nonprofits_upserted: int
    filings_upserted: int
    nonprofit_upsert_duration_ms: int
    filing_upsert_duration_ms: int


class SqlAlchemyNonprofitRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert_nonprofit(self, record: NonprofitRecord) -> NonprofitRecord:
        with nonprofit_session_scope(self._session_factory) as session:
            normalized_record = _normalized_nonprofit_record(record)
            _execute_upsert(
                session,
                NonprofitModel,
                values=_nonprofit_values(normalized_record),
                conflict_columns=["ein"],
                update_values=_nonprofit_update_values(normalized_record),
            )
            model = session.scalar(
                select(NonprofitModel).where(NonprofitModel.ein == normalized_record.ein).limit(1)
            )
            assert model is not None
            return _nonprofit_record(model)

    def get_nonprofit_by_ein(self, ein: str) -> NonprofitRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            model = session.scalar(select(NonprofitModel).where(NonprofitModel.ein == _normalize_ein(ein)).limit(1))
            return None if model is None else _nonprofit_record(model)

    def get_nonprofit_snapshot_by_ein(self, ein: str) -> dict[str, Any] | None:
        latest_filing = _latest_filing_subquery()
        with nonprofit_session_scope(self._session_factory) as session:
            row = session.execute(
                select(
                    NonprofitModel.ein,
                    NonprofitModel.canonical_name,
                    NonprofitModel.state,
                    NonprofitModel.subsection_code,
                    NonprofitModel.irs_status,
                    NonprofitModel.deductibility_code,
                    NonprofitModel.ntee_category,
                    latest_filing.c.tax_period,
                    latest_filing.c.total_assets,
                    latest_filing.c.total_income,
                    latest_filing.c.total_revenue,
                )
                .outerjoin(latest_filing, latest_filing.c.nonprofit_id == NonprofitModel.nonprofit_id)
                .where(NonprofitModel.ein == _normalize_ein(ein))
                .limit(1)
            ).mappings().first()
            return None if row is None else _snapshot_row(dict(row))

    def upsert_filing(self, record: NonprofitFilingRecord) -> NonprofitFilingRecord:
        with nonprofit_session_scope(self._session_factory) as session:
            normalized_record = _normalized_filing_record(record)
            _execute_upsert(
                session,
                NonprofitFilingModel,
                values=_filing_values(normalized_record),
                conflict_columns=["nonprofit_id", "tax_year", "form_type", "filing_date", "source_name"],
                update_values=_filing_update_values(normalized_record),
            )
            model = session.scalar(
                select(NonprofitFilingModel)
                .where(
                    NonprofitFilingModel.nonprofit_id == normalized_record.nonprofit_id,
                    NonprofitFilingModel.tax_year == normalized_record.tax_year,
                    NonprofitFilingModel.form_type == normalized_record.form_type,
                    NonprofitFilingModel.filing_date == _parse_date(normalized_record.filing_date),
                    NonprofitFilingModel.source_name == normalized_record.source_name,
                )
                .limit(1)
            )
            assert model is not None
        return _filing_record(model)

    def upsert_raw_filing(self, record: NonprofitRawFilingRecord) -> NonprofitRawFilingRecord:
        with nonprofit_session_scope(self._session_factory) as session:
            normalized_record = _normalized_raw_filing_record(record)
            _execute_upsert(
                session,
                NonprofitRawFilingModel,
                values=_raw_filing_values(normalized_record),
                conflict_columns=["filing_id", "xml_content_hash"],
                update_values=_raw_filing_update_values(normalized_record),
            )
            model = session.scalar(
                select(NonprofitRawFilingModel)
                .where(
                    NonprofitRawFilingModel.filing_id == normalized_record.filing_id,
                    NonprofitRawFilingModel.xml_content_hash == normalized_record.xml_content_hash,
                )
                .limit(1)
            )
            assert model is not None
        return _raw_filing_record(model)

    def upsert_nonprofits_and_filings_batch(
        self,
        records: list[tuple[NonprofitRecord, NonprofitFilingRecord]],
    ) -> NonprofitBatchUpsertStats:
        if not records:
            return NonprofitBatchUpsertStats(
                nonprofits_upserted=0,
                filings_upserted=0,
                nonprofit_upsert_duration_ms=0,
                filing_upsert_duration_ms=0,
            )

        normalized_pairs = [
            (_normalized_nonprofit_record(nonprofit), _normalized_filing_record(filing))
            for nonprofit, filing in records
        ]
        nonprofits_by_ein: dict[str, NonprofitRecord] = {}
        for nonprofit, _filing in normalized_pairs:
            nonprofits_by_ein[nonprofit.ein] = nonprofit

        perf_counter = time.perf_counter
        with nonprofit_session_scope(self._session_factory) as session:
            nonprofit_started_at = perf_counter()
            nonprofit_values = [_nonprofit_values(record) for record in nonprofits_by_ein.values()]
            _execute_upsert_many(
                session,
                NonprofitModel,
                values=nonprofit_values,
                conflict_columns=["ein"],
                update_columns=list(_nonprofit_update_values(next(iter(nonprofits_by_ein.values()))).keys()),
            )
            nonprofit_ids = {
                str(row.ein): int(row.nonprofit_id)
                for row in session.execute(
                    select(NonprofitModel.ein, NonprofitModel.nonprofit_id).where(
                        NonprofitModel.ein.in_(list(nonprofits_by_ein.keys()))
                    )
                )
            }
            nonprofit_upsert_duration_ms = _elapsed_ms(perf_counter() - nonprofit_started_at)

            filing_started_at = perf_counter()
            filing_values = [
                _filing_values(replace(filing, nonprofit_id=nonprofit_ids[nonprofit.ein]))
                for nonprofit, filing in normalized_pairs
            ]
            _execute_upsert_many(
                session,
                NonprofitFilingModel,
                values=filing_values,
                conflict_columns=["nonprofit_id", "tax_year", "form_type", "filing_date", "source_name"],
                update_columns=list(_filing_update_values(normalized_pairs[0][1]).keys()),
            )
            filing_upsert_duration_ms = _elapsed_ms(perf_counter() - filing_started_at)

        return NonprofitBatchUpsertStats(
            nonprofits_upserted=len(nonprofits_by_ein),
            filings_upserted=len(normalized_pairs),
            nonprofit_upsert_duration_ms=nonprofit_upsert_duration_ms,
            filing_upsert_duration_ms=filing_upsert_duration_ms,
        )

    def list_filings_for_nonprofit(self, nonprofit_id: int, *, limit: int | None = None) -> list[NonprofitFilingRecord]:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(NonprofitFilingModel)
                .where(NonprofitFilingModel.nonprofit_id == nonprofit_id)
                .order_by(desc(NonprofitFilingModel.tax_year), desc(NonprofitFilingModel.filing_date))
            )
            if limit is not None:
                statement = statement.limit(limit)
            return [_filing_record(model) for model in session.scalars(statement).all()]

    def list_filings_by_ein(self, ein: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(
                    NonprofitModel.ein,
                    NonprofitFilingModel.tax_year,
                    NonprofitFilingModel.form_type,
                    NonprofitFilingModel.filing_date,
                    NonprofitFilingModel.amended,
                    NonprofitFilingModel.parse_status,
                )
                .join(NonprofitFilingModel, NonprofitFilingModel.nonprofit_id == NonprofitModel.nonprofit_id)
                .where(NonprofitModel.ein == _normalize_ein(ein))
                .order_by(desc(NonprofitFilingModel.tax_year), desc(NonprofitFilingModel.filing_date))
            )
            if limit is not None:
                statement = statement.limit(limit)
            rows = session.execute(statement).mappings().all()
            return [_filing_query_row(dict(row)) for row in rows]

    def list_peer_benchmark_filings(
        self,
        *,
        ntee: str | None = None,
        org_type: str | None = None,
        revenue_band: str | None = None,
    ) -> list[dict[str, Any]]:
        latest_filing = _latest_filing_with_payload_subquery()
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(
                    NonprofitModel.ein,
                    NonprofitModel.ntee_category,
                    NonprofitModel.subsection_code,
                    latest_filing.c.total_revenue,
                    latest_filing.c.raw_payload,
                )
                .join(latest_filing, latest_filing.c.nonprofit_id == NonprofitModel.nonprofit_id)
            )
            if ntee and ntee != "unknown":
                statement = statement.where(func.substr(func.coalesce(NonprofitModel.ntee_category, ""), 1, 1) == ntee)
            if org_type and org_type != "unknown":
                statement = statement.where(func.coalesce(NonprofitModel.subsection_code, "") == org_type)
            if revenue_band and revenue_band != "unknown":
                statement = statement.where(_revenue_band_predicate(latest_filing.c.total_revenue, revenue_band))
            rows = session.execute(statement).mappings().all()
            return [dict(row) for row in rows]

    def get_raw_filing_by_identity(
        self,
        *,
        nonprofit_id: int,
        tax_year: int | None,
        form_type: str,
        filing_date: str | None = None,
        source_name: str | None = None,
        content_hash: str | None = None,
    ) -> NonprofitRawFilingRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = select(NonprofitRawFilingModel).where(
                NonprofitRawFilingModel.nonprofit_id == nonprofit_id,
                NonprofitRawFilingModel.tax_year == tax_year,
                NonprofitRawFilingModel.form_type == _normalize_optional_text(form_type),
            )
            if filing_date is not None:
                statement = statement.where(NonprofitRawFilingModel.filing_date == _parse_date(filing_date))
            if source_name is not None:
                statement = statement.where(NonprofitRawFilingModel.source_name == _normalize_optional_text(source_name))
            if content_hash is not None:
                statement = statement.where(
                    NonprofitRawFilingModel.xml_content_hash == _normalize_optional_text(content_hash)
                )
            model = session.scalar(
                statement.order_by(
                    desc(NonprofitRawFilingModel.updated_at),
                    desc(NonprofitRawFilingModel.raw_filing_id),
                ).limit(1)
            )
            return None if model is None else _raw_filing_record(model)

    def get_latest_raw_filing_by_ein(
        self,
        ein: str,
        *,
        tax_year: int | None = None,
        form_type: str | None = None,
    ) -> NonprofitRawFilingRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(NonprofitRawFilingModel)
                .join(NonprofitModel, NonprofitModel.nonprofit_id == NonprofitRawFilingModel.nonprofit_id)
                .where(NonprofitModel.ein == _normalize_ein(ein))
            )
            if tax_year is not None:
                statement = statement.where(NonprofitRawFilingModel.tax_year == tax_year)
            if form_type is not None:
                statement = statement.where(NonprofitRawFilingModel.form_type == _normalize_optional_text(form_type))
            model = session.scalar(
                statement.order_by(
                    desc(NonprofitRawFilingModel.tax_year),
                    desc(NonprofitRawFilingModel.filing_date),
                    desc(NonprofitRawFilingModel.updated_at),
                    desc(NonprofitRawFilingModel.raw_filing_id),
                ).limit(1)
            )
            return None if model is None else _raw_filing_record(model)

    def upsert_source(self, record: NonprofitSourceRecord) -> NonprofitSourceRecord:
        with nonprofit_session_scope(self._session_factory) as session:
            normalized_record = _normalized_source_record(record)
            _execute_upsert(
                session,
                NonprofitSourceModel,
                values=_source_values(normalized_record),
                conflict_columns=["nonprofit_id", "source_id", "record_id", "retrieved_at"],
                update_values=_source_update_values(normalized_record),
            )
            model = session.scalar(
                select(NonprofitSourceModel)
                .where(
                    NonprofitSourceModel.nonprofit_id == normalized_record.nonprofit_id,
                    NonprofitSourceModel.source_id == normalized_record.source_id,
                    NonprofitSourceModel.record_id == normalized_record.record_id,
                    NonprofitSourceModel.retrieved_at == _parse_timestamp(normalized_record.retrieved_at),
                )
                .limit(1)
            )
            assert model is not None
        return _source_record(model)

    def list_sources_for_nonprofit(
        self,
        nonprofit_id: int,
        *,
        source_id: str | None = None,
        limit: int | None = None,
    ) -> list[NonprofitSourceRecord]:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(NonprofitSourceModel)
                .where(NonprofitSourceModel.nonprofit_id == nonprofit_id)
                .order_by(desc(NonprofitSourceModel.retrieved_at))
            )
            if source_id:
                statement = statement.where(NonprofitSourceModel.source_id == source_id)
            if limit is not None:
                statement = statement.limit(limit)
            return [_source_record(model) for model in session.scalars(statement).all()]

    def list_sources_by_ein(
        self,
        ein: str,
        *,
        source_id: str | None = None,
        limit: int | None = None,
    ) -> list[NonprofitSourceRecord]:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(NonprofitSourceModel)
                .join(NonprofitModel, NonprofitModel.nonprofit_id == NonprofitSourceModel.nonprofit_id)
                .where(NonprofitModel.ein == _normalize_ein(ein))
                .order_by(desc(NonprofitSourceModel.retrieved_at))
            )
            if source_id:
                statement = statement.where(NonprofitSourceModel.source_id == source_id)
            if limit is not None:
                statement = statement.limit(limit)
            return [_source_record(model) for model in session.scalars(statement).all()]

    def create_compliance_check(self, record: ComplianceCheckRecord) -> ComplianceCheckRecord:
        with nonprofit_session_scope(self._session_factory) as session:
            model = _check_model(record)
            session.add(model)
            session.flush()
            return _check_record(model)

    def latest_compliance_check(
        self,
        nonprofit_id: int,
        *,
        check_type: str | None = None,
    ) -> ComplianceCheckRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(ComplianceCheckModel)
                .where(ComplianceCheckModel.nonprofit_id == nonprofit_id)
                .order_by(desc(ComplianceCheckModel.evaluated_at), desc(ComplianceCheckModel.created_at))
            )
            if check_type:
                statement = statement.where(ComplianceCheckModel.check_type == check_type)
            model = session.scalar(statement.limit(1))
            return None if model is None else _check_record(model)

    def latest_compliance_check_by_ein(
        self,
        ein: str,
        *,
        check_type: str | None = None,
    ) -> ComplianceCheckRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(ComplianceCheckModel)
                .join(NonprofitModel, NonprofitModel.nonprofit_id == ComplianceCheckModel.nonprofit_id)
                .where(NonprofitModel.ein == _normalize_ein(ein))
                .order_by(desc(ComplianceCheckModel.evaluated_at), desc(ComplianceCheckModel.created_at))
            )
            if check_type:
                statement = statement.where(ComplianceCheckModel.check_type == check_type)
            model = session.scalar(statement.limit(1))
            return None if model is None else _check_record(model)

    def search_nonprofit_summaries(
        self,
        *,
        name_query: str,
        limit: int,
        state: str | None = None,
        subsection: str | None = None,
        active_only: bool = False,
        cursor_name: str | None = None,
        cursor_ein: str | None = None,
    ) -> list[dict[str, Any]]:
        latest_filing = _latest_filing_subquery()
        normalized_query = str(name_query or "").strip().lower()
        cursor_name_normalized = str(cursor_name or "").strip().lower() or None

        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(
                    NonprofitModel.ein,
                    NonprofitModel.canonical_name,
                    NonprofitModel.state,
                    NonprofitModel.subsection_code,
                    NonprofitModel.irs_status,
                    latest_filing.c.tax_period,
                )
                .outerjoin(latest_filing, latest_filing.c.nonprofit_id == NonprofitModel.nonprofit_id)
                .where(NonprofitModel.normalized_name.contains(normalized_query))
                .order_by(NonprofitModel.normalized_name.asc(), NonprofitModel.ein.asc())
            )
            if state:
                statement = statement.where(NonprofitModel.state == state.strip().upper())
            if subsection:
                statement = statement.where(NonprofitModel.subsection_code == subsection.strip())
            if active_only:
                statement = statement.where(NonprofitModel.irs_status == "active")
            if cursor_name_normalized and cursor_ein:
                statement = statement.where(
                    or_(
                        NonprofitModel.normalized_name > cursor_name_normalized,
                        and_(NonprofitModel.normalized_name == cursor_name_normalized, NonprofitModel.ein > cursor_ein),
                    )
                )
            rows = session.execute(statement.limit(limit)).mappings().all()
            return [_search_row(dict(row)) for row in rows]

    def list_nonprofit_eins_page(self, *, limit: int, start_after_ein: str | None = None) -> list[str]:
        normalized_start = _normalize_ein(start_after_ein) if start_after_ein else None
        with nonprofit_session_scope(self._session_factory) as session:
            statement = select(NonprofitModel.ein).order_by(NonprofitModel.ein.asc()).limit(limit)
            if normalized_start:
                statement = statement.where(NonprofitModel.ein > normalized_start)
            return [str(value) for value in session.scalars(statement).all()]

    def get_archive_by_source_url(self, source_url: str) -> Form990ArchiveRecord | None:
        normalized_source_url = _normalize_source_url(source_url)
        with nonprofit_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(Form990ArchiveModel).where(Form990ArchiveModel.source_url == normalized_source_url).limit(1)
            )
            return None if model is None else _archive_record(model)

    def get_archive_by_id(self, archive_id: int) -> Form990ArchiveRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            model = session.scalar(select(Form990ArchiveModel).where(Form990ArchiveModel.archive_id == archive_id).limit(1))
            return None if model is None else _archive_record(model)

    def upsert_archive_probe(self, record: Form990ArchiveRecord) -> Form990ArchiveRecord:
        normalized_record = _normalized_archive_record(record)
        with nonprofit_session_scope(self._session_factory) as session:
            _execute_upsert(
                session,
                Form990ArchiveModel,
                values=_archive_values(normalized_record),
                conflict_columns=["source_url"],
                update_values=_archive_update_values(normalized_record),
            )
            model = session.scalar(
                select(Form990ArchiveModel)
                .where(Form990ArchiveModel.source_url == normalized_record.source_url)
                .limit(1)
            )
            assert model is not None
        return _archive_record(model)

    def mark_archive_processing(
        self,
        archive_id: int,
        *,
        started_at: str | None = None,
        ended_at: str | None = None,
        processed_at: str | None = None,
        status: str,
    ) -> Form990ArchiveRecord | None:
        with nonprofit_session_scope(self._session_factory) as session:
            model = session.scalar(select(Form990ArchiveModel).where(Form990ArchiveModel.archive_id == archive_id).limit(1))
            if model is None:
                return None
            started = _parse_timestamp(started_at) or model.update_started_at or datetime.now(timezone.utc)
            ended_value = _parse_timestamp(ended_at) or _parse_timestamp(processed_at) or datetime.now(timezone.utc)
            processed_value = _parse_timestamp(processed_at) or ended_value
            model.update_started_at = started
            model.update_ended_at = ended_value
            model.last_processed_at = processed_value
            model.status = status
            model.processing_duration_ms = max(int((ended_value - started).total_seconds() * 1000), 0)
            session.flush()
            return _archive_record(model)

    def get_extracted_file(self, archive_id: int, filename: str) -> Form990ExtractedFileRecord | None:
        normalized_filename = _normalize_optional_text(filename) or ""
        with nonprofit_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(Form990ExtractedFileModel)
                .where(
                    Form990ExtractedFileModel.archive_id == archive_id,
                    Form990ExtractedFileModel.filename == normalized_filename,
                )
                .limit(1)
            )
            return None if model is None else _extracted_file_record(model)

    def list_extracted_files_for_archive(self, archive_id: int) -> list[Form990ExtractedFileRecord]:
        with nonprofit_session_scope(self._session_factory) as session:
            statement = (
                select(Form990ExtractedFileModel)
                .where(Form990ExtractedFileModel.archive_id == archive_id)
                .order_by(Form990ExtractedFileModel.filename.asc())
            )
            return [_extracted_file_record(model) for model in session.scalars(statement).all()]

    def upsert_extracted_file(self, record: Form990ExtractedFileRecord) -> Form990ExtractedFileRecord:
        normalized_record = _normalized_extracted_file_record(record)
        with nonprofit_session_scope(self._session_factory) as session:
            _execute_upsert(
                session,
                Form990ExtractedFileModel,
                values=_extracted_file_values(normalized_record),
                conflict_columns=["archive_id", "filename"],
                update_values=_extracted_file_update_values(normalized_record),
            )
            model = session.scalar(
                select(Form990ExtractedFileModel)
                .where(
                    Form990ExtractedFileModel.archive_id == normalized_record.archive_id,
                    Form990ExtractedFileModel.filename == normalized_record.filename,
                )
                .limit(1)
            )
            assert model is not None
        return _extracted_file_record(model)

def _normalize_ein(ein: str) -> str:
    return "".join(ch for ch in str(ein or "") if ch.isdigit())[:9]


def _normalize_source_url(source_url: str) -> str:
    return str(source_url or "").strip()


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_date(value: str | None) -> date | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if "T" in normalized or " " in normalized:
        return _parse_timestamp(normalized).date()
    return date.fromisoformat(normalized)


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _format_date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _latest_filing_subquery():
    ranked = (
        select(
            NonprofitFilingModel.nonprofit_id.label("nonprofit_id"),
            NonprofitFilingModel.tax_period.label("tax_period"),
            NonprofitFilingModel.total_assets.label("total_assets"),
            NonprofitFilingModel.total_income.label("total_income"),
            NonprofitFilingModel.total_revenue.label("total_revenue"),
            func.row_number()
            .over(
                partition_by=NonprofitFilingModel.nonprofit_id,
                order_by=(
                    desc(NonprofitFilingModel.tax_year),
                    desc(NonprofitFilingModel.filing_date),
                    desc(NonprofitFilingModel.updated_at),
                ),
            )
            .label("row_number"),
        ).subquery()
    )
    return (
        select(
            ranked.c.nonprofit_id,
            ranked.c.tax_period,
            ranked.c.total_assets,
            ranked.c.total_income,
            ranked.c.total_revenue,
        )
        .where(ranked.c.row_number == 1)
        .subquery()
    )


def _latest_filing_with_payload_subquery():
    ranked = (
        select(
            NonprofitFilingModel.nonprofit_id.label("nonprofit_id"),
            NonprofitFilingModel.total_revenue.label("total_revenue"),
            NonprofitFilingModel.raw_payload.label("raw_payload"),
            func.row_number()
            .over(
                partition_by=NonprofitFilingModel.nonprofit_id,
                order_by=(
                    desc(NonprofitFilingModel.tax_year),
                    desc(NonprofitFilingModel.filing_date),
                    desc(NonprofitFilingModel.updated_at),
                ),
            )
            .label("row_number"),
        ).subquery()
    )
    return (
        select(
            ranked.c.nonprofit_id,
            ranked.c.total_revenue,
            ranked.c.raw_payload,
        )
        .where(ranked.c.row_number == 1)
        .subquery()
    )


def _revenue_band_predicate(column: Any, band: str):
    if band == "under_250k":
        return column < 250_000
    if band == "250k_to_1m":
        return and_(column >= 250_000, column < 1_000_000)
    if band == "1m_to_10m":
        return and_(column >= 1_000_000, column < 10_000_000)
    if band == "10m_to_100m":
        return and_(column >= 10_000_000, column < 100_000_000)
    if band == "100m_plus":
        return column >= 100_000_000
    return True


def _snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ein": row.get("ein"),
        "name": row.get("canonical_name"),
        "state": row.get("state"),
        "subsection": row.get("subsection_code"),
        "status": row.get("irs_status"),
        "deductibility": row.get("deductibility_code"),
        "ntee_cd": row.get("ntee_category"),
        "tax_period": row.get("tax_period"),
        "asset_amt": row.get("total_assets"),
        "income_amt": row.get("total_income"),
        "revenue_amt": row.get("total_revenue"),
    }


def _filing_query_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ein": row.get("ein"),
        "tax_year": None if row.get("tax_year") is None else str(row.get("tax_year")),
        "return_type": row.get("form_type"),
        "filing_date": _format_date(row.get("filing_date")),
        "amended_return": _query_bool_string(row.get("amended")),
        "parse_status": row.get("parse_status"),
    }


def _search_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ein": row.get("ein"),
        "name": row.get("canonical_name"),
        "state": row.get("state"),
        "subsection": row.get("subsection_code"),
        "status": row.get("irs_status"),
        "tax_period": row.get("tax_period"),
    }


def _query_bool_string(value: bool | None) -> str | None:
    if value is None:
        return None
    return "true" if value else "false"


def _nonprofit_model(record: NonprofitRecord) -> NonprofitModel:
    payload: dict[str, Any] = {
        "ein": _normalize_ein(record.ein),
        "canonical_name": record.canonical_name,
        "normalized_name": record.normalized_name,
        "subsection_code": record.subsection_code,
        "deductibility_code": record.deductibility_code,
        "tax_deductible": record.tax_deductible,
        "entity_type": record.entity_type,
        "irs_status": record.irs_status,
        "revoked": record.revoked,
        "country": record.country,
        "state": record.state,
        "ntee_category": record.ntee_category,
        "canonical_source": record.canonical_source,
        "source_version": record.source_version,
        "last_seen_at": _parse_timestamp(record.last_seen_at),
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "updated_at": _parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    }
    if record.nonprofit_id is not None:
        payload["nonprofit_id"] = record.nonprofit_id
    return NonprofitModel(**payload)


def _apply_nonprofit_record(model: NonprofitModel, record: NonprofitRecord) -> None:
    model.canonical_name = record.canonical_name
    model.normalized_name = record.normalized_name
    model.subsection_code = record.subsection_code
    model.deductibility_code = record.deductibility_code
    model.tax_deductible = record.tax_deductible
    model.entity_type = record.entity_type
    model.irs_status = record.irs_status
    model.revoked = record.revoked
    model.country = record.country
    model.state = record.state
    model.ntee_category = record.ntee_category
    model.canonical_source = record.canonical_source
    model.source_version = record.source_version
    model.last_seen_at = _parse_timestamp(record.last_seen_at)
    model.updated_at = _parse_timestamp(record.updated_at) or datetime.now(timezone.utc)


def _nonprofit_record(model: NonprofitModel) -> NonprofitRecord:
    return NonprofitRecord(
        nonprofit_id=model.nonprofit_id,
        ein=model.ein,
        canonical_name=model.canonical_name,
        normalized_name=model.normalized_name,
        subsection_code=model.subsection_code,
        deductibility_code=model.deductibility_code,
        tax_deductible=model.tax_deductible,
        entity_type=model.entity_type,
        irs_status=model.irs_status,
        revoked=model.revoked,
        country=model.country,
        state=model.state,
        ntee_category=model.ntee_category,
        canonical_source=model.canonical_source,
        source_version=model.source_version,
        last_seen_at=_format_timestamp(model.last_seen_at),
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _filing_model(record: NonprofitFilingRecord) -> NonprofitFilingModel:
    return NonprofitFilingModel(
        filing_id=record.filing_id,
        nonprofit_id=record.nonprofit_id,
        tax_year=record.tax_year,
        tax_period=record.tax_period,
        form_type=record.form_type,
        filing_date=_parse_date(record.filing_date),
        amended=record.amended,
        parse_status=record.parse_status,
        total_assets=record.total_assets,
        total_income=record.total_income,
        total_revenue=record.total_revenue,
        source_name=record.source_name,
        source_record_id=record.source_record_id,
        source_signature=record.source_signature,
        xml_source_reference=record.xml_source_reference,
        raw_file_reference=record.raw_file_reference,
        raw_payload=record.raw_payload,
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        updated_at=_parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    )


def _apply_filing_record(model: NonprofitFilingModel, record: NonprofitFilingRecord) -> None:
    model.tax_year = record.tax_year
    model.tax_period = record.tax_period
    model.form_type = record.form_type
    model.filing_date = _parse_date(record.filing_date)
    model.amended = record.amended
    model.parse_status = record.parse_status
    model.total_assets = record.total_assets
    model.total_income = record.total_income
    model.total_revenue = record.total_revenue
    model.source_name = record.source_name
    model.source_record_id = record.source_record_id
    model.source_signature = record.source_signature
    model.xml_source_reference = record.xml_source_reference
    model.raw_file_reference = record.raw_file_reference
    model.raw_payload = record.raw_payload
    model.updated_at = _parse_timestamp(record.updated_at) or datetime.now(timezone.utc)


def _filing_record(model: NonprofitFilingModel) -> NonprofitFilingRecord:
    return NonprofitFilingRecord(
        filing_id=model.filing_id,
        nonprofit_id=model.nonprofit_id,
        tax_year=model.tax_year,
        tax_period=model.tax_period,
        form_type=model.form_type,
        filing_date=_format_date(model.filing_date),
        amended=model.amended,
        parse_status=model.parse_status,
        total_assets=model.total_assets,
        total_income=model.total_income,
        total_revenue=model.total_revenue,
        source_name=model.source_name,
        source_record_id=model.source_record_id,
        source_signature=model.source_signature,
        xml_source_reference=model.xml_source_reference,
        raw_file_reference=model.raw_file_reference,
        raw_payload=model.raw_payload,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _source_model(record: NonprofitSourceRecord) -> NonprofitSourceModel:
    return NonprofitSourceModel(
        nonprofit_source_id=record.nonprofit_source_id,
        nonprofit_id=record.nonprofit_id,
        source_id=record.source_id,
        provider_name=record.provider_name,
        category=record.category,
        record_id=record.record_id,
        retrieved_at=_parse_timestamp(record.retrieved_at) or datetime.now(timezone.utc),
        valid_as_of=_parse_timestamp(record.valid_as_of),
        expires_at=_parse_timestamp(record.expires_at),
        status=record.status,
        driver=record.driver,
        integration_id=record.integration_id,
        tenant_enabled=record.tenant_enabled,
        required_for_eligibility=record.required_for_eligibility,
        evaluation_effect=record.evaluation_effect,
        explanation_code=record.explanation_code,
        explanation=record.explanation,
        licensed=record.licensed,
        notes=record.notes,
        source_signature=record.source_signature,
        normalized_data=record.normalized_data,
        raw_payload=record.raw_payload,
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        updated_at=_parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    )


def _apply_source_record(model: NonprofitSourceModel, record: NonprofitSourceRecord) -> None:
    model.source_id = record.source_id
    model.provider_name = record.provider_name
    model.category = record.category
    model.record_id = record.record_id
    model.retrieved_at = _parse_timestamp(record.retrieved_at) or datetime.now(timezone.utc)
    model.valid_as_of = _parse_timestamp(record.valid_as_of)
    model.expires_at = _parse_timestamp(record.expires_at)
    model.status = record.status
    model.driver = record.driver
    model.integration_id = record.integration_id
    model.tenant_enabled = record.tenant_enabled
    model.required_for_eligibility = record.required_for_eligibility
    model.evaluation_effect = record.evaluation_effect
    model.explanation_code = record.explanation_code
    model.explanation = record.explanation
    model.licensed = record.licensed
    model.notes = record.notes
    model.source_signature = record.source_signature
    model.normalized_data = record.normalized_data
    model.raw_payload = record.raw_payload
    model.updated_at = _parse_timestamp(record.updated_at) or datetime.now(timezone.utc)


def _source_record(model: NonprofitSourceModel) -> NonprofitSourceRecord:
    return NonprofitSourceRecord(
        nonprofit_source_id=model.nonprofit_source_id,
        nonprofit_id=model.nonprofit_id,
        source_id=model.source_id,
        provider_name=model.provider_name,
        category=model.category,
        record_id=model.record_id,
        retrieved_at=_format_timestamp(model.retrieved_at) or "",
        valid_as_of=_format_timestamp(model.valid_as_of),
        expires_at=_format_timestamp(model.expires_at),
        status=model.status,
        driver=model.driver,
        integration_id=model.integration_id,
        tenant_enabled=model.tenant_enabled,
        required_for_eligibility=model.required_for_eligibility,
        evaluation_effect=model.evaluation_effect,
        explanation_code=model.explanation_code,
        explanation=model.explanation,
        licensed=model.licensed,
        notes=model.notes,
        source_signature=model.source_signature,
        normalized_data=model.normalized_data,
        raw_payload=model.raw_payload,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _raw_filing_model(record: NonprofitRawFilingRecord) -> NonprofitRawFilingModel:
    return NonprofitRawFilingModel(
        raw_filing_id=record.raw_filing_id,
        nonprofit_id=record.nonprofit_id,
        filing_id=record.filing_id,
        tax_year=record.tax_year,
        form_type=record.form_type,
        filing_date=_parse_date(record.filing_date),
        source_name=record.source_name,
        source_record_id=record.source_record_id,
        source_signature=record.source_signature,
        xml_content_hash=record.xml_content_hash,
        xml_artifact_reference=record.xml_artifact_reference,
        parse_status=record.parse_status,
        parser_version=record.parser_version,
        canonicalization_version=record.canonicalization_version,
        raw_filing_json=record.raw_filing_json,
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        updated_at=_parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    )


def _apply_raw_filing_record(model: NonprofitRawFilingModel, record: NonprofitRawFilingRecord) -> None:
    model.nonprofit_id = record.nonprofit_id
    model.filing_id = record.filing_id
    model.tax_year = record.tax_year
    model.form_type = record.form_type
    model.filing_date = _parse_date(record.filing_date)
    model.source_name = record.source_name
    model.source_record_id = record.source_record_id
    model.source_signature = record.source_signature
    model.xml_content_hash = record.xml_content_hash
    model.xml_artifact_reference = record.xml_artifact_reference
    model.parse_status = record.parse_status
    model.parser_version = record.parser_version
    model.canonicalization_version = record.canonicalization_version
    model.raw_filing_json = record.raw_filing_json
    model.updated_at = _parse_timestamp(record.updated_at) or datetime.now(timezone.utc)


def _raw_filing_record(model: NonprofitRawFilingModel) -> NonprofitRawFilingRecord:
    return NonprofitRawFilingRecord(
        raw_filing_id=model.raw_filing_id,
        nonprofit_id=model.nonprofit_id,
        filing_id=model.filing_id,
        tax_year=model.tax_year,
        form_type=model.form_type,
        filing_date=_format_date(model.filing_date),
        source_name=model.source_name,
        source_record_id=model.source_record_id,
        source_signature=model.source_signature,
        xml_content_hash=model.xml_content_hash,
        xml_artifact_reference=model.xml_artifact_reference,
        parse_status=model.parse_status,
        parser_version=model.parser_version,
        canonicalization_version=model.canonicalization_version,
        raw_filing_json=model.raw_filing_json,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _check_model(record: ComplianceCheckRecord) -> ComplianceCheckModel:
    return ComplianceCheckModel(
        compliance_check_id=record.compliance_check_id,
        nonprofit_id=record.nonprofit_id,
        check_type=record.check_type,
        status=record.status,
        evaluated_at=_parse_timestamp(record.evaluated_at) or datetime.now(timezone.utc),
        policy_version=record.policy_version,
        model_version=record.model_version,
        source_hash=record.source_hash,
        environment=record.environment,
        registration_status=record.registration_status,
        registration_jurisdiction=record.registration_jurisdiction,
        registration_expiration_date=_parse_date(record.registration_expiration_date),
        solicitation_permitted=record.solicitation_permitted,
        state_business_status=record.state_business_status,
        state_business_good_standing=record.state_business_good_standing,
        final_recommendation=record.final_recommendation,
        flags_json=record.flags_json,
        reasons_json=record.reasons_json,
        evidence_json=record.evidence_json,
        summary_json=record.summary_json,
        metadata_json=record.metadata_json,
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
    )


def _check_record(model: ComplianceCheckModel) -> ComplianceCheckRecord:
    return ComplianceCheckRecord(
        compliance_check_id=model.compliance_check_id,
        nonprofit_id=model.nonprofit_id,
        check_type=model.check_type,
        status=model.status,
        evaluated_at=_format_timestamp(model.evaluated_at) or "",
        policy_version=model.policy_version,
        model_version=model.model_version,
        source_hash=model.source_hash,
        environment=model.environment,
        registration_status=model.registration_status,
        registration_jurisdiction=model.registration_jurisdiction,
        registration_expiration_date=_format_date(model.registration_expiration_date),
        solicitation_permitted=model.solicitation_permitted,
        state_business_status=model.state_business_status,
        state_business_good_standing=model.state_business_good_standing,
        final_recommendation=model.final_recommendation,
        flags_json=model.flags_json,
        reasons_json=model.reasons_json,
        evidence_json=model.evidence_json,
        summary_json=model.summary_json,
        metadata_json=model.metadata_json,
        created_at=_format_timestamp(model.created_at) or "",
    )


def _archive_model(record: Form990ArchiveRecord) -> Form990ArchiveModel:
    return Form990ArchiveModel(
        archive_id=record.archive_id,
        source_url=_normalize_source_url(record.source_url),
        filename=record.filename,
        etag=record.etag,
        last_modified=record.last_modified,
        content_length=record.content_length,
        response_status=record.response_status,
        last_checked_at=_parse_timestamp(record.last_checked_at),
        last_processed_at=_parse_timestamp(record.last_processed_at),
        status=record.status,
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        update_started_at=_parse_timestamp(record.update_started_at) or datetime.now(timezone.utc),
        update_ended_at=_parse_timestamp(record.update_ended_at),
        processing_duration_ms=record.processing_duration_ms,
    )


def _apply_archive_record(model: Form990ArchiveModel, record: Form990ArchiveRecord) -> None:
    model.filename = record.filename
    model.etag = record.etag
    model.last_modified = record.last_modified
    model.content_length = record.content_length
    model.response_status = record.response_status
    model.last_checked_at = _parse_timestamp(record.last_checked_at)
    model.last_processed_at = _parse_timestamp(record.last_processed_at)
    model.status = record.status
    model.update_started_at = _parse_timestamp(record.update_started_at) or datetime.now(timezone.utc)
    model.update_ended_at = _parse_timestamp(record.update_ended_at)
    model.processing_duration_ms = record.processing_duration_ms


def _archive_record(model: Form990ArchiveModel) -> Form990ArchiveRecord:
    return Form990ArchiveRecord(
        archive_id=model.archive_id,
        source_url=model.source_url,
        filename=model.filename,
        etag=model.etag,
        last_modified=model.last_modified,
        content_length=model.content_length,
        response_status=model.response_status,
        last_checked_at=_format_timestamp(model.last_checked_at),
        last_processed_at=_format_timestamp(model.last_processed_at),
        status=model.status,
        created_at=_format_timestamp(model.created_at) or "",
        update_started_at=_format_timestamp(model.update_started_at) or "",
        update_ended_at=_format_timestamp(model.update_ended_at),
        processing_duration_ms=model.processing_duration_ms,
    )


def _extracted_file_model(record: Form990ExtractedFileRecord) -> Form990ExtractedFileModel:
    return Form990ExtractedFileModel(
        file_id=record.file_id,
        archive_id=record.archive_id,
        filename=record.filename,
        content_hash=record.content_hash,
        parse_status=record.parse_status,
        parsed_at=_parse_timestamp(record.parsed_at),
        error_message=record.error_message,
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        updated_at=_parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    )


def _apply_extracted_file_record(model: Form990ExtractedFileModel, record: Form990ExtractedFileRecord) -> None:
    model.content_hash = record.content_hash
    model.parse_status = record.parse_status
    model.parsed_at = _parse_timestamp(record.parsed_at)
    model.error_message = record.error_message
    model.updated_at = _parse_timestamp(record.updated_at) or datetime.now(timezone.utc)


def _extracted_file_record(model: Form990ExtractedFileModel) -> Form990ExtractedFileRecord:
    return Form990ExtractedFileRecord(
        file_id=model.file_id,
        archive_id=model.archive_id,
        filename=model.filename,
        content_hash=model.content_hash,
        parse_status=model.parse_status,
        parsed_at=_format_timestamp(model.parsed_at),
        error_message=model.error_message,
        created_at=_format_timestamp(model.created_at) or "",
        updated_at=_format_timestamp(model.updated_at) or "",
    )


def _execute_upsert(
    session: Session,
    model: type[Any],
    *,
    values: dict[str, Any],
    conflict_columns: list[str],
    update_values: dict[str, Any],
) -> None:
    insert_fn = _insert_for_session(session)
    statement = insert_fn(model).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=list(conflict_columns),
        set_=dict(update_values),
    )
    session.execute(statement)
    session.flush()


def _execute_upsert_many(
    session: Session,
    model: type[Any],
    *,
    values: list[dict[str, Any]],
    conflict_columns: list[str],
    update_columns: list[str],
) -> None:
    if not values:
        return
    insert_fn = _insert_for_session(session)
    statement = insert_fn(model).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=list(conflict_columns),
        set_={column: getattr(statement.excluded, column) for column in update_columns},
    )
    session.execute(statement)
    session.flush()


def _insert_for_session(session: Session):
    dialect_name = session.bind.dialect.name if session.bind is not None else ""
    if dialect_name == "postgresql":
        return postgresql_insert
    if dialect_name == "sqlite":
        return sqlite_insert
    raise NotImplementedError(f"Unsupported nonprofit repository dialect for upsert: {dialect_name}")


def _elapsed_ms(elapsed_seconds: float) -> int:
    return max(0, int(round(float(elapsed_seconds) * 1000)))


def _normalized_nonprofit_record(record: NonprofitRecord) -> NonprofitRecord:
    normalized_name = _normalize_optional_text(record.normalized_name)
    canonical_name = _normalize_optional_text(record.canonical_name) or f"EIN {_normalize_ein(record.ein)}"
    return NonprofitRecord(
        nonprofit_id=record.nonprofit_id,
        ein=_normalize_ein(record.ein),
        canonical_name=canonical_name,
        normalized_name=normalized_name or canonical_name.lower(),
        subsection_code=_normalize_optional_text(record.subsection_code),
        deductibility_code=_normalize_optional_text(record.deductibility_code),
        tax_deductible=record.tax_deductible,
        entity_type=_normalize_optional_text(record.entity_type),
        irs_status=_normalize_optional_text(record.irs_status),
        revoked=bool(record.revoked),
        country=_normalize_optional_text(record.country),
        state=_normalize_optional_text(record.state),
        ntee_category=_normalize_optional_text(record.ntee_category),
        canonical_source=_normalize_optional_text(record.canonical_source),
        source_version=_normalize_optional_text(record.source_version),
        last_seen_at=_format_timestamp(_parse_timestamp(record.last_seen_at)),
        created_at=_format_timestamp(_parse_timestamp(record.created_at) or datetime.now(timezone.utc)) or "",
        updated_at=_format_timestamp(_parse_timestamp(record.updated_at) or datetime.now(timezone.utc)) or "",
    )


def _normalized_filing_record(record: NonprofitFilingRecord) -> NonprofitFilingRecord:
    return NonprofitFilingRecord(
        filing_id=record.filing_id,
        nonprofit_id=record.nonprofit_id,
        tax_year=record.tax_year,
        tax_period=_normalize_optional_text(record.tax_period),
        form_type=_normalize_optional_text(record.form_type) or "unknown",
        filing_date=_format_date(_parse_date(record.filing_date)),
        amended=bool(record.amended),
        parse_status=_normalize_optional_text(record.parse_status),
        total_assets=record.total_assets,
        total_income=record.total_income,
        total_revenue=record.total_revenue,
        source_name=_normalize_optional_text(record.source_name),
        source_record_id=_normalize_optional_text(record.source_record_id),
        source_signature=_normalize_optional_text(record.source_signature),
        xml_source_reference=_normalize_optional_text(record.xml_source_reference),
        raw_file_reference=_normalize_optional_text(record.raw_file_reference),
        raw_payload=record.raw_payload,
        created_at=_format_timestamp(_parse_timestamp(record.created_at) or datetime.now(timezone.utc)) or "",
        updated_at=_format_timestamp(_parse_timestamp(record.updated_at) or datetime.now(timezone.utc)) or "",
    )


def _normalized_source_record(record: NonprofitSourceRecord) -> NonprofitSourceRecord:
    return NonprofitSourceRecord(
        nonprofit_source_id=record.nonprofit_source_id,
        nonprofit_id=record.nonprofit_id,
        source_id=_normalize_optional_text(record.source_id) or "",
        provider_name=_normalize_optional_text(record.provider_name) or "",
        category=_normalize_optional_text(record.category) or "",
        record_id=_normalize_optional_text(record.record_id),
        retrieved_at=_format_timestamp(_parse_timestamp(record.retrieved_at) or datetime.now(timezone.utc)) or "",
        valid_as_of=_format_timestamp(_parse_timestamp(record.valid_as_of)),
        expires_at=_format_timestamp(_parse_timestamp(record.expires_at)),
        status=_normalize_optional_text(record.status),
        driver=_normalize_optional_text(record.driver),
        integration_id=_normalize_optional_text(record.integration_id),
        tenant_enabled=record.tenant_enabled,
        required_for_eligibility=record.required_for_eligibility,
        evaluation_effect=_normalize_optional_text(record.evaluation_effect),
        explanation_code=_normalize_optional_text(record.explanation_code),
        explanation=_normalize_optional_text(record.explanation),
        licensed=record.licensed,
        notes=_normalize_optional_text(record.notes),
        source_signature=_normalize_optional_text(record.source_signature),
        normalized_data=record.normalized_data,
        raw_payload=record.raw_payload,
        created_at=_format_timestamp(_parse_timestamp(record.created_at) or datetime.now(timezone.utc)) or "",
        updated_at=_format_timestamp(_parse_timestamp(record.updated_at) or datetime.now(timezone.utc)) or "",
    )


def _normalized_raw_filing_record(record: NonprofitRawFilingRecord) -> NonprofitRawFilingRecord:
    return NonprofitRawFilingRecord(
        raw_filing_id=record.raw_filing_id,
        nonprofit_id=record.nonprofit_id,
        filing_id=record.filing_id,
        tax_year=record.tax_year,
        form_type=_normalize_optional_text(record.form_type) or "unknown",
        filing_date=_format_date(_parse_date(record.filing_date)),
        source_name=_normalize_optional_text(record.source_name),
        source_record_id=_normalize_optional_text(record.source_record_id),
        source_signature=_normalize_optional_text(record.source_signature),
        xml_content_hash=_normalize_optional_text(record.xml_content_hash) or "",
        xml_artifact_reference=_normalize_optional_text(record.xml_artifact_reference),
        parse_status=_normalize_optional_text(record.parse_status),
        parser_version=_normalize_optional_text(record.parser_version) or "",
        canonicalization_version=_normalize_optional_text(record.canonicalization_version) or "",
        raw_filing_json=record.raw_filing_json,
        created_at=_format_timestamp(_parse_timestamp(record.created_at) or datetime.now(timezone.utc)) or "",
        updated_at=_format_timestamp(_parse_timestamp(record.updated_at) or datetime.now(timezone.utc)) or "",
    )


def _normalized_archive_record(record: Form990ArchiveRecord) -> Form990ArchiveRecord:
    return Form990ArchiveRecord(
        archive_id=record.archive_id,
        source_url=_normalize_source_url(record.source_url),
        filename=_normalize_optional_text(record.filename),
        etag=_normalize_optional_text(record.etag),
        last_modified=_normalize_optional_text(record.last_modified),
        content_length=record.content_length,
        response_status=record.response_status,
        last_checked_at=_format_timestamp(_parse_timestamp(record.last_checked_at)),
        last_processed_at=_format_timestamp(_parse_timestamp(record.last_processed_at)),
        status=_normalize_optional_text(record.status),
        created_at=_format_timestamp(_parse_timestamp(record.created_at) or datetime.now(timezone.utc)) or "",
        update_started_at=_format_timestamp(_parse_timestamp(record.update_started_at) or datetime.now(timezone.utc)) or "",
        update_ended_at=_format_timestamp(_parse_timestamp(record.update_ended_at)),
        processing_duration_ms=record.processing_duration_ms,
    )


def _normalized_extracted_file_record(record: Form990ExtractedFileRecord) -> Form990ExtractedFileRecord:
    return Form990ExtractedFileRecord(
        file_id=record.file_id,
        archive_id=record.archive_id,
        filename=_normalize_optional_text(record.filename) or "",
        content_hash=_normalize_optional_text(record.content_hash),
        parse_status=_normalize_optional_text(record.parse_status),
        parsed_at=_format_timestamp(_parse_timestamp(record.parsed_at)),
        error_message=_normalize_optional_text(record.error_message),
        created_at=_format_timestamp(_parse_timestamp(record.created_at) or datetime.now(timezone.utc)) or "",
        updated_at=_format_timestamp(_parse_timestamp(record.updated_at) or datetime.now(timezone.utc)) or "",
    )


def _nonprofit_values(record: NonprofitRecord) -> dict[str, Any]:
    values: dict[str, Any] = {
        "ein": record.ein,
        "canonical_name": record.canonical_name,
        "normalized_name": record.normalized_name,
        "subsection_code": record.subsection_code,
        "deductibility_code": record.deductibility_code,
        "tax_deductible": record.tax_deductible,
        "entity_type": record.entity_type,
        "irs_status": record.irs_status,
        "revoked": record.revoked,
        "country": record.country,
        "state": record.state,
        "ntee_category": record.ntee_category,
        "canonical_source": record.canonical_source,
        "source_version": record.source_version,
        "last_seen_at": _parse_timestamp(record.last_seen_at),
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "updated_at": _parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    }
    if record.nonprofit_id is not None:
        values["nonprofit_id"] = record.nonprofit_id
    return values


def _nonprofit_update_values(record: NonprofitRecord) -> dict[str, Any]:
    values = _nonprofit_values(record)
    values.pop("nonprofit_id", None)
    values.pop("created_at", None)
    return values


def _filing_values(record: NonprofitFilingRecord) -> dict[str, Any]:
    values: dict[str, Any] = {
        "nonprofit_id": record.nonprofit_id,
        "tax_year": record.tax_year,
        "tax_period": record.tax_period,
        "form_type": record.form_type,
        "filing_date": _parse_date(record.filing_date),
        "amended": record.amended,
        "parse_status": record.parse_status,
        "total_assets": record.total_assets,
        "total_income": record.total_income,
        "total_revenue": record.total_revenue,
        "source_name": record.source_name,
        "source_record_id": record.source_record_id,
        "source_signature": record.source_signature,
        "xml_source_reference": record.xml_source_reference,
        "raw_file_reference": record.raw_file_reference,
        "raw_payload": record.raw_payload,
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "updated_at": _parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    }
    if record.filing_id is not None:
        values["filing_id"] = record.filing_id
    return values


def _filing_update_values(record: NonprofitFilingRecord) -> dict[str, Any]:
    values = _filing_values(record)
    values.pop("filing_id", None)
    values.pop("created_at", None)
    return values


def _source_values(record: NonprofitSourceRecord) -> dict[str, Any]:
    values: dict[str, Any] = {
        "nonprofit_id": record.nonprofit_id,
        "source_id": record.source_id,
        "provider_name": record.provider_name,
        "category": record.category,
        "record_id": record.record_id,
        "retrieved_at": _parse_timestamp(record.retrieved_at) or datetime.now(timezone.utc),
        "valid_as_of": _parse_timestamp(record.valid_as_of),
        "expires_at": _parse_timestamp(record.expires_at),
        "status": record.status,
        "driver": record.driver,
        "integration_id": record.integration_id,
        "tenant_enabled": record.tenant_enabled,
        "required_for_eligibility": record.required_for_eligibility,
        "evaluation_effect": record.evaluation_effect,
        "explanation_code": record.explanation_code,
        "explanation": record.explanation,
        "licensed": record.licensed,
        "notes": record.notes,
        "source_signature": record.source_signature,
        "normalized_data": record.normalized_data,
        "raw_payload": record.raw_payload,
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "updated_at": _parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    }
    if record.nonprofit_source_id is not None:
        values["nonprofit_source_id"] = record.nonprofit_source_id
    return values


def _source_update_values(record: NonprofitSourceRecord) -> dict[str, Any]:
    values = _source_values(record)
    values.pop("nonprofit_source_id", None)
    values.pop("created_at", None)
    return values


def _raw_filing_values(record: NonprofitRawFilingRecord) -> dict[str, Any]:
    values: dict[str, Any] = {
        "nonprofit_id": record.nonprofit_id,
        "filing_id": record.filing_id,
        "tax_year": record.tax_year,
        "form_type": record.form_type,
        "filing_date": _parse_date(record.filing_date),
        "source_name": record.source_name,
        "source_record_id": record.source_record_id,
        "source_signature": record.source_signature,
        "xml_content_hash": record.xml_content_hash,
        "xml_artifact_reference": record.xml_artifact_reference,
        "parse_status": record.parse_status,
        "parser_version": record.parser_version,
        "canonicalization_version": record.canonicalization_version,
        "raw_filing_json": record.raw_filing_json,
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "updated_at": _parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    }
    if record.raw_filing_id is not None:
        values["raw_filing_id"] = record.raw_filing_id
    return values


def _raw_filing_update_values(record: NonprofitRawFilingRecord) -> dict[str, Any]:
    values = _raw_filing_values(record)
    values.pop("raw_filing_id", None)
    values.pop("created_at", None)
    return values


def _archive_values(record: Form990ArchiveRecord) -> dict[str, Any]:
    values: dict[str, Any] = {
        "source_url": record.source_url,
        "filename": record.filename,
        "etag": record.etag,
        "last_modified": record.last_modified,
        "content_length": record.content_length,
        "response_status": record.response_status,
        "last_checked_at": _parse_timestamp(record.last_checked_at),
        "last_processed_at": _parse_timestamp(record.last_processed_at),
        "status": record.status,
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "update_started_at": _parse_timestamp(record.update_started_at) or datetime.now(timezone.utc),
        "update_ended_at": _parse_timestamp(record.update_ended_at),
        "processing_duration_ms": record.processing_duration_ms,
    }
    if record.archive_id is not None:
        values["archive_id"] = record.archive_id
    return values


def _archive_update_values(record: Form990ArchiveRecord) -> dict[str, Any]:
    values = _archive_values(record)
    values.pop("archive_id", None)
    values.pop("created_at", None)
    return values


def _extracted_file_values(record: Form990ExtractedFileRecord) -> dict[str, Any]:
    values: dict[str, Any] = {
        "archive_id": record.archive_id,
        "filename": record.filename,
        "content_hash": record.content_hash,
        "parse_status": record.parse_status,
        "parsed_at": _parse_timestamp(record.parsed_at),
        "error_message": record.error_message,
        "created_at": _parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        "updated_at": _parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    }
    if record.file_id is not None:
        values["file_id"] = record.file_id
    return values


def _extracted_file_update_values(record: Form990ExtractedFileRecord) -> dict[str, Any]:
    values = _extracted_file_values(record)
    values.pop("file_id", None)
    values.pop("created_at", None)
    return values
