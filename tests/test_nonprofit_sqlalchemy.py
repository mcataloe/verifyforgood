from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from charity_status_platform.customer_accounts import CustomerAccountsBase, build_customer_accounts_engine, build_customer_accounts_session_factory
from charity_status_platform.customer_accounts.sqlalchemy_db import customer_accounts_session_scope
from charity_status_platform.nonprofits import (
    ComplianceCheckRecord,
    Form990ArchiveRecord,
    Form990ExtractedFileRecord,
    NonprofitFilingRecord,
    NonprofitModel,
    NonprofitRecord,
    NonprofitRawFilingRecord,
    PostgresNonprofitQueryClient,
    NonprofitSourceRecord,
    SqlAlchemyNonprofitRepository,
)
from charity_status_platform.runtime import build_nonprofit_postgres_repository, build_nonprofit_query_client


def _session_factory(tmp_path: Path):
    db_path = tmp_path / "nonprofits.sqlite3"
    engine = build_customer_accounts_engine(f"sqlite+pysqlite:///{db_path}")
    CustomerAccountsBase.metadata.create_all(engine)
    return build_customer_accounts_session_factory(engine)


def test_customer_accounts_metadata_contains_nonprofit_foundation_tables():
    table_names = set(CustomerAccountsBase.metadata.tables.keys())

    assert "nonprofits" in table_names
    assert "nonprofit_filings" in table_names
    assert "nonprofit_raw_filings" in table_names
    assert "nonprofit_sources" in table_names
    assert "compliance_checks" in table_names
    assert "form990_archives" in table_names
    assert "form990_extracted_files" in table_names


def test_nonprofit_model_allows_extended_ntee_category_labels():
    ntee_column = NonprofitModel.__table__.c["ntee_category"]

    assert getattr(ntee_column.type, "length", None) == 128


def test_nonprofit_model_allows_extended_entity_type_labels():
    entity_type_column = NonprofitModel.__table__.c["entity_type"]

    assert getattr(entity_type_column.type, "length", None) == 128


def test_nonprofit_repository_tracks_form990_archive_and_extracted_file_metadata(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    archive = Form990ArchiveRecord(
        archive_id=None,
        source_url="https://example.org/2025_TEOS_XML_01A.zip",
        filename="2025_TEOS_XML_01A.zip",
        etag="etag-1",
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
        response_status=200,
        last_checked_at="2026-04-03T00:00:00+00:00",
        status="pending",
        created_at="2026-04-03T00:00:00+00:00",
        update_started_at="2026-04-03T00:00:00+00:00",
    )
    archive = repository.upsert_archive_probe(archive)
    repository.upsert_extracted_file(
        Form990ExtractedFileRecord(
            file_id=None,
            archive_id=archive.archive_id,
            filename="folder/object-1.xml",
            content_hash="abc123",
            parse_status="parsed",
            parsed_at="2026-04-03T00:05:00+00:00",
            created_at="2026-04-03T00:05:00+00:00",
            updated_at="2026-04-03T00:05:00+00:00",
        )
    )

    fetched_archive = repository.get_archive_by_source_url("https://example.org/2025_TEOS_XML_01A.zip")
    fetched_file = repository.get_extracted_file(archive.archive_id, "folder/object-1.xml")
    archive_files = repository.list_extracted_files_for_archive(archive.archive_id)
    processed = repository.mark_archive_processing(
        archive.archive_id,
        started_at="2026-04-03T00:00:00+00:00",
        ended_at="2026-04-03T00:10:00+00:00",
        processed_at="2026-04-03T00:10:00+00:00",
        status="processed",
    )

    assert fetched_archive is not None
    assert fetched_archive.etag == "etag-1"
    assert fetched_file is not None
    assert fetched_file.content_hash == "abc123"
    assert len(archive_files) == 1
    assert processed is not None
    assert processed.status == "processed"
    assert processed.update_started_at == "2026-04-03T00:00:00+00:00"
    assert processed.update_ended_at == "2026-04-03T00:10:00+00:00"
    assert processed.processing_duration_ms == 600000


def test_nonprofit_repository_upserts_and_reads_nonprofit_related_records(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    nonprofit = NonprofitRecord(
        nonprofit_id=None,
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
        canonical_source="irs.eo_bmf",
        source_version="2026.03",
        last_seen_at="2026-03-31T00:00:00+00:00",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
    )
    nonprofit = repository.upsert_nonprofit(nonprofit)

    filing = NonprofitFilingRecord(
        filing_id=None,
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
        nonprofit_source_id=None,
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
        compliance_check_id=None,
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
        compliance_check_id=None,
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
    assert isinstance(fetched.nonprofit_id, int)


def test_nonprofit_repository_tracks_canonical_raw_filing_versions(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    nonprofit = repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=None,
            ein="12-3456789",
            canonical_name="Example Nonprofit",
            normalized_name="example nonprofit",
            created_at="2026-04-07T00:00:00+00:00",
            updated_at="2026-04-07T00:00:00+00:00",
        )
    )
    filing = repository.upsert_filing(
        NonprofitFilingRecord(
            filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            tax_year=2024,
            tax_period="202412",
            form_type="990",
            filing_date="2025-05-15",
            amended=False,
            parse_status="parsed",
            source_name="irs.form990",
            source_record_id="return-123",
            created_at="2026-04-07T00:00:00+00:00",
            updated_at="2026-04-07T00:00:00+00:00",
        )
    )

    first = repository.upsert_raw_filing(
        NonprofitRawFilingRecord(
            raw_filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            filing_id=filing.filing_id,
            tax_year=2024,
            form_type="990",
            filing_date="2025-05-15",
            source_name="irs.form990",
            source_record_id="return-123",
            source_signature="sig-1",
            xml_content_hash="hash-1",
            xml_artifact_reference="workspace://archive#return-123.xml",
            parse_status="parsed",
            parser_version="form990.xml_parser.v1",
            canonicalization_version="form990.raw_filing_json.v1",
            raw_filing_json={"Return": {"ReturnHeader": {"ReturnTypeCd": "990"}}},
            created_at="2026-04-07T00:00:00+00:00",
            updated_at="2026-04-07T00:00:00+00:00",
        )
    )
    second = repository.upsert_raw_filing(
        NonprofitRawFilingRecord(
            raw_filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            filing_id=filing.filing_id,
            tax_year=2024,
            form_type="990",
            filing_date="2025-05-15",
            source_name="irs.form990",
            source_record_id="return-123",
            source_signature="sig-2",
            xml_content_hash="hash-2",
            xml_artifact_reference="workspace://archive#return-123.xml",
            parse_status="parsed",
            parser_version="form990.xml_parser.v1",
            canonicalization_version="form990.raw_filing_json.v1",
            raw_filing_json={"Return": {"ReturnHeader": {"ReturnTypeCd": "990"}, "Version": "2"}},
            created_at="2026-04-07T00:05:00+00:00",
            updated_at="2026-04-07T00:05:00+00:00",
        )
    )

    fetched_by_identity = repository.get_raw_filing_by_identity(
        nonprofit_id=nonprofit.nonprofit_id,
        tax_year=2024,
        form_type="990",
        filing_date="2025-05-15",
        source_name="irs.form990",
    )
    fetched_latest = repository.get_latest_raw_filing_by_ein("123456789", tax_year=2024, form_type="990")

    assert first.raw_filing_id is not None
    assert second.raw_filing_id is not None
    assert first.raw_filing_id != second.raw_filing_id
    assert fetched_by_identity is not None
    assert fetched_by_identity.xml_content_hash == "hash-2"
    assert fetched_latest is not None
    assert fetched_latest.source_signature == "sig-2"


def test_nonprofit_repository_accepts_iso_datetime_for_filing_date(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    nonprofit = NonprofitRecord(
        nonprofit_id=None,
        ein="12-3456789",
        canonical_name="Example Nonprofit",
        normalized_name="example nonprofit",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
    )
    nonprofit = repository.upsert_nonprofit(nonprofit)

    repository.upsert_filing(
        NonprofitFilingRecord(
            filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            tax_year=2023,
            tax_period="202312",
            form_type="990",
            filing_date="2023-12-22T13:23:38-06:00",
            amended=False,
            parse_status="parsed",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )

    filings = repository.list_filings_for_nonprofit(nonprofit.nonprofit_id)

    assert filings[0].filing_date == "2023-12-22"


def test_nonprofit_repository_supports_large_financial_values(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    nonprofit = NonprofitRecord(
        nonprofit_id=None,
        ein="98-6001153",
        canonical_name="Large Balance Nonprofit",
        normalized_name="large balance nonprofit",
        created_at="2026-04-04T00:00:00+00:00",
        updated_at="2026-04-04T00:00:00+00:00",
    )
    nonprofit = repository.upsert_nonprofit(nonprofit)

    repository.upsert_filing(
        NonprofitFilingRecord(
            filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            tax_year=2022,
            tax_period="2023-04-30",
            form_type="990",
            filing_date="2023-12-22",
            amended=False,
            parse_status="parsed",
            total_assets=4_474_648_174,
            total_income=2_345_678_901,
            total_revenue=1_248_945_332,
            source_name="irs.form990",
            source_record_id="202333569349300603_public",
            created_at="2026-04-04T00:00:00+00:00",
            updated_at="2026-04-04T00:00:00+00:00",
        )
    )

    filings = repository.list_filings_for_nonprofit(nonprofit.nonprofit_id)

    assert filings[0].total_assets == 4_474_648_174
    assert filings[0].total_income == 2_345_678_901
    assert filings[0].total_revenue == 1_248_945_332


def test_nonprofit_repository_supports_snapshot_search_and_ein_queries(tmp_path: Path):
    repository = SqlAlchemyNonprofitRepository(_session_factory(tmp_path))
    nonprofit = NonprofitRecord(
        nonprofit_id=None,
        ein="12-3456789",
        canonical_name="Helping Hands Foundation",
        normalized_name="helping hands foundation",
        subsection_code="03",
        deductibility_code="1",
        irs_status="active",
        state="IL",
        ntee_category="P20",
        created_at="2026-03-31T00:00:00+00:00",
        updated_at="2026-03-31T00:00:00+00:00",
    )
    nonprofit = repository.upsert_nonprofit(nonprofit)
    repository.upsert_filing(
        NonprofitFilingRecord(
            filing_id=None,
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
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )
    repository.create_compliance_check(
        ComplianceCheckRecord(
            compliance_check_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            check_type="state_compliance",
            status="pass",
            evaluated_at="2026-04-01T00:00:00+00:00",
            created_at="2026-04-01T00:00:00+00:00",
        )
    )
    repository.upsert_source(
        NonprofitSourceRecord(
            nonprofit_source_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            source_id="state_registry_mock",
            provider_name="state_registry",
            category="compliance",
            record_id="registry-1",
            retrieved_at="2026-04-02T00:00:00+00:00",
            created_at="2026-04-02T00:00:00+00:00",
            updated_at="2026-04-02T00:00:00+00:00",
        )
    )

    snapshot = repository.get_nonprofit_snapshot_by_ein("123456789")
    search_rows = repository.search_nonprofit_summaries(name_query="helping", limit=10, state="IL", subsection="03", active_only=True)
    filing_rows = repository.list_filings_by_ein("123456789")
    source_rows = repository.list_sources_by_ein("123456789", source_id="state_registry_mock")
    latest_check = repository.latest_compliance_check_by_ein("123456789", check_type="state_compliance")
    eins = repository.list_nonprofit_eins_page(limit=10)

    assert snapshot == {
        "ein": "123456789",
        "name": "Helping Hands Foundation",
        "state": "IL",
        "subsection": "03",
        "status": "active",
        "deductibility": "1",
        "ntee_cd": "P20",
        "tax_period": "202412",
        "asset_amt": 120000,
        "income_amt": 80000,
        "revenue_amt": 76000,
    }
    assert search_rows == [
        {
            "ein": "123456789",
            "name": "Helping Hands Foundation",
            "state": "IL",
            "subsection": "03",
            "status": "active",
            "tax_period": "202412",
        }
    ]
    assert filing_rows == [
        {
            "ein": "123456789",
            "tax_year": "2024",
            "return_type": "990",
            "filing_date": "2025-05-15",
            "amended_return": "false",
            "parse_status": "parsed",
        }
    ]
    assert source_rows[0].source_id == "state_registry_mock"
    assert latest_check is not None
    assert latest_check.status == "pass"
    assert eins == ["123456789"]


def test_nonprofits_table_enforces_unique_ein(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    repository = SqlAlchemyNonprofitRepository(session_factory)
    repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=None,
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
                    nonprofit_id=999,
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


def test_runtime_builder_returns_postgres_nonprofit_query_client_only_when_selected(tmp_path: Path):
    sqlite_url = f"sqlite+pysqlite:///{tmp_path / 'nonprofit_query_runtime.sqlite3'}"
    engine = build_customer_accounts_engine(sqlite_url)
    CustomerAccountsBase.metadata.create_all(engine)
    repository = SqlAlchemyNonprofitRepository(build_customer_accounts_session_factory(engine))
    repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=None,
            ein="123456789",
            canonical_name="Query Runtime Org",
            normalized_name="query runtime org",
            created_at="2026-03-31T00:00:00+00:00",
            updated_at="2026-03-31T00:00:00+00:00",
        )
    )

    athena_delegate = type(
        "AthenaDelegate",
        (),
        {
            "lookup_form990_enrichment": staticmethod(lambda ein: (None, None, None, None)),
            "lookup_peer_benchmark": staticmethod(lambda group: {"count": 0, "metrics": {}}),
        },
    )()
    client = build_nonprofit_query_client(
        athena_client=athena_delegate,
        env={
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": sqlite_url,
            "PLATFORM_NONPROFIT_QUERY_BACKEND": "postgres",
        },
    )
    disabled = build_nonprofit_query_client(athena_client=athena_delegate, env={})

    assert isinstance(client, PostgresNonprofitQueryClient)
    assert disabled is athena_delegate
    assert client.lookup_nonprofit("123456789")[1]["name"] == "Query Runtime Org"
