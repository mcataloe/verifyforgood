from __future__ import annotations


LEGACY_NAMESPACE_ROOT = "charity_status"
LEGACY_MODULE_ALIASES: dict[str, tuple[str, ...]] = {
    "verification_platform.organization_verification": (
        "charity_status.query",
        "charity_status.decision",
        "charity_status.evidence",
        "charity_status.policy",
        "charity_status.scoring",
    ),
    "verification_platform.nonprofit_registry": (
        "charity_status.state_registry",
    ),
    "verification_platform.filing_ingestion": (
        "charity_status.form990",
        "charity_status.ingest",
    ),
    "verification_platform.compliance_data": (
        "charity_status.enrichments",
        "charity_status.enrichments.compliance",
        "charity_status.enrichments.external_signals",
    ),
    "verification_platform.entity_resolution": (
        "charity_status.normalization",
    ),
    "verification_platform.source_connectors": (
        "charity_status.sources",
        "charity_status.ingest",
    ),
    "verification_platform.platform_contracts": (
        "charity_status.core",
        "charity_status.platform",
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
