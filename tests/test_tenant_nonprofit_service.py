from __future__ import annotations

from types import SimpleNamespace

import pytest

from verification.backend.shared.enrichments import EvaluationContext, OrganizationIntegrationSetting
from verification.backend.shared.organization_verification.nonprofit_service import NonprofitService, TenantNonprofitContext
from verification.backend.shared.organization_verification.verification_service import OrganizationVerificationInput as VerificationInput


def _tenant_context() -> TenantNonprofitContext:
    return TenantNonprofitContext(
        organization_id="org_1",
        authenticated_subject="api_key:key_1",
        authenticated_user_id=None,
        auth_method="api_key",
        credential_id="key_1",
        metadata={"organization_id": "org_1", "tenant_scoped_request": "true"},
    )


def _client():
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: (
            "qid-1",
            {
                "ein": ein,
                "name": "Tenant Org",
                "state": "IL",
                "status": "1",
                "deductibility": "1",
                "subsection": subsection or "03",
                "ntee_cd": "P20",
                "tax_period": "202501",
                "filing_req_cd": "1",
                "asset_amt": "",
                "income_amt": "",
                "revenue_amt": "",
            },
        ),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: (
            "qid-f",
            [{"tax_year": "2024", "return_type": "990", "filing_date": "2025-01-01", "amended_return": "false", "parse_status": "parsed"}],
        ),
        search_nonprofits=lambda **kwargs: (
            "qid-s",
            [{"ein": "123456789", "name": "Tenant Org", "state": "IL", "subsection": "03", "status": "1", "tax_period": "202501"}],
        ),
    )


def _enrichment():
    return SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []})


def test_nonprofit_service_requires_tenant_context():
    service = NonprofitService(client=_client(), enrichment_service=SimpleNamespace(enrich=lambda **kwargs: _enrichment()))

    with pytest.raises(ValueError, match="organization_id is required"):
        service.lookup_nonprofit(
            tenant_context=TenantNonprofitContext("", "subject", None, "api_key", "key_1"),
            verification_input=VerificationInput(ein="123456789"),
        )


def test_nonprofit_service_delegates_lookup_search_filings_and_sources():
    service = NonprofitService(client=_client(), enrichment_service=SimpleNamespace(enrich=lambda **kwargs: _enrichment()))
    tenant_context = _tenant_context()

    lookup_status, lookup_payload = service.lookup_nonprofit(
        tenant_context=tenant_context,
        verification_input=VerificationInput(ein="123456789"),
    )
    search_status, search_payload = service.search_nonprofits(
        tenant_context=tenant_context,
        name_query="tenant",
        limit=5,
    )
    filings_status, filings_payload = service.get_filings(
        tenant_context=tenant_context,
        ein="123456789",
    )
    sources_status, sources_payload = service.get_sources(
        tenant_context=tenant_context,
        ein="123456789",
    )

    assert lookup_status == 200
    assert lookup_payload["organization"]["name"] == "Tenant Org"
    assert search_status == 200
    assert search_payload["items"][0]["name"] == "Tenant Org"
    assert filings_status == 200
    assert filings_payload["filings"][0]["form_type"] == "990"
    assert sources_status == 200
    assert sources_payload["organization"]["name"] == "Tenant Org"


def test_nonprofit_service_applies_feature_flag_overrides_before_enrichment_calls():
    captured = []

    class _FeatureFlagService:
        def apply_evaluation_context_overrides(self, *, organization_id, context):
            captured.append((organization_id, context.setting_for("candid").enabled, context.setting_for("charity_navigator").enabled))
            return EvaluationContext(
                organization_integration_settings={
                    "candid": OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False),
                    "charity_navigator": OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False),
                }
            )

    class _EnrichmentService:
        def enrich(self, **kwargs):
            evaluation_context = kwargs["evaluation_context"]
            return SimpleNamespace(
                to_dict=lambda: {
                    "providers": [],
                    "failures": [],
                    "integration_evaluation": {
                        "integrations": [
                            {
                                "integration_id": "candid",
                                "offered": True,
                                "credentials_present": True,
                                "tenant_enabled": evaluation_context.setting_for("candid").enabled,
                                "required_for_eligibility": False,
                                "attempted": False,
                                "availability_status": "tenant_disabled",
                                "requirement_status": "not_required",
                            },
                            {
                                "integration_id": "charity_navigator",
                                "offered": True,
                                "credentials_present": True,
                                "tenant_enabled": evaluation_context.setting_for("charity_navigator").enabled,
                                "required_for_eligibility": False,
                                "attempted": False,
                                "availability_status": "tenant_disabled",
                                "requirement_status": "not_required",
                            },
                        ],
                        "attempted_integrations": [],
                        "used_integrations": [],
                        "required_unmet_integrations": [],
                        "failure_integrations": [],
                    },
                }
            )

    service = NonprofitService(
        client=_client(),
        enrichment_service=_EnrichmentService(),
        feature_flag_service=_FeatureFlagService(),
    )

    status, payload = service.lookup_nonprofit(
        tenant_context=_tenant_context(),
        verification_input=VerificationInput(ein="123456789"),
        evaluation_context=EvaluationContext(
            organization_integration_settings={
                "candid": OrganizationIntegrationSetting(enabled=True, required_for_eligibility=False),
                "charity_navigator": OrganizationIntegrationSetting(enabled=True, required_for_eligibility=False),
            }
        ),
    )

    assert status == 200
    assert captured == [("org_1", True, True)]
    states = {item["integration_id"]: item for item in payload["integration_evaluation"]["integrations"]}
    assert states["candid"]["tenant_enabled"] is False
    assert states["charity_navigator"]["tenant_enabled"] is False
    assert payload["integration_evaluation"]["attempted_integrations"] == []


def test_nonprofit_service_falls_back_to_supplied_context_when_flag_resolution_fails():
    class _FeatureFlagService:
        def apply_evaluation_context_overrides(self, *, organization_id, context):
            raise RuntimeError("flag store unavailable")

    class _EnrichmentService:
        def enrich(self, **kwargs):
            evaluation_context = kwargs["evaluation_context"]
            return SimpleNamespace(
                to_dict=lambda: {
                    "providers": [],
                    "failures": [],
                    "integration_evaluation": {
                        "integrations": [
                            {
                                "integration_id": "candid",
                                "offered": True,
                                "credentials_present": True,
                                "tenant_enabled": evaluation_context.setting_for("candid").enabled,
                                "required_for_eligibility": False,
                                "attempted": False,
                                "availability_status": "tenant_disabled",
                                "requirement_status": "not_required",
                            }
                        ],
                        "attempted_integrations": [],
                        "used_integrations": [],
                        "required_unmet_integrations": [],
                        "failure_integrations": [],
                    },
                }
            )

    service = NonprofitService(
        client=_client(),
        enrichment_service=_EnrichmentService(),
        feature_flag_service=_FeatureFlagService(),
    )

    status, payload = service.lookup_nonprofit(
        tenant_context=_tenant_context(),
        verification_input=VerificationInput(ein="123456789"),
        evaluation_context=EvaluationContext(
            organization_integration_settings={
                "candid": OrganizationIntegrationSetting(enabled=True, required_for_eligibility=False),
            }
        ),
    )

    assert status == 200
    states = {item["integration_id"]: item for item in payload["integration_evaluation"]["integrations"]}
    assert states["candid"]["tenant_enabled"] is True

