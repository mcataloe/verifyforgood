from __future__ import annotations

from types import SimpleNamespace

from charity_status.enrichments import EnrichmentService, ProviderRegistry
from charity_status.enrichments.providers import MockProvider
from charity_status.query.verification import VerificationInput, verify_nonprofit


def _record() -> dict[str, str]:
    return {
        "name": "Evidence Org",
        "state": "IL",
        "status": "1",
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "filing_req_cd": "1",
        "asset_amt": "",
        "income_amt": "",
        "revenue_amt": "",
    }


def _client(
    filings=None,
    metrics=None,
    governance=None,
    quality=None,
    peer_stats=None,
):
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", _record()),
        lookup_form990_enrichment=lambda ein: (filings, metrics, governance, quality),
        lookup_peer_benchmark=lambda group: peer_stats or {"count": 0, "metrics": {}},
    )


def test_evidence_eo_bmf_only_fallback_case():
    status, payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []})),
    )

    assert status == 200
    assert payload["evidence"]["model_version"] == payload["score_explanation"]["model_version"]
    sources = {s["source"]: s for s in payload["evidence"]["sources"]}
    assert sources["irs.eo_bmf"]["used"] is True
    assert sources["irs_form_990_xml"]["used"] is False


def test_evidence_eo_plus_990_case():
    filings = {
        "tax_year": "2024",
        "return_type": "990",
        "filing_date": "2025-01-10",
        "amended_return": False,
        "parse_status": "parsed",
        "mission_description_present": True,
        "program_accomplishments_present": True,
        "leadership_disclosed": True,
        "total_revenue": "2500000",
    }
    metrics = {
        "programExpenseRatio": 0.8,
        "liabilitiesToAssetsRatio": 0.45,
        "operatingMargin": 0.04,
        "monthsOfRunway": 9,
    }
    governance = {"public_disclosure_available": True, "material_diversion_reported": False, "whistleblower_policy": True}
    quality = {"narrativeMissing": False, "scoreConfidence": "high"}
    peer_stats = {
        "count": 100,
        "metrics": {
            "programExpenseRatio": {"p25": 0.6, "median": 0.7, "p75": 0.78},
            "liabilitiesToAssetsRatio": {"p25": 0.35, "median": 0.5, "p75": 0.65},
            "operatingMargin": {"p25": 0.0, "median": 0.03, "p75": 0.08},
            "monthsOfRunway": {"p25": 4, "median": 6, "p75": 10},
        },
    }

    status, payload = verify_nonprofit(
        _client(filings=filings, metrics=metrics, governance=governance, quality=quality, peer_stats=peer_stats),
        VerificationInput(ein="123456789"),
        enrichment_service=SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []})),
    )
    assert status == 200
    peer_factor = [f for f in payload["evidence"]["factors"] if f["key"] == "peer_benchmarking_used"][0]
    assert peer_factor["value"] is True
    sources = {s["source"]: s for s in payload["evidence"]["sources"]}
    assert sources["irs_form_990_xml"]["used"] is True


def test_evidence_enrichment_failure_case():
    status, payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=SimpleNamespace(
            enrich=lambda ein, organization_name=None: SimpleNamespace(
                to_dict=lambda: {"providers": [], "failures": [{"provider": "candid", "error": "timeout"}]}
            )
        ),
    )
    assert status == 200
    failure_factor = [f for f in payload["evidence"]["factors"] if f["key"] == "enrichment_failures"][0]
    assert failure_factor["value"] == 1
    health_rule = [r for r in payload["evidence"]["rule_results"] if r["rule"] == "enrichment_provider_health"][0]
    assert health_rule["passed"] is False


def test_evidence_flow_with_source_catalog_enrichment_payload():
    service = EnrichmentService(ProviderRegistry([MockProvider(enabled=True)]))
    status, payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=service,
    )
    assert status == 200
    assert "source_catalog" in payload["enrichment"]
    assert payload["evidence"]["model_version"] == payload["score_explanation"]["model_version"]


def test_evidence_explains_optional_integration_without_penalty():
    baseline_status, baseline_payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=SimpleNamespace(
            enrich=lambda ein, organization_name=None, evaluation_context=None: SimpleNamespace(
                to_dict=lambda: {"providers": [], "failures": []}
            )
        ),
    )
    status, payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=SimpleNamespace(
            enrich=lambda ein, organization_name=None, evaluation_context=None: SimpleNamespace(
                to_dict=lambda: {
                    "providers": [],
                    "failures": [],
                    "integration_evaluation": {
                        "integrations": [
                            {
                                "integration_id": "candid",
                                "offered": True,
                                "credentials_present": True,
                                "tenant_enabled": True,
                                "required_for_eligibility": False,
                                "attempted": True,
                                "availability_status": "no_match",
                                "requirement_status": "not_required",
                                "driver": "live",
                            }
                        ],
                        "attempted_integrations": ["candid"],
                        "used_integrations": [],
                        "required_unmet_integrations": [],
                        "failure_integrations": [],
                    },
                }
            )
        ),
    )

    assert baseline_status == 200
    assert status == 200
    assert payload["decision"]["status"] == baseline_payload["decision"]["status"]
    assert payload["score_explanation"]["integration_policy"]["status"] == "neutral"
    assert payload["integration_evaluation"]["explanations"][0]["code"] == "integration_optional_and_skipped"
    factor = next(item for item in payload["evidence"]["factors"] if item["key"] == "integration_policy:candid")
    assert factor["polarity"] == "neutral"


def test_evidence_explains_required_integration_unavailable():
    status, payload = verify_nonprofit(
        _client(),
        VerificationInput(ein="123456789"),
        enrichment_service=SimpleNamespace(
            enrich=lambda ein, organization_name=None, evaluation_context=None: SimpleNamespace(
                to_dict=lambda: {
                    "providers": [],
                    "failures": [],
                    "integration_evaluation": {
                        "integrations": [
                            {
                                "integration_id": "candid",
                                "offered": True,
                                "credentials_present": False,
                                "tenant_enabled": True,
                                "required_for_eligibility": True,
                                "attempted": False,
                                "availability_status": "missing_credentials",
                                "requirement_status": "unmet",
                                "driver": "live",
                            }
                        ],
                        "attempted_integrations": [],
                        "used_integrations": [],
                        "required_unmet_integrations": ["candid"],
                        "failure_integrations": [],
                    },
                }
            )
        ),
    )

    assert status == 200
    assert payload["decision"]["status"] == "manual_review"
    assert payload["score_explanation"]["integration_policy"]["status"] == "required_unavailable"
    assert payload["integration_evaluation"]["explanations"][0]["code"] == "integration_required_but_unavailable"
    factor = next(item for item in payload["evidence"]["factors"] if item["key"] == "integration_policy:candid")
    assert factor["polarity"] == "warning"
