from __future__ import annotations

from types import SimpleNamespace

from charity_status.enrichments.compliance import extract_state_compliance
from charity_status.enrichments.providers.state_registry_mock import StateRegistryMockProvider
from charity_status.enrichments.registry import ProviderRegistry
from charity_status.enrichments.service import EnrichmentService
from charity_status.policy import evaluate_policy
from charity_status.query.verification import VerificationInput, verify_nonprofit


def _client(name: str = "Evidence Org"):
    record = {
        "name": name,
        "state": "IL",
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


def test_state_compliance_success():
    service = EnrichmentService(ProviderRegistry([StateRegistryMockProvider(enabled=True)]))
    data = service.enrich("123456789", "Good Org").to_dict()
    compliance = extract_state_compliance(data)
    assert compliance["registration_status"] == "active"
    assert compliance["registration_jurisdiction"] == "IL"
    assert compliance["solicitation_permitted"] is True


def test_state_compliance_unavailable():
    service = EnrichmentService(ProviderRegistry([StateRegistryMockProvider(enabled=True)]))
    data = service.enrich("888888888", "No Match Org").to_dict()
    compliance = extract_state_compliance(data)
    assert compliance["registration_status"] is None
    assert compliance["compliance_flags"] == []


def test_state_compliance_provider_failure_is_tolerated():
    service = EnrichmentService(ProviderRegistry([StateRegistryMockProvider(enabled=True)]))
    data = service.enrich("999999999", "Fail Org").to_dict()
    compliance = extract_state_compliance(data)
    assert any(f["provider"] == "state_registry_mock" for f in data["failures"])
    assert compliance["registration_status"] is None


def test_adverse_compliance_flag_affects_evidence_and_policy():
    service = EnrichmentService(ProviderRegistry([StateRegistryMockProvider(enabled=True)]))
    status, payload = verify_nonprofit(
        _client("Risk Org"),
        VerificationInput(ein="123456789"),
        enrichment_service=service,
    )
    assert status == 200

    evidence_factor = [f for f in payload["evidence"]["factors"] if f["key"] == "state_compliance_flags_count"][0]
    assert evidence_factor["value"] == 1

    policy_eval = evaluate_policy(payload, "strict_manual")
    assert policy_eval["final_recommendation"] == "manual_review"
