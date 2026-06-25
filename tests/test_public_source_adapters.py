from __future__ import annotations

from types import SimpleNamespace

from verification.backend.shared.enrichments import EnrichmentService, ProviderRegistry
from verification.backend.shared.enrichments.external_signals import extract_external_signals
from verification.backend.shared.enrichments.providers import OFACMockProvider, StateBusinessMockProvider, StateRegistryMockProvider, USAspendingMockProvider
from verification.backend.shared.policy import evaluate_policy
from verification.backend.shared.query.verification import VerificationInput, verify_nonprofit


def _client(name: str = "US Org"):
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


def test_public_source_family_success_paths():
    service = EnrichmentService(
        ProviderRegistry(
            [
                StateRegistryMockProvider(enabled=True),
                StateBusinessMockProvider(enabled=True),
                USAspendingMockProvider(enabled=True),
                OFACMockProvider(enabled=True),
            ]
        )
    )
    result = service.enrich("123456789", "US Org").to_dict()
    providers = {item["name"]: item for item in result["providers"]}
    assert providers["state_registry_mock"]["status"] == "matched"
    assert providers["state_business_mock"]["status"] == "matched"
    assert providers["usaspending_mock"]["status"] == "matched"
    assert providers["ofac_mock"]["status"] == "matched"
    assert result["source_catalog"]["us_only"] is True


def test_public_source_provider_unavailable_path():
    service = EnrichmentService(ProviderRegistry([StateBusinessMockProvider(enabled=False)]))
    result = service.enrich("123456789", "US Org").to_dict()
    assert result["providers"][0]["status"] == "disabled"


def test_public_source_provider_error_path():
    service = EnrichmentService(ProviderRegistry([USAspendingMockProvider(enabled=True)]))
    result = service.enrich("999999999", "US Org").to_dict()
    assert result["providers"][0]["status"] == "failed"
    assert result["failures"][0]["provider"] == "usaspending_mock"


def test_public_source_evidence_and_policy_integration():
    service = EnrichmentService(
        ProviderRegistry(
            [
                StateRegistryMockProvider(enabled=True),
                StateBusinessMockProvider(enabled=True),
                USAspendingMockProvider(enabled=True),
                OFACMockProvider(enabled=True),
            ]
        )
    )
    status, payload = verify_nonprofit(_client("Watchlist Org"), VerificationInput(ein="123456789"), enrichment_service=service)
    assert status == 200
    payload["external_signals"] = extract_external_signals(payload.get("enrichment"))
    sanctions_factor = [f for f in payload["evidence"]["factors"] if f["key"] == "sanctions_match"][0]
    assert sanctions_factor["value"] is True
    policy_eval = evaluate_policy(payload, "strict_deny")
    assert policy_eval["final_recommendation"] == "deny"

