from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from charity_status_platform.customer_accounts import CustomerAccountsBase, build_customer_accounts_engine, build_customer_accounts_session_factory
from charity_status_platform.customer_accounts.sqlalchemy_db import customer_accounts_session_scope
from charity_status_platform.nonprofits import (
    ComplianceCheckRecord,
    NonprofitFilingRecord,
    NonprofitModel,
    NonprofitRecord,
    NonprofitSourceRecord,
    SqlAlchemyNonprofitRepository,
    build_nonprofit_id,
    make_record_id,
)
from charity_status_platform.runtime import build_nonprofit_postgres_repository


def _session_factory(tmp_path: Path):
    db_path = tmp_path / "nonprofits.sqlite3"
    engine = build_customer_accounts_engine(f"sqlite+pysqlite:///{db_path}")
    CustomerAccountsBase.metadata.create_all(engine)
    return build_customer_accounts_session_factory(engine)


def test_customer_accounts_metadata_contains_nonprofit_foundation_tables():
    table_names = set(CustomerAccountsBase.metadata.tables.keys())

    assert "nonprofits" in table_names
    assert "nonprofit_filings" in table_names
    assert "nonprofit_sources" in table_names
    assert "compliance_checks" in table_names


def test_nonprofit_repository_upserts_and_reads_nonprofit_related_records(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    nonprofit = NonprofitRecord(
        nonprofit_id=build_nonprofit_id("12-3456789"),
        ein="12-3456789",
        canonical_name="Example Nonprofit",
        normalized_name="example nonprofit",
        subsection_code="03",
        deductibility_code="1",
        tax_deductible=True,
        entity_type="charitable organization",
        irs_status="active",
        country="US",
        state="IL",
        ntee_category="B",
        canonical_source="irs_eo_bmf_athena",
        source_version="2026.03",
        last_seen_at="2026-03-31T00:00:00+00:00",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
    )
    repository.upsert_nonprofit(nonprofit)

    filing = NonprofitFilingRecord(
        filing_id=make_record_id("fil"),
        nonprofit_id=nonprofit.nonprofit_id,
        tax_year=2024,
        tax_period="202412",
        form_type="990",
        filing_date="2025-05-15",
        amended=False,
        parse_status="parsed",
        total_assets=120000,
        total_income=80000,
        total_revenue=76000,
        source_name="irs_form990",
        source_record_id="return-123",
        raw_payload={"return_type": "990"},
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
    )
    source = NonprofitSourceRecord(
        nonprofit_source_id=make_record_id("src"),
        nonprofit_id=nonprofit.nonprofit_id,
        source_id="state_registry.compliance",
        provider_name="state_registry",
        category="compliance",
        record_id="registry-1",
        retrieved_at="2026-03-31T00:00:00+00:00",
        valid_as_of="2026-03-31T00:00:00+00:00",
        status="matched",
        driver="scraper",
        integration_id="state_registry",
        tenant_enabled=True,
        required_for_eligibility=False,
        evaluation_effect="positive",
        explanation_code="integration_successfully_evaluated",
        explanation="Matched and evaluated",
        licensed=False,
        notes="Public registry",
        normalized_data={"registration_status": "active"},
        raw_payload={"source_payload": {"status": "active"}},
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
    )
    check_old = ComplianceCheckRecord(
        compliance_check_id=make_record_id("chk"),
        nonprofit_id=nonprofit.nonprofit_id,
        check_type="state_compliance",
        status="warning",
        evaluated_at="2026-03-31T00:00:00+00:00",
        final_recommendation="review",
        flags_json=["registration_expiring"],
        reasons_json=[{"code": "expiring"}],
        evidence_json={"sources": ["state_registry.compliance"]},
        summary_json={"status": "warning"},
        metadata_json={"policy_evaluation": {"result": "warning"}},
        created_at="2026-03-31T00:00:00+00:00",
    )
    check_new = ComplianceCheckRecord(
        compliance_check_id=make_record_id("chk"),
        nonprofit_id=nonprofit.nonprofit_id,
        check_type="state_compliance",
        status="pass",
        evaluated_at="2026-04-01T00:00:00+00:00",
        final_recommendation="approve",
        summary_json={"status": "pass"},
        created_at="2026-04-01T00:00:00+00:00",
    )

    repository.upsert_filing(filing)
    repository.upsert_source(source)
    repository.create_compliance_check(check_old)
    repository.create_compliance_check(check_new)

    fetched = repository.get_nonprofit_by_ein("123456789")
    filings = repository.list_filings_for_nonprofit(nonprofit.nonprofit_id, limit=1)
    sources = repository.list_sources_for_nonprofit(nonprofit.nonprofit_id, source_id="state_registry.compliance")
    latest_check = repository.latest_compliance_check(nonprofit.nonprofit_id, check_type="state_compliance")

    assert fetched is not None
    assert fetched.canonical_name == "Example Nonprofit"
    assert filings[0].form_type == "990"
    assert sources[0].provider_name == "state_registry"
    assert latest_check is not None
    assert latest_check.status == "pass"
    assert latest_check.final_recommendation == "approve"


def test_nonprofits_table_enforces_unique_ein(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    repository = SqlAlchemyNonprofitRepository(session_factory)
    repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=build_nonprofit_id("123456789"),
            ein="123456789",
            canonical_name="Org One",
            normalized_name="org one",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )

    with pytest.raises(IntegrityError):
        with customer_accounts_session_scope(session_factory) as session:
            session.add(
                NonprofitModel(
                    nonprofit_id="npo_duplicate",
                    ein="123456789",
                    canonical_name="Org Two",
                    normalized_name="org two",
                    revoked=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.flush()


def test_runtime_builder_returns_nonprofit_postgres_repository_only_when_selected(tmp_path: Path):
    sqlite_url = f"sqlite+pysqlite:///{tmp_path / 'nonprofit_runtime.sqlite3'}"
    engine = build_customer_accounts_engine(sqlite_url)
    CustomerAccountsBase.metadata.create_all(engine)

    repository = build_nonprofit_postgres_repository(
        {
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": sqlite_url,
            "PLATFORM_NONPROFIT_STORE_BACKEND": "postgres",
        }
    )
    disabled = build_nonprofit_postgres_repository({})

    assert repository is not None
    assert disabled is None
