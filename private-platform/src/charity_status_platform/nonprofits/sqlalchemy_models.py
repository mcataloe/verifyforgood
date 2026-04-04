from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from charity_status_platform.customer_accounts.sqlalchemy_db import CustomerAccountsBase


JSON_VARIANT = JSON().with_variant(JSONB(), "postgresql")
BIGINT_PRIMARY_KEY = BigInteger().with_variant(Integer(), "sqlite")


class NonprofitModel(CustomerAccountsBase):
    __tablename__ = "nonprofits"
    __table_args__ = (
        UniqueConstraint("ein", name="uq_nonprofits_ein"),
        Index("ix_nonprofits_normalized_name", "normalized_name"),
        Index("ix_nonprofits_normalized_name_ein", "normalized_name", "ein"),
    )

    nonprofit_id: Mapped[int] = mapped_column(
        BIGINT_PRIMARY_KEY, Identity(start=1), primary_key=True, autoincrement=True
    )
    ein: Mapped[str] = mapped_column(String(9), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subsection_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    deductibility_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tax_deductible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    irs_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    country: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ntee_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    canonical_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    filings: Mapped[list["NonprofitFilingModel"]] = relationship(
        back_populates="nonprofit", cascade="all, delete-orphan"
    )
    sources: Mapped[list["NonprofitSourceModel"]] = relationship(
        back_populates="nonprofit", cascade="all, delete-orphan"
    )
    compliance_checks: Mapped[list["ComplianceCheckModel"]] = relationship(
        back_populates="nonprofit",
        cascade="all, delete-orphan",
    )


class NonprofitFilingModel(CustomerAccountsBase):
    __tablename__ = "nonprofit_filings"
    __table_args__ = (
        UniqueConstraint(
            "nonprofit_id",
            "tax_year",
            "form_type",
            "filing_date",
            "source_name",
            name="uq_nonprofit_filings_nonprofit_identity",
        ),
        Index(
            "ix_nonprofit_filings_nonprofit_tax_year",
            "nonprofit_id",
            "tax_year",
            "filing_date",
        ),
        Index(
            "ix_nonprofit_filings_nonprofit_latest",
            "nonprofit_id",
            "tax_year",
            "filing_date",
            "updated_at",
        ),
        Index(
            "ix_nonprofit_filings_nonprofit_source",
            "nonprofit_id",
            "source_name",
            "source_record_id",
        ),
    )

    filing_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonprofit_id: Mapped[int] = mapped_column(
        ForeignKey("nonprofits.nonprofit_id"), nullable=False
    )
    tax_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tax_period: Mapped[str | None] = mapped_column(String(16), nullable=True)
    form_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    total_assets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_income: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_revenue: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    xml_source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    nonprofit: Mapped[NonprofitModel] = relationship(back_populates="filings")


class NonprofitSourceModel(CustomerAccountsBase):
    __tablename__ = "nonprofit_sources"
    __table_args__ = (
        UniqueConstraint(
            "nonprofit_id",
            "source_id",
            "record_id",
            "retrieved_at",
            name="uq_nonprofit_sources_lineage",
        ),
        Index(
            "ix_nonprofit_sources_nonprofit_retrieved", "nonprofit_id", "retrieved_at"
        ),
        Index("ix_nonprofit_sources_nonprofit_source_id", "nonprofit_id", "source_id"),
    )

    nonprofit_source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonprofit_id: Mapped[int] = mapped_column(
        ForeignKey("nonprofits.nonprofit_id"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_as_of: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    driver: Mapped[str | None] = mapped_column(String(64), nullable=True)
    integration_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tenant_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    required_for_eligibility: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    evaluation_effect: Mapped[str | None] = mapped_column(String(32), nullable=True)
    explanation_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    licensed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    normalized_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    nonprofit: Mapped[NonprofitModel] = relationship(back_populates="sources")


class ComplianceCheckModel(CustomerAccountsBase):
    __tablename__ = "compliance_checks"
    __table_args__ = (
        Index(
            "ix_compliance_checks_nonprofit_evaluated", "nonprofit_id", "evaluated_at"
        ),
        Index("ix_compliance_checks_nonprofit_type", "nonprofit_id", "check_type"),
        Index(
            "ix_compliance_checks_nonprofit_type_evaluated",
            "nonprofit_id",
            "check_type",
            "evaluated_at",
        ),
    )

    compliance_check_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonprofit_id: Mapped[int] = mapped_column(
        ForeignKey("nonprofits.nonprofit_id"), nullable=False
    )
    check_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    policy_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    registration_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_jurisdiction: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    registration_expiration_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    solicitation_permitted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    state_business_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_business_good_standing: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    final_recommendation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    flags_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    reasons_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    evidence_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_VARIANT, nullable=True
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON_VARIANT, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    nonprofit: Mapped[NonprofitModel] = relationship(back_populates="compliance_checks")


class Form990ArchiveModel(CustomerAccountsBase):
    __tablename__ = "form990_archives"
    __table_args__ = (
        UniqueConstraint("source_url", name="uq_form990_archives_source_url"),
        Index("ix_form990_archives_last_checked_at", "last_checked_at"),
    )

    archive_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    extracted_files: Mapped[list["Form990ExtractedFileModel"]] = relationship(
        back_populates="archive",
        cascade="all, delete-orphan",
    )


class Form990ExtractedFileModel(CustomerAccountsBase):
    __tablename__ = "form990_extracted_files"
    __table_args__ = (
        UniqueConstraint(
            "archive_id", "filename", name="uq_form990_extracted_files_archive_filename"
        ),
        Index(
            "ix_form990_extracted_files_archive_status", "archive_id", "parse_status"
        ),
    )

    file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    archive_id: Mapped[str] = mapped_column(
        ForeignKey("form990_archives.archive_id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parse_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    archive: Mapped[Form990ArchiveModel] = relationship(
        back_populates="extracted_files"
    )
