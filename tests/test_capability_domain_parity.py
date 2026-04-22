from types import SimpleNamespace

from verification.backend.shared.enrichments.compliance import extract_state_compliance as legacy_extract_state_compliance
from verification.backend.shared.enrichments.service import EnrichmentService as LegacyEnrichmentService
from verification.backend.shared.enrichments.service import EntityEnrichmentService
from verification.backend.shared.enrichments.registry import ProviderRegistry
from verification.backend.shared.enrichments.providers.state_registry_mock import StateRegistryMockProvider
from verification.backend.shared.normalization.ein import format_ein as legacy_format_ein
from verification.backend.shared.normalization.ein import normalize_ein as legacy_normalize_ein
from verification.backend.shared.query.nonprofit_lookup import map_nonprofit_record as legacy_map_nonprofit_record
from verification.backend.shared.query.verification import get_nonprofit_filings as legacy_get_nonprofit_filings
from verification.backend.shared.query.verification import verify_nonprofit as legacy_verify_nonprofit
from verification.backend.shared.sources import NormalizedSourceRecord as LegacyNormalizedSourceRecord
from verification.backend.shared.sources import SourceCatalog as LegacySourceCatalog
from verification.backend.shared.compliance_data import EnrichmentService, interpret_jurisdiction_compliance
from verification.backend.shared.entity_resolution import format_employer_identification_number, normalize_employer_identification_number
from verification.backend.shared.organization_verification import (
    OrganizationVerificationInput,
    get_regulatory_filings,
    map_organization_record,
    verify_organization,
)
from verification.backend.shared.source_connectors import NormalizedOrganizationSourceRecord, SourceConnectorCatalog


def _sample_row(name: str = "Parity Org") -> dict[str, str]:
    return {
        "name": name,
        "state": "IL",
        "status": "1",
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "asset_amt": "",
        "income_amt": "",
        "revenue_amt": "",
    }


def _client(record=None, filing_rows=None):
    record = record or _sample_row()
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", record),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein: (
            "qid-f",
            filing_rows
            or [
                {
                    "tax_year": "2024",
                    "return_type": "990",
                    "filing_date": "2025-01-01",
                    "amended_return": "false",
                    "parse_status": "parsed",
                }
            ],
        ),
    )


def test_ein_validation_neutral_names_match_legacy_behavior():
    assert normalize_employer_identification_number("12-3456789") == legacy_normalize_ein("12-3456789") == "123456789"
    assert format_employer_identification_number("123456789") == legacy_format_ein("123456789") == "12-3456789"


def test_organization_lookup_neutral_name_matches_legacy_shape():
    neutral = map_organization_record("123456789", _sample_row()).to_dict()
    legacy = legacy_map_nonprofit_record("123456789", _sample_row()).to_dict()

    assert neutral == legacy
    assert neutral["organization"]["name"] == "Parity Org"


def test_regulatory_filings_neutral_name_matches_legacy_behavior():
    client = _client()

    assert get_regulatory_filings(client, "123456789") == legacy_get_nonprofit_filings(client, "123456789")


def test_organization_verification_neutral_name_matches_legacy_behavior():
    client = _client()
    neutral = verify_organization(client, OrganizationVerificationInput(ein="123456789"))
    legacy = legacy_verify_nonprofit(client, OrganizationVerificationInput(ein="123456789"))

    assert neutral == legacy


def test_compliance_interpretation_neutral_name_matches_legacy_behavior():
    service = EnrichmentService(ProviderRegistry([StateRegistryMockProvider(enabled=True)]))
    payload = service.enrich("123456789", "Parity Org").to_dict()

    assert interpret_jurisdiction_compliance(payload) == legacy_extract_state_compliance(payload)


def test_entity_enrichment_service_neutral_name_is_legacy_service():
    assert EnrichmentService is LegacyEnrichmentService
    assert EntityEnrichmentService is LegacyEnrichmentService


def test_source_normalization_neutral_classes_are_legacy_classes():
    assert NormalizedOrganizationSourceRecord is LegacyNormalizedSourceRecord
    assert SourceConnectorCatalog is LegacySourceCatalog

