from __future__ import annotations

from types import SimpleNamespace

import pytest

from verification_platform.organization_verification.nonprofit_service import NonprofitService, TenantNonprofitContext
from verification_platform.organization_verification.verification_service import OrganizationVerificationInput as VerificationInput


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
