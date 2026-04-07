from __future__ import annotations

import json
from pathlib import Path

import pytest

from charity_status_backend.ingest_task.eo_bmf_ingest import EO_BMF_FILING_FORM_TYPE, ingest_eo_bmf_csv
from charity_status_backend.ingest_task.eo_bmf_runner import run_local_eo_bmf_ingest
from charity_status_platform.customer_accounts import (
    CustomerAccountsBase,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
)
from charity_status_platform.nonprofits import (
    EoBmfNonprofitPersistenceService,
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


class RecordingProgressSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.completed = False

    def item_completed(self, increments=None, *, last_item=None) -> None:
        self.calls.append({"increments": dict(increments or {}), "last_item": last_item})

    def complete(self) -> None:
        self.completed = True


class RecordingProgressReporter:
    def __init__(self) -> None:
        self.starts: list[dict[str, object]] = []
        self.sessions: list[RecordingProgressSession] = []

    def start(self, *, total_items, fields, update_every=10):
        session = RecordingProgressSession()
        self.starts.append(
            {
                "total_items": total_items,
                "field_keys": [field.key for field in fields],
                "update_every": update_every,
            }
        )
        self.sessions.append(session)
        return session


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
    assert stats.map_duration_ms >= 0
    assert stats.nonprofit_upsert_duration_ms >= 0
    assert stats.filing_upsert_duration_ms >= 0
    assert stats.db_upsert_duration_ms == stats.nonprofit_upsert_duration_ms + stats.filing_upsert_duration_ms
    assert stats.rows_per_second >= 0.0
    assert stats.nonprofit_upserts_per_second >= 0.0
    assert stats.filing_upserts_per_second >= 0.0
    assert stats.invalid_row_rate == 0.0
    assert 0.0 <= stats.db_time_share <= 1.0
    assert snapshot is not None
    assert snapshot["name"] == "Example EO Org"
    assert snapshot["tax_period"] == "202412"
    assert snapshot["asset_amt"] == 120000
    assert filings[0]["return_type"] == EO_BMF_FILING_FORM_TYPE


def test_ingest_eo_bmf_csv_reports_progress_for_processed_and_invalid_rows(tmp_path: Path):
    repository, _sqlite_url = _repository(tmp_path)
    csv_path = tmp_path / "eo-progress.csv"
    csv_path.write_text(
        (
            "12-3456789,Example EO Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,example eo org\n"
            "bad-ein,Invalid Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,invalid org\n"
            "98-7654321,Second EO Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,second eo org\n"
        ),
        encoding="utf-8",
    )
    reporter = RecordingProgressReporter()

    stats = ingest_eo_bmf_csv(
        path=str(csv_path),
        filename="eo-progress.csv",
        repository=repository,
        batch_size=2,
        progress_reporter=reporter,
    )

    assert stats.status == "success"
    assert stats.rows_seen == 3
    assert stats.invalid_rows == 1
    assert reporter.starts == [{"total_items": 3, "field_keys": ["processed", "invalid"], "update_every": 10}]
    assert reporter.sessions[0].calls == [
        {"increments": {"invalid": 1}, "last_item": "eo-progress.csv:row:2"},
        {"increments": {"processed": 1}, "last_item": "123456789:eo-progress.csv:202412"},
        {"increments": {"processed": 1}, "last_item": "987654321:eo-progress.csv:202412"},
    ]
    assert reporter.sessions[0].completed is True


def test_ingest_eo_bmf_csv_keeps_committed_batches_when_later_batch_fails(tmp_path: Path, monkeypatch):
    repository, _sqlite_url = _repository(tmp_path)
    csv_path = tmp_path / "eo-failure.csv"
    csv_path.write_text(
        (
            "11-1111111,First Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,first org\n"
            "22-2222222,Second Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,second org\n"
            "33-3333333,Third Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,third org\n"
        ),
        encoding="utf-8",
    )
    service = EoBmfNonprofitPersistenceService(repository)
    real_persist_batch = service.persist_batch
    call_count = {"value": 0}

    def _flaky_persist_batch(records):
        call_count["value"] += 1
        if call_count["value"] == 2:
            raise RuntimeError("simulated batch failure")
        return real_persist_batch(records)

    monkeypatch.setattr(service, "persist_batch", _flaky_persist_batch)

    with pytest.raises(RuntimeError, match="simulated batch failure"):
        ingest_eo_bmf_csv(
            path=str(csv_path),
            filename="eo-failure.csv",
            persistence_service=service,
            batch_size=2,
        )

    assert repository.get_nonprofit_snapshot_by_ein("111111111") is not None
    assert repository.get_nonprofit_snapshot_by_ein("222222222") is not None
    assert repository.get_nonprofit_snapshot_by_ein("333333333") is None


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


def test_run_local_eo_bmf_ingest_downloads_and_cleans_workspace(tmp_path: Path, monkeypatch, capsys):
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
    stdout_lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    completion_payload = json.loads(stdout_lines[-1])
    file_log_payload = next(
        json.loads(line)
        for line in stdout_lines
        if '"component": "eo_bmf.file"' in line and '"message": "file processed"' in line
    )

    assert exit_code == 0
    assert snapshot is not None
    assert snapshot["name"] == "Runtime EO Org"
    assert not any((workspace / "downloads").glob("*.csv"))
    assert completion_payload["total_run_duration_ms"] >= 0
    assert completion_payload["rows_per_second"] >= 0.0
    assert completion_payload["nonprofit_upserts_per_second"] >= 0.0
    assert completion_payload["filing_upserts_per_second"] >= 0.0
    assert completion_payload["invalid_row_rate"] == 0.0
    assert completion_payload["files"][0]["download_duration_ms"] >= 0
    assert completion_payload["files"][0]["total_file_duration_ms"] >= 0
    assert completion_payload["files"][0]["map_duration_ms"] >= 0
    assert completion_payload["files"][0]["db_upsert_duration_ms"] >= 0
    assert file_log_payload["download_duration_ms"] >= 0
    assert file_log_payload["total_file_duration_ms"] >= 0


def test_run_local_eo_bmf_ingest_processes_multiple_files_with_workers(tmp_path: Path, monkeypatch, capsys):
    repository, sqlite_url = _repository(tmp_path)
    workspace = tmp_path / "workspace"

    def _fake_download(*, url: str, destination: Path, timeout_seconds: int) -> None:
        destination.write_text(
            (
                "12-3456789,Runtime EO Org,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,120000,80000,76000,P20,runtime eo org\n"
                if destination.name == "eo1.csv"
                else "98-7654321,Runtime EO Org Two,,,Chicago,IL,60601,,03,,,,1,,,,1,202412,,,,,,,220000,180000,176000,P20,runtime eo org two\n"
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "charity_status_backend.ingest_task.eo_bmf_runner._download_file_to_path",
        _fake_download,
    )
    monkeypatch.setattr(
        "charity_status_backend.ingest_task.eo_bmf_runner.IRS_FILES",
        ["eo1.csv", "eo2.csv"],
    )

    exit_code = run_local_eo_bmf_ingest(
        strict=False,
        keep_temp=False,
        workspace=str(workspace),
        workers=2,
        batch_size=1,
        env={
            "PLATFORM_POSTGRES_ENABLED": "true",
            "PLATFORM_POSTGRES_URL": sqlite_url,
            "PLATFORM_NONPROFIT_STORE_BACKEND": "postgres",
            "PLATFORM_NONPROFIT_QUERY_BACKEND": "postgres",
            "EO_BMF_DOWNLOAD_TIMEOUT_SECONDS": "300",
        },
    )

    stdout_lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    completion_payload = json.loads(stdout_lines[-1])

    assert exit_code == 0
    assert repository.get_nonprofit_snapshot_by_ein("123456789") is not None
    assert repository.get_nonprofit_snapshot_by_ein("987654321") is not None
    assert completion_payload["files_processed"] == 2
    assert {item["filename"] for item in completion_payload["files"]} == {"eo1.csv", "eo2.csv"}
    assert completion_payload["rows_seen"] == 2
