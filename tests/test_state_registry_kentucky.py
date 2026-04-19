from __future__ import annotations

from pathlib import Path

from verification.state_registry import (
    StateRegistryAdapterRegistry,
    StateRegistryEntityStatus,
    StateRegistryLookupRequest,
    StateRegistryLookupService,
    StateRegistryStanding,
)
from verification.state_registry.adapters import KentuckyBusinessRegistryAdapter
from verification.state_registry.adapters.kentucky.mapper import map_kentucky_company_record
from verification.state_registry.adapters.kentucky.parser import kentucky_external_entity_id, parse_kentucky_companies_tsv


FIXTURE_DIR = Path("tests/fixtures/state_registry/kentucky")


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_kentucky_bulk_parser_reads_tab_delimited_companies():
    rows = parse_kentucky_companies_tsv(_read_fixture("all_companies.tsv"))

    assert len(rows) == 4
    assert rows[0]["ID"] == "1234567"
    assert rows[0]["Name"] == "KENTUCKY HEALTHY KIDS FOUNDATION"


def test_kentucky_adapter_search_returns_ambiguous_candidates():
    adapter = KentuckyBusinessRegistryAdapter(companies_snapshot_text=_read_fixture("all_companies.tsv"))
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"KY": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="Kentucky Healthy Kids Foundation", state="KY"))

    assert len(results) == 2
    assert [item.external_entity_id for item in results] == ["1234567:09:99999", "1234567:09:99998"]
    assert results[0].status == StateRegistryEntityStatus.ACTIVE
    assert results[1].status == StateRegistryEntityStatus.INACTIVE


def test_kentucky_adapter_no_results_returns_empty_list():
    adapter = KentuckyBusinessRegistryAdapter(companies_snapshot_text=_read_fixture("all_companies.tsv"))
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"KY": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="No Such Kentucky Entity", state="KY"))

    assert results == []


def test_kentucky_mapper_normalizes_status_standing_and_dates():
    rows = parse_kentucky_companies_tsv(_read_fixture("all_companies.tsv"))

    record = map_kentucky_company_record(
        rows[3],
        request=StateRegistryLookupRequest(organization_name="Ohio River Relief Fund", state="KY"),
    )

    assert record is not None
    assert record.status == StateRegistryEntityStatus.REVOKED
    assert record.standing is None
    assert record.entity_type == "Foreign Corporation"
    assert record.formation_date == "2015-06-30"
    assert record.last_filing_date == "2015-07-01"
    assert record.parser_version == "kentucky_bulk_companies.v1"
    assert record.raw_payload_ref is not None


def test_kentucky_fetch_by_external_entity_id_uses_composite_key():
    rows = parse_kentucky_companies_tsv(_read_fixture("all_companies.tsv"))
    target = rows[2]
    adapter = KentuckyBusinessRegistryAdapter(companies_snapshot_text=_read_fixture("all_companies.tsv"))
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"KY": adapter}))

    record = service.fetch_by_external_entity_id(
        state_code="KY",
        external_entity_id=kentucky_external_entity_id(target) or "",
        request=StateRegistryLookupRequest(organization_name="Bluegrass Community Services", state="KY"),
    )

    assert record is not None
    assert record.external_entity_id == "7654321:06:99999"
    assert record.standing == StateRegistryStanding.GOOD_STANDING
    assert record.status == StateRegistryEntityStatus.ACTIVE


def test_kentucky_parser_version_and_raw_payload_metadata_are_stable():
    row = parse_kentucky_companies_tsv(_read_fixture("all_companies.tsv"))[0]

    record = map_kentucky_company_record(row)

    assert record is not None
    assert record.raw_hash
    assert record.raw_fetched_at == "2026-03-16T00:00:00+00:00"
    assert record.raw_payload_ref is not None
    assert record.raw_payload_ref.parser_version == "kentucky_bulk_companies.v1"


def test_kentucky_malformed_rows_are_ignored():
    rows = parse_kentucky_companies_tsv(_read_fixture("malformed_companies.tsv"))
    parsed = [map_kentucky_company_record(row) for row in rows]

    assert parsed == [None, None]

