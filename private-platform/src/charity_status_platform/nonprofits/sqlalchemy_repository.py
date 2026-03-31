from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

from charity_status_platform.customer_accounts.sqlalchemy_db import customer_accounts_session_scope

from .sqlalchemy_models import ComplianceCheckModel, NonprofitFilingModel, NonprofitModel, NonprofitSourceModel


@dataclass(frozen=True)
class NonprofitRecord:
    nonprofit_id: str
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
    filing_id: str
    nonprofit_id: str
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
    raw_s3_key: str | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NonprofitSourceRecord:
    nonprofit_source_id: str
    nonprofit_id: str
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
class ComplianceCheckRecord:
    compliance_check_id: str
    nonprofit_id: str
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


class SqlAlchemyNonprofitRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def upsert_nonprofit(self, record: NonprofitRecord) -> NonprofitRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(select(NonprofitModel).where(NonprofitModel.ein == record.ein).limit(1))
            if model is None:
                session.add(_nonprofit_model(record))
            else:
                _apply_nonprofit_record(model, record)
            session.flush()
        return record

    def get_nonprofit_by_ein(self, ein: str) -> NonprofitRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(select(NonprofitModel).where(NonprofitModel.ein == _normalize_ein(ein)).limit(1))
            return None if model is None else _nonprofit_record(model)

    def upsert_filing(self, record: NonprofitFilingRecord) -> NonprofitFilingRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(NonprofitFilingModel)
                .where(NonprofitFilingModel.filing_id == record.filing_id)
                .limit(1)
            )
            if model is None:
                session.add(_filing_model(record))
            else:
                _apply_filing_record(model, record)
            session.flush()
        return record

    def list_filings_for_nonprofit(self, nonprofit_id: str, *, limit: int | None = None) -> list[NonprofitFilingRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            statement = (
                select(NonprofitFilingModel)
                .where(NonprofitFilingModel.nonprofit_id == nonprofit_id)
                .order_by(desc(NonprofitFilingModel.tax_year), desc(NonprofitFilingModel.filing_date))
            )
            if limit is not None:
                statement = statement.limit(limit)
            return [_filing_record(model) for model in session.scalars(statement).all()]

    def upsert_source(self, record: NonprofitSourceRecord) -> NonprofitSourceRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(NonprofitSourceModel)
                .where(NonprofitSourceModel.nonprofit_source_id == record.nonprofit_source_id)
                .limit(1)
            )
            if model is None:
                session.add(_source_model(record))
            else:
                _apply_source_record(model, record)
            session.flush()
        return record

    def list_sources_for_nonprofit(
        self,
        nonprofit_id: str,
        *,
        source_id: str | None = None,
        limit: int | None = None,
    ) -> list[NonprofitSourceRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
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

    def create_compliance_check(self, record: ComplianceCheckRecord) -> ComplianceCheckRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            session.add(_check_model(record))
            session.flush()
        return record

    def latest_compliance_check(
        self,
        nonprofit_id: str,
        *,
        check_type: str | None = None,
    ) -> ComplianceCheckRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            statement = (
                select(ComplianceCheckModel)
                .where(ComplianceCheckModel.nonprofit_id == nonprofit_id)
                .order_by(desc(ComplianceCheckModel.evaluated_at), desc(ComplianceCheckModel.created_at))
            )
            if check_type:
                statement = statement.where(ComplianceCheckModel.check_type == check_type)
            model = session.scalar(statement.limit(1))
            return None if model is None else _check_record(model)


def build_nonprofit_id(ein: str) -> str:
    return f"npo_{_normalize_ein(ein)}"


def make_record_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def _normalize_ein(ein: str) -> str:
    return "".join(ch for ch in str(ein or "") if ch.isdigit())[:9]


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
    return date.fromisoformat(normalized)


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _format_date(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _nonprofit_model(record: NonprofitRecord) -> NonprofitModel:
    return NonprofitModel(
        nonprofit_id=record.nonprofit_id,
        ein=_normalize_ein(record.ein),
        canonical_name=record.canonical_name,
        normalized_name=record.normalized_name,
        subsection_code=record.subsection_code,
        deductibility_code=record.deductibility_code,
        tax_deductible=record.tax_deductible,
        entity_type=record.entity_type,
        irs_status=record.irs_status,
        revoked=record.revoked,
        country=record.country,
        state=record.state,
        ntee_category=record.ntee_category,
        canonical_source=record.canonical_source,
        source_version=record.source_version,
        last_seen_at=_parse_timestamp(record.last_seen_at),
        created_at=_parse_timestamp(record.created_at) or datetime.now(timezone.utc),
        updated_at=_parse_timestamp(record.updated_at) or datetime.now(timezone.utc),
    )


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
        raw_s3_key=record.raw_s3_key,
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
    model.raw_s3_key = record.raw_s3_key
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
        raw_s3_key=model.raw_s3_key,
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
