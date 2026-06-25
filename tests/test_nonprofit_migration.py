from __future__ import annotations

from pathlib import Path

from verification.backend.shared.customer_accounts import CustomerAccountsBase, build_customer_accounts_engine, build_customer_accounts_session_factory
from verification.backend.shared.nonprofits import SqlAlchemyNonprofitRepository
from verification.backend.shared.runtime import run_nonprofit_migration


class _FakeQueryClient:
    def __init__(self) -> None:
        self._eins = ["123456789"]

    def list_nonprofit_eins_page(self, limit: int, start_after_ein: str | None = None):
        if start_after_ein:
            return []
        return self._eins[:limit]

    def lookup_nonprofit(self, ein: str, subsection: str | None = None):
        return "qid-lookup", {
            "ein": ein,
            "name": "Example Nonprofit",
            "state": "IL",
            "status": "1",
            "deductibility": "1",
            "subsection": "03",
            "ntee_cd": "P20",
            "tax_period": "202412",
            "asset_amt": "120000",
            "income_amt": "80000",
            "revenue_amt": "76000",
        }

    def list_form990_filings(self, ein: str, limit: int = 10):
        return "qid-filings", [
            {
                "tax_year": "2024",
                "return_type": "990",
                "filing_date": "2025-05-15",
                "amended_return": "false",
                "parse_status": "parsed",
            }
        ]


class _FakeProfileStore:
    def get_profile(self, ein: str):
        return {
            "materialized_at": "2026-03-31T00:00:00+00:00",
            "model_version": "1.0.0",
            "source_hash": "hash_1",
            "environment": "test",
            "source_data_versions": {"irs_bmf": "2026.03"},
            "enrichment": {
                "providers": [
                    {
                        "name": "state_registry_mock",
                        "status": "matched",
                        "fields": {"registration_status": "active"},
                        "source": {
                            "source_name": "state_registry_mock",
                            "record_id": "sr-1",
                            "fetched_at": "2026-03-30T00:00:00+00:00",
                            "licensed": False,
                            "notes": "Public registry",
                        },
                    }
                ]
            },
            "state_compliance": {
                "registration_status": "active",
                "registration_jurisdiction": "IL",
                "registration_expiration_date": "2026-12-31",
                "solicitation_permitted": True,
                "compliance_flags": [],
            },
            "policy_evaluation": {"policy_id": "default", "final_recommendation": "approve", "matched_rules": []},
            "decision": {"status": "approve"},
            "summary": {"decision_status": "approve"},
            "evidence": {"factors": []},
            "external_signals": {"state_business_status": "good_standing", "state_business_good_standing": True},
            "audit": {"model_version": "1.0.0"},
        }


def _sqlite_url(tmp_path: Path, name: str) -> str:
    return f"sqlite+pysqlite:///{tmp_path / name}"


def test_nonprofit_migration_dry_run_reports_missing_targets(tmp_path: Path):
    report = run_nonprofit_migration(
        sqlalchemy_url=_sqlite_url(tmp_path, "dry_run.sqlite3"),
        query_client=_FakeQueryClient(),
        profile_store=_FakeProfileStore(),
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.processed_eins == 1
    assert report.source_counts.nonprofits == 1
    assert report.source_counts.filings == 1
    assert report.source_counts.sources == 1
    assert report.source_counts.compliance_checks == 1
    assert report.target_counts.nonprofits == 0
    assert report.validation["nonprofits"].missing == 1


def test_nonprofit_migration_backfills_and_validates_postgres_rows(tmp_path: Path):
    sqlite_url = _sqlite_url(tmp_path, "apply.sqlite3")
    report = run_nonprofit_migration(
        sqlalchemy_url=sqlite_url,
        query_client=_FakeQueryClient(),
        profile_store=_FakeProfileStore(),
    )

    engine = build_customer_accounts_engine(sqlite_url)
    CustomerAccountsBase.metadata.create_all(engine)
    repository = SqlAlchemyNonprofitRepository(build_customer_accounts_session_factory(engine))
    nonprofit = repository.get_nonprofit_by_ein("123456789")
    filings = repository.list_filings_by_ein("123456789")
    sources = repository.list_sources_by_ein("123456789")
    check = repository.latest_compliance_check_by_ein("123456789", check_type="materialized_profile_snapshot")

    assert report.dry_run is False
    assert report.source_counts == report.target_counts
    assert all(entity_validation.missing == 0 for entity_validation in report.validation.values())
    assert nonprofit is not None
    assert nonprofit.canonical_name == "Example Nonprofit"
    assert filings[0]["return_type"] == "990"
    assert sources[0].source_id == "state_registry_mock"
    assert check is not None
    assert check.final_recommendation == "approve"

