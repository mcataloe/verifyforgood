from __future__ import annotations

import pathlib
from pathlib import Path

from infrastructure.charity_status.form990.index import parse_index_records
from infrastructure.charity_status.form990.ingest import ingest_form990_records

from charity_status_platform.customer_accounts import CustomerAccountsBase, build_customer_accounts_engine, build_customer_accounts_session_factory
from charity_status_platform.nonprofits import Form990NonprofitPersistenceService, SqlAlchemyNonprofitRepository


def _repository(tmp_path: Path) -> SqlAlchemyNonprofitRepository:
    db_path = tmp_path / "nonprofit_ingest.sqlite3"
    engine = build_customer_accounts_engine(f"sqlite+pysqlite:///{db_path}")
    CustomerAccountsBase.metadata.create_all(engine)
    return SqlAlchemyNonprofitRepository(build_customer_accounts_session_factory(engine))


def test_form990_persistence_service_is_repeat_safe_and_updates_existing_rows(tmp_path: Path):
    repository = _repository(tmp_path)
    service = Form990NonprofitPersistenceService(repository)

    initial = {
        "ein": "12-3456789",
        "tax_year": "2024",
        "tax_period_end": "2024-12-31",
        "filing_date": "2025-05-15",
        "return_type": "990",
        "irs_object_id": "object-1",
        "parse_status": "parsed",
        "total_revenue": "1000",
        "total_assets_eoy": "2000",
        "source_archive": "2024_TEOS_XML_01A",
        "source_year": "2024",
        "source_signature": "sig-1",
        "xml_source_reference": "s3://bucket/archive.zip#object-1.xml",
        "raw_file_reference": "workspace://form990/raw-sources/2024/zip_archive/2024_TEOS_XML_01A/object-1.xml",
    }
    updated = {
        **initial,
        "total_revenue": "3000",
        "source_signature": "sig-2",
    }

    first = service.persist_normalized_records([initial])
    second = service.persist_normalized_records([updated])

    nonprofit = repository.get_nonprofit_by_ein("123456789")
    filings = repository.list_filings_for_nonprofit(nonprofit.nonprofit_id)
    sources = repository.list_sources_for_nonprofit(nonprofit.nonprofit_id)

    assert first.to_dict() == {
        "nonprofits_upserted": 1,
        "filings_upserted": 1,
        "sources_upserted": 1,
        "skipped_records": 0,
    }
    assert second.filings_upserted == 1
    assert len(filings) == 1
    assert len(sources) == 1
    assert filings[0].total_revenue == 3000
    assert filings[0].source_signature == "sig-2"
    assert sources[0].source_signature == "sig-2"
    assert sources[0].normalized_data["source_archive"] == "2024_TEOS_XML_01A"


def test_ingest_form990_records_persists_to_nonprofit_repository_when_hook_is_present(tmp_path: Path):
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    repository = _repository(tmp_path)
    persistence_service = Form990NonprofitPersistenceService(repository)
    records = parse_index_records(
        [
            {
                "ein": "123456789",
                "tax_year": "2023",
                "filing_date": "2024-05-15",
                "return_type": "990",
                "irs_object_id": "obj-1",
                "xml_url": "https://example.org/obj-1.xml",
                "source_archive": "2023_TEOS_XML_01A",
                "source_signature": "sig-obj-1",
            }
        ]
    )

    result = ingest_form990_records(
        records=records,
        download_raw=True,
        downloader=lambda url: xml_content,
        nonprofit_persistence_service=persistence_service,
    )

    nonprofit = repository.get_nonprofit_by_ein("123456789")
    filings = repository.list_filings_for_nonprofit(nonprofit.nonprofit_id)
    sources = repository.list_sources_for_nonprofit(nonprofit.nonprofit_id)

    assert result.nonprofit_persistence == {
        "nonprofits_upserted": 1,
        "filings_upserted": 1,
        "sources_upserted": 1,
        "skipped_records": 0,
    }
    assert len(filings) == 1
    assert len(sources) == 1
    assert filings[0].raw_file_reference == "https://example.org/obj-1.xml"
