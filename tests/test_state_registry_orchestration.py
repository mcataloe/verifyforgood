from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from verification.backend.shared.enrichments.registry import ProviderRegistry
from verification.backend.shared.enrichments.service import EnrichmentService
from verification.backend.shared.enrichments.providers.state_registry import StateRegistryProvider
from verification.backend.shared.query.verification import VerificationInput, verify_nonprofit
from verification.backend.ingest.state import (
    InMemoryStateRegistryRecordRepository,
    RawStateRegistryRecord,
    StateRegistryAdapter,
    StateRegistryEntityStatus,
    StateRegistryLookupRequest,
    StateRegistryLookupService,
    StateRegistryRecord,
    StateRegistrySourceType,
    build_state_registry_adapter_registry,
)
from verification.backend.ingest.state.adapters import IllinoisBusinessRegistryAdapter


def _client(state: str = "IL", name: str = "Example Charity"):
    record = {
        "name": name,
        "state": state,
        "status": "1",
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "filing_req_cd": "1",
    }
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", record),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
    )


def test_lookup_service_persists_normalized_records():
    repository = InMemoryStateRegistryRecordRepository()
    service = StateRegistryLookupService(
        adapter_registry=build_state_registry_adapter_registry(
            [
                IllinoisBusinessRegistryAdapter(
                    records=[
                        {
                            "file_number": "12345",
                            "entity_name": "Example Charity",
                            "status": "Active",
                            "standing": "Good Standing",
                            "raw_fetched_at": "2026-03-16T00:00:00+00:00",
                        }
                    ]
                )
            ]
        ),
        repository=repository,
    )

    outcome = service.lookup(StateRegistryLookupRequest(organization_name="Example Charity", state="IL"))

    assert len(outcome.records) == 1
    assert outcome.persisted_count == 1
    items = repository.items()
    assert items[0]["pk"] == "STATE#IL"
    assert items[0]["record"]["external_entity_id"] == "12345"
    assert items[0]["raw_payload_ref"]["parser_version"] == "illinois_business_registry.v1"


def test_lookup_service_returns_structured_failure_for_unsupported_state():
    service = StateRegistryLookupService(adapter_registry=build_state_registry_adapter_registry([]))

    outcome = service.lookup(StateRegistryLookupRequest(organization_name="Missing Adapter Org", state="CA"))

    assert outcome.records == []
    assert outcome.failures[0].error_code == "unsupported_state"
    assert "CA" in outcome.failures[0].message


@dataclass
class _MixedAdapter(StateRegistryAdapter):
    @property
    def state_code(self) -> str:
        return "IL"

    @property
    def source_name(self) -> str:
        return "mixed_test_registry"

    @property
    def source_type(self) -> StateRegistrySourceType:
        return StateRegistrySourceType.API

    def search(self, request: StateRegistryLookupRequest) -> list[RawStateRegistryRecord]:
        del request
        return [{"entity_name": "Broken Record"}, {"entity_name": "Healthy Record"}]

    def parse_record(
        self,
        raw_record: RawStateRegistryRecord,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        del request
        if raw_record.get("entity_name") == "Broken Record":
            raise ValueError("unexpected row format")
        return StateRegistryRecord(
            state_code="IL",
            source_name=self.source_name,
            source_type=self.source_type,
            entity_name="Healthy Record",
            external_entity_id="ok-1",
            status=StateRegistryEntityStatus.ACTIVE,
        )


def test_lookup_service_isolates_parse_failures_and_keeps_valid_records():
    service = StateRegistryLookupService(
        adapter_registry=build_state_registry_adapter_registry([_MixedAdapter()])
    )

    outcome = service.lookup(StateRegistryLookupRequest(organization_name="Healthy Record", state="IL"))

    assert len(outcome.records) == 1
    assert outcome.records[0].external_entity_id == "ok-1"
    assert outcome.failures[0].error_code == "record_parse_failed"


def test_state_registry_provider_failure_does_not_break_verification_flow():
    lookup_service = StateRegistryLookupService(
        adapter_registry=build_state_registry_adapter_registry([])
    )
    enrichment_service = EnrichmentService(
        ProviderRegistry([StateRegistryProvider(enabled=True, lookup_service=lookup_service)])
    )

    status, payload = verify_nonprofit(
        _client(state="CA", name="Unsupported State Org"),
        VerificationInput(ein="123456789"),
        enrichment_service=enrichment_service,
    )

    assert status == 200
    assert payload["enrichment"]["providers"][0]["status"] == "failed"
    assert payload["enrichment"]["failures"][0]["provider"] == "state_registry"
    assert payload["state_compliance"]["registration_status"] is None


def test_state_registry_provider_uses_lookup_service_for_supported_state():
    lookup_service = StateRegistryLookupService(
        adapter_registry=build_state_registry_adapter_registry(
            [
                IllinoisBusinessRegistryAdapter(
                    records=[
                        {
                            "file_number": "12345",
                            "entity_name": "Example Charity",
                            "status": "Active",
                            "standing": "Good Standing",
                            "raw_fetched_at": "2026-03-16T00:00:00+00:00",
                        }
                    ]
                )
            ]
        )
    )
    enrichment_service = EnrichmentService(
        ProviderRegistry([StateRegistryProvider(enabled=True, lookup_service=lookup_service)])
    )

    status, payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=enrichment_service,
    )

    assert status == 200
    assert payload["state_compliance"]["registration_status"] == "active"
    assert payload["state_compliance"]["registration_jurisdiction"] == "IL"
    assert payload["enrichment"]["providers"][0]["source"]["source_name"] == "illinois_secretary_of_state"

