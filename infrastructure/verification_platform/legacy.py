from __future__ import annotations


LEGACY_NAMESPACE_ROOT = "verification"
LEGACY_MODULE_ALIASES: dict[str, tuple[str, ...]] = {
    "verification_platform.organization_verification": (
        "verification.query",
        "verification.decision",
        "verification.evidence",
        "verification.policy",
        "verification.scoring",
    ),
    "verification_platform.organization_verification.organization_lookup": (
        "verification.query.nonprofit_lookup",
    ),
    "verification_platform.organization_verification.regulatory_filings": (
        "verification.query.verification",
    ),
    "verification_platform.organization_verification.verification_service": (
        "verification.query.verification",
    ),
    "verification_platform.nonprofit_registry": (
        "verification.state_registry",
    ),
    "verification_platform.filing_ingestion": (
        "verification.form990",
        "verification.ingest",
    ),
    "verification_platform.compliance_data": (
        "verification.enrichments",
        "verification.enrichments.compliance",
        "verification.enrichments.external_signals",
    ),
    "verification_platform.compliance_data.interpretation": (
        "verification.enrichments.compliance",
    ),
    "verification_platform.compliance_data.entity_enrichment": (
        "verification.enrichments.service",
    ),
    "verification_platform.entity_resolution": (
        "verification.normalization",
    ),
    "verification_platform.entity_resolution.ein_validation": (
        "verification.normalization.ein",
    ),
    "verification_platform.source_connectors": (
        "verification.sources",
        "verification.ingest",
    ),
    "verification_platform.source_connectors.normalization": (
        "verification.sources.models",
    ),
    "verification_platform.source_connectors.catalog": (
        "verification.sources.catalog",
    ),
    "verification_platform.platform_contracts": (
        "verification.core",
        "verification.platform",
    ),
}


def resolve_legacy_module_path(module_name: str) -> tuple[str, ...]:
    return LEGACY_MODULE_ALIASES.get(str(module_name or "").strip(), ())


def legacy_module_aliases() -> dict[str, tuple[str, ...]]:
    return dict(LEGACY_MODULE_ALIASES)


def capability_module_names() -> tuple[str, ...]:
    return tuple(LEGACY_MODULE_ALIASES.keys())


__all__ = [
    "LEGACY_MODULE_ALIASES",
    "LEGACY_NAMESPACE_ROOT",
    "capability_module_names",
    "legacy_module_aliases",
    "resolve_legacy_module_path",
]

