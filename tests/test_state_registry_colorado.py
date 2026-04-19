from __future__ import annotations

import json
from pathlib import Path

from verification.state_registry import (
    StateRegistryAdapterRegistry,
    StateRegistryEntityStatus,
    StateRegistryLookupRequest,
    StateRegistryLookupService,
    StateRegistryStanding,
)
from verification.state_registry.adapters import ColoradoBusinessRegistryAdapter
from verification.state_registry.adapters.colorado.client import ColoradoRegistryClient
from verification.state_registry.adapters.colorado.mapper import map_colorado_record


FIXTURE_DIR = Path("tests/fixtures/state_registry/colorado")


def _load_fixture(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class _FakeColoradoClient:
    def __init__(self, search_rows=None, entity_rows=None):
        self._search_rows = list(search_rows or [])
        self._entity_rows = dict(entity_rows or {})

    def search(self, *, normalized_name: str, limit: int = 10):
        del normalized_name, limit
        return list(self._search_rows)

    def fetch_by_entity_id(self, entity_id: str):
        return self._entity_rows.get(entity_id)


def test_colorado_adapter_search_maps_results_through_service():
    rows = _load_fixture("search_results.json")
    adapter = ColoradoBusinessRegistryAdapter(client=_FakeColoradoClient(search_rows=rows))
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"CO": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="American Red Cross", state="CO"))

    assert len(results) == 2
    assert results[0].state_code == "CO"
    assert results[0].source_name == "colorado_secretary_of_state"
    assert results[0].registry_url == "https://www.sos.state.co.us/biz/BusinessEntityDetail.do?masterFileId=20251665680"
    assert results[1].entity_name == "AMERICAN RED CROSS - WELD COUNTY CHAPTER"


def test_colorado_adapter_no_results_returns_empty_list():
    adapter = ColoradoBusinessRegistryAdapter(client=_FakeColoradoClient(search_rows=[]))
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"CO": adapter}))

    results = service.search(StateRegistryLookupRequest(organization_name="No Match Org", state="CO"))

    assert results == []


def test_colorado_mapper_normalizes_status_and_standing():
    row = _load_fixture("search_results.json")[1]

    parsed = map_colorado_record(
        row,
        request=StateRegistryLookupRequest(organization_name="American Red Cross - Weld County Chapter", state="CO"),
    )

    assert parsed is not None
    assert parsed.status == StateRegistryEntityStatus.DISSOLVED
    assert parsed.standing == StateRegistryStanding.NOT_IN_GOOD_STANDING
    assert parsed.entity_type == "Domestic Nonprofit Corporation"
    assert parsed.formation_date == "1991-12-18"
    assert parsed.raw_payload_ref is not None
    assert parsed.parser_version == "colorado_business_entities.v1"


def test_colorado_mapper_ignores_malformed_rows():
    malformed_rows = _load_fixture("malformed_results.json")

    parsed = [map_colorado_record(row) for row in malformed_rows]

    assert parsed == [None, None]


def test_colorado_fetch_by_external_entity_id_returns_normalized_record():
    row = _load_fixture("search_results.json")[0]
    adapter = ColoradoBusinessRegistryAdapter(client=_FakeColoradoClient(entity_rows={row["entityid"]: row}))
    service = StateRegistryLookupService(StateRegistryAdapterRegistry({"CO": adapter}))

    record = service.fetch_by_external_entity_id(
        state_code="CO",
        external_entity_id=row["entityid"],
        request=StateRegistryLookupRequest(organization_name="Kylderon Mist Valley LLC", state="CO"),
    )

    assert record is not None
    assert record.external_entity_id == row["entityid"]
    assert record.status == StateRegistryEntityStatus.ACTIVE
    assert record.standing == StateRegistryStanding.GOOD_STANDING


def test_colorado_client_rejects_non_list_payload(monkeypatch):
    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"unexpected":"object"}'

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=10: _Response())
    client = ColoradoRegistryClient()

    try:
        client.search(normalized_name="AMERICAN RED CROSS")
        assert False, "expected error"
    except Exception as exc:
        assert "response must be a list" in str(exc)

