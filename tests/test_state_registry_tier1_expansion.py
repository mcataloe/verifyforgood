from __future__ import annotations

from pathlib import Path

from charity_status.state_registry import (
    StateRegistryAdapterRegistry,
    StateRegistryEntityStatus,
    StateRegistryLookupRequest,
    StateRegistryLookupService,
    StateRegistryStanding,
)
from charity_status.state_registry.adapters import (
    NevadaBusinessRegistryAdapter,
    NewYorkBusinessRegistryAdapter,
    OhioBusinessRegistryAdapter,
    SouthDakotaBusinessRegistryAdapter,
    UtahBusinessRegistryAdapter,
)
from charity_status.state_registry.adapters.nevada.client import NevadaRegistryClient
from charity_status.state_registry.adapters.nevada.mapper import map_nevada_record
from charity_status.state_registry.adapters.new_york.client import NewYorkRegistryClient
from charity_status.state_registry.adapters.new_york.mapper import map_new_york_record
from charity_status.state_registry.adapters.ohio.client import OhioRegistryClient
from charity_status.state_registry.adapters.ohio.mapper import map_ohio_record
from charity_status.state_registry.adapters.south_dakota.client import SouthDakotaRegistryClient
from charity_status.state_registry.adapters.south_dakota.mapper import map_south_dakota_record
from charity_status.state_registry.adapters.utah.client import UtahRegistryClient
from charity_status.state_registry.adapters.utah.mapper import map_utah_record


FIXTURE_DIR = Path("tests/fixtures/state_registry")


def _read_fixture(state_dir: str, name: str) -> str:
    return (FIXTURE_DIR / state_dir / name).read_text(encoding="utf-8")


def test_utah_adapter_search_maps_results_through_service():
    adapter = UtahBusinessRegistryAdapter(
        client=UtahRegistryClient(response_loader=lambda query: _read_fixture("utah", "search_results.html"))
    )
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"UT": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="American Red Cross Utah", state="UT"))

    assert len(results) == 2
    assert results[0].external_entity_id == "12345678-0140"
    assert results[0].registry_url == "https://businessregistration.utah.gov/EntitySearch/BusinessInformation?entityId=12345678-0140"


def test_utah_mapper_normalizes_status_and_traceability():
    adapter = UtahRegistryClient(response_loader=lambda query: _read_fixture("utah", "search_results.html"))
    row = adapter.search(normalized_name="AMERICAN RED CROSS")[1]

    record = map_utah_record(row, request=StateRegistryLookupRequest(organization_name="American Red Cross Utah County Chapter", state="UT"))

    assert record is not None
    assert record.status == StateRegistryEntityStatus.INACTIVE
    assert record.standing == StateRegistryStanding.NOT_IN_GOOD_STANDING
    assert record.formation_date == "2004-05-12"
    assert record.parser_version == "utah_business_registry.v1"


def test_utah_malformed_rows_are_ignored():
    rows = UtahRegistryClient(response_loader=lambda query: _read_fixture("utah", "malformed_results.html")).search(normalized_name="BAD")

    assert [map_utah_record(row) for row in rows] == [None]


def test_nevada_adapter_search_maps_results_through_service():
    adapter = NevadaBusinessRegistryAdapter(
        client=NevadaRegistryClient(response_loader=lambda query: _read_fixture("nevada", "search_results.html"))
    )
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"NV": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="American Red Cross Nevada", state="NV"))

    assert len(results) == 2
    assert results[0].status == StateRegistryEntityStatus.ACTIVE
    assert results[1].external_entity_id == "NV20002020202"


def test_nevada_mapper_normalizes_revoked_status():
    row = NevadaRegistryClient(response_loader=lambda query: _read_fixture("nevada", "search_results.html")).search(normalized_name="RED CROSS")[1]

    record = map_nevada_record(row, request=StateRegistryLookupRequest(organization_name="American Red Cross Las Vegas Chapter", state="NV"))

    assert record is not None
    assert record.status == StateRegistryEntityStatus.REVOKED
    assert record.standing == StateRegistryStanding.NOT_IN_GOOD_STANDING


def test_nevada_malformed_rows_are_ignored():
    rows = NevadaRegistryClient(response_loader=lambda query: _read_fixture("nevada", "malformed_results.html")).search(normalized_name="BAD")

    assert [map_nevada_record(row) for row in rows] == [None]


def test_ohio_adapter_search_maps_results_through_service():
    adapter = OhioBusinessRegistryAdapter(
        client=OhioRegistryClient(response_loader=lambda query: _read_fixture("ohio", "search_results.html"))
    )
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"OH": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="American Red Cross Of Ohio", state="OH"))

    assert len(results) == 2
    assert results[0].external_entity_id == "7654321"
    assert results[0].status == StateRegistryEntityStatus.ACTIVE


def test_ohio_mapper_normalizes_cancelled_status():
    row = OhioRegistryClient(response_loader=lambda query: _read_fixture("ohio", "search_results.html")).search(normalized_name="RED CROSS")[1]

    record = map_ohio_record(row, request=StateRegistryLookupRequest(organization_name="American Red Cross Columbus Chapter", state="OH"))

    assert record is not None
    assert record.status == StateRegistryEntityStatus.INACTIVE
    assert record.standing == StateRegistryStanding.NOT_IN_GOOD_STANDING


def test_ohio_malformed_rows_are_ignored():
    rows = OhioRegistryClient(response_loader=lambda query: _read_fixture("ohio", "malformed_results.html")).search(normalized_name="BAD")

    assert [map_ohio_record(row) for row in rows] == [None]


def test_south_dakota_adapter_search_maps_results_through_service():
    adapter = SouthDakotaBusinessRegistryAdapter(
        client=SouthDakotaRegistryClient(response_loader=lambda query: _read_fixture("south_dakota", "search_results.html"))
    )
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"SD": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="American Red Cross South Dakota", state="SD"))

    assert len(results) == 2
    assert results[0].external_entity_id == "NS010101"
    assert results[0].registry_url == "https://sosenterprise.sd.gov/BusinessServices/Business/FilingDetail.aspx?fid=NS010101"


def test_south_dakota_mapper_normalizes_revoked_status():
    row = SouthDakotaRegistryClient(response_loader=lambda query: _read_fixture("south_dakota", "search_results.html")).search(normalized_name="RED CROSS")[1]

    record = map_south_dakota_record(row, request=StateRegistryLookupRequest(organization_name="American Red Cross Rapid City Chapter", state="SD"))

    assert record is not None
    assert record.status == StateRegistryEntityStatus.REVOKED
    assert record.standing == StateRegistryStanding.NOT_IN_GOOD_STANDING


def test_south_dakota_malformed_rows_are_ignored():
    rows = SouthDakotaRegistryClient(response_loader=lambda query: _read_fixture("south_dakota", "malformed_results.html")).search(normalized_name="BAD")

    assert [map_south_dakota_record(row) for row in rows] == [None]


def test_new_york_adapter_search_maps_results_through_service():
    adapter = NewYorkBusinessRegistryAdapter(
        client=NewYorkRegistryClient(response_loader=lambda query: _read_fixture("new_york", "search_results.html"))
    )
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"NY": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="American Red Cross Of New York", state="NY"))

    assert len(results) == 2
    assert results[0].external_entity_id == "5012345"
    assert results[0].status == StateRegistryEntityStatus.ACTIVE


def test_new_york_mapper_normalizes_inactive_dissolution_status():
    row = NewYorkRegistryClient(response_loader=lambda query: _read_fixture("new_york", "search_results.html")).search(normalized_name="RED CROSS")[1]

    record = map_new_york_record(row, request=StateRegistryLookupRequest(organization_name="American Red Cross Albany Chapter", state="NY"))

    assert record is not None
    assert record.status == StateRegistryEntityStatus.DISSOLVED
    assert record.standing == StateRegistryStanding.NOT_IN_GOOD_STANDING


def test_new_york_malformed_rows_are_ignored():
    rows = NewYorkRegistryClient(response_loader=lambda query: _read_fixture("new_york", "malformed_results.html")).search(normalized_name="BAD")

    assert [map_new_york_record(row) for row in rows] == [None]
