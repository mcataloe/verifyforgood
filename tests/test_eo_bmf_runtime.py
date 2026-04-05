from __future__ import annotations

from pathlib import Path

from charity_status_backend.ingest_task.eo_bmf_ingest import EO_BMF_FILING_FORM_TYPE, ingest_eo_bmf_csv
from charity_status_backend.ingest_task.eo_bmf_runner import run_local_eo_bmf_ingest
from charity_status_platform.customer_accounts import (
    CustomerAccountsBase,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
)
from charity_status_platform.nonprofits import (
    NonprofitFilingRecord,
    NonprofitRecord,
    PostgresNonprofitQueryClient,
    SqlAlchemyNonprofitRepository,
)


def _repository(tmp_path: Path) -> tuple[SqlAlchemyNonprofitRepository, str]:
    sqlite_url = f"sqlite+pysqlite:///{tmp_path / 'eo_bmf.sqlite3'}"
    engine = build_customer_accounts_engine(sqlite_url)
    CustomerAccountsBase.metadata.create_all(engine)
    repository = SqlAlchemyNonprofitRepository(build_customer_accounts_session_factory(engine))
    return repository, sqlite_url


def test_ingest_eo_bmf_csv_upserts_nonprofit_and_pseudo_filing(tmp_path: Path):
    repository, _sqlite_url = _repository(tmp_path)
    csv_path = tmp_path / "eo1.csv"
    csv_path.write_text(
        ",".join(
            [
                "12-3456789",
                "Example EO Org",
                "",
                "123 Main",
                "Chicago",
                "IL",
                "60601",
                "",
                "03",
                "",
                "",
                "",
                "1",
                "",
                "",
                "",
                "1",
                "202412",
                "",
                "",
                "1",
                "",
                "",
                "120000",
                "80000",
                "76000",
                "P20",
                "example eo org",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stats = ingest_eo_bmf_csv(
        path=str(csv_path),
        filename="eo1.csv",
        repository=repository,
    )

    snapshot = repository.get_nonprofit_snapshot_by_ein("123456789")
    filings = repository.list_filings_by_ein("123456789")

    assert stats.status == "success"
    assert stats.nonprofits_upserted == 1
    assert stats.filings_upserted == 1
    assert stats.invalid_rows == 0
    assert snapshot is not None
    assert snapshot["name"] == "Example EO Org"
    assert snapshot["tax_period"] == "202412"
    assert snapshot["asset_amt"] == 120000
    assert filings[0]["return_type"] == EO_BMF_FILING_FORM_TYPE


def test_postgres_query_client_filters_eo_bmf_pseudo_filings(tmp_path: Path):
    repository, _sqlite_url = _repository(tmp_path)
    nonprofit = repository.upsert_nonprofit(
        NonprofitRecord(
            nonprofit_id=None,
            ein="123456789",
            canonical_name="Example Org",
            normalized_name="example org",
            canonical_source="irs.eo_bmf",
            created_at="2026-04-05T00:00:00+00:00",
            updated_at="2026-04-05T00:00:00+00:00",
        )
    )
    repository.upsert_filing(
        NonprofitFilingRecord(
            filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            tax_year=2024,
            tax_period="202412",
            form_type=EO_BMF_FILING_FORM_TYPE,
            filing_date=None,
            amended=False,
            parse_status="parsed",
            source_name="irs.eo_bmf",
            source_record_id="eo-bmf-row",
            created_at="2026-04-05T00:00:00+00:00",
            updated_at="2026-04-05T00:00:00+00:00",
        )
    )
    repository.upsert_filing(
        NonprofitFilingRecord(
            filing_id=None,
            nonprofit_id=nonprofit.nonprofit_id,
            tax_year=2023,
            tax_period="202312",
            form_type="990",
            filing_date="2024-05-15",
            amended=False,
            parse_status="parsed",
            source_name="irs_form990",
            source_record_id="return-123",
            created_at="2026-04-05T00:00:00+00:00",
            updated_at="2026-04-05T00:00:00+00:00",
        )
    )
    client = PostgresNonprofitQueryClient(
        repository=repository,
        delegate_client=type(
            "Delegate",
            (),
            {
                "lookup_form990_enrichment": staticmethod(lambda ein: (None, None, None, None)),
                "lookup_peer_benchmark": staticmethod(lambda group: {"count": 0, "metrics": {}}),
            },
        )(),
    )

    _source, filings = client.list_form990_filings("123456789", limit=10)

    assert filings == [
        {
            "ein": "123456789",
            "tax_year": "2023",
            "return_type": "990",
            "filing_date": "2024-05-15",
            "amended_return": "false",
            "parse_status": "parsed",
        }
    ]


def test_run_local_eo_bmf_ingest_downloads_and_cleans_workspace(tmp_path: Path, monkeypatch):
    repository, sqlite_url = _repository(tmp_path)
    workspace = tmp_path / "workspace"

    def _fake_download(*, url: str, destination: Path, timeout_seconds: int) -> None:
        assert timeout_seconds == 300
        destination.write_text(
            "12-3456789,Runtime EO Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,runtime eo org\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "charity_status_backend.ingest_task.eo_bmf_runner._download_file_to_path",
        _fake_download,
    )
    monkeypatch.setattr(
        "charity_status_backend.ingest_task.eo_bmf_runner.IRS_FILES",
        ["eo1.csv"],
    )

    exit_code = run_local_eo_bmf_ingest(
        strict=False,
        keep_temp=False,
        workspace=str(workspace),
        env={
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": sqlite_url,
            "PLATFORM_NONPROFIT_STORE_BACKEND": "postgres",
            "PLATFORM_NONPROFIT_QUERY_BACKEND": "postgres",
            "EO_BMF_DOWNLOAD_TIMEOUT_SECONDS": "300",
        },
    )

    snapshot = repository.get_nonprofit_snapshot_by_ein("123456789")

    assert exit_code == 0
    assert snapshot is not None
    assert snapshot["name"] == "Runtime EO Org"
    assert not any((workspace / "downloads").glob("*.csv"))
