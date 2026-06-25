from verification.backend.ingest.state import (
    MatchConfidence,
    StateRegistryAdapterRegistry,
    StateRegistryEntityStatus,
    StateRegistryLookupRequest,
    StateRegistryRecord,
    StateRegistrySourceType,
    StateRegistryStanding,
    UnsupportedStateRegistryError,
    build_raw_payload_ref,
    build_state_registry_adapter_registry,
    normalize_entity_status,
    normalize_standing,
)
from verification.backend.ingest.state.adapters import IllinoisBusinessRegistryAdapter


def test_state_registry_record_to_dict_and_traceability():
    raw_payload_ref = build_raw_payload_ref(
        payload={"file_number": "12345", "entity_name": "Example Charity"},
        source_identifier="illinois_secretary_of_state:12345",
        parser_version="illinois_business_registry.v1",
        retrieved_at="2026-03-16T00:00:00+00:00",
    )
    record = StateRegistryRecord(
        state_code="il",
        source_name="illinois_secretary_of_state",
        source_type=StateRegistrySourceType.SEARCH_PORTAL,
        external_entity_id="12345",
        entity_name="Example Charity",
        status=StateRegistryEntityStatus.ACTIVE,
        standing=StateRegistryStanding.GOOD_STANDING,
        matched_on="normalized_entity_name",
        confidence=MatchConfidence.HIGH,
        raw_payload_ref=raw_payload_ref,
    )

    payload = record.to_dict()

    assert payload["state_code"] == "IL"
    assert payload["status"] == "active"
    assert payload["standing"] == "good_standing"
    assert payload["confidence"] == "high"
    assert payload["raw_payload_ref"]["raw_hash"] == raw_payload_ref.raw_hash
    assert payload["parser_version"] == "illinois_business_registry.v1"


def test_state_registry_record_rejects_invalid_state_code():
    try:
        StateRegistryRecord(
            state_code="ILL",
            source_name="illinois_secretary_of_state",
            source_type=StateRegistrySourceType.SEARCH_PORTAL,
        )
        assert False, "expected validation error"
    except ValueError as exc:
        assert "two-letter state code" in str(exc)


def test_lookup_request_normalizes_name_and_state():
    request = StateRegistryLookupRequest(
        organization_name="Example Charity, Inc.",
        state="il",
    )

    assert request.state == "IL"
    assert request.normalized_organization_name == "EXAMPLE CHARITY INC"


def test_status_and_standing_normalization_helpers():
    assert normalize_entity_status("administratively dissolved") == StateRegistryEntityStatus.DISSOLVED
    assert normalize_entity_status("good standing") == StateRegistryEntityStatus.ACTIVE
    assert normalize_standing("good standing") == StateRegistryStanding.GOOD_STANDING
    assert normalize_standing("delinquent") == StateRegistryStanding.NOT_IN_GOOD_STANDING


def test_adapter_registry_registers_and_resolves_state_adapter():
    adapter = IllinoisBusinessRegistryAdapter()
    registry = build_state_registry_adapter_registry([adapter])

    resolved = registry.resolve("IL")

    assert resolved is adapter
    assert registry.supported_states() == ["IL"]


def test_adapter_registry_unsupported_state_fails_cleanly():
    registry = StateRegistryAdapterRegistry()
    try:
        registry.resolve("CA")
        assert False, "expected unsupported-state error"
    except UnsupportedStateRegistryError as exc:
        assert "CA" in str(exc)


def test_illinois_adapter_parses_raw_record_into_canonical_model():
    adapter = IllinoisBusinessRegistryAdapter()
    request = StateRegistryLookupRequest(organization_name="Example Charity", state="IL")
    record = adapter.parse_record(
        {
            "file_number": "12345",
            "entity_name": "Example Charity",
            "entity_type": "Domestic Not For Profit Corporation",
            "status": "Active",
            "standing": "Good Standing",
            "formation_date": "2001-01-01",
            "registry_url": "https://example.il.gov/entity/12345",
            "raw_fetched_at": "2026-03-16T00:00:00+00:00",
        },
        request=request,
    )

    assert record is not None
    payload = record.to_dict()
    assert payload["external_entity_id"] == "12345"
    assert payload["status"] == "active"
    assert payload["standing"] == "good_standing"
    assert payload["matched_on"] == "normalized_entity_name"
    assert payload["confidence"] == "high"

