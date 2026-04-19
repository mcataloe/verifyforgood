import importlib

from verification.form990 import Form990IngestService as LegacyForm990IngestService
from verification.normalization import normalize_ein as legacy_normalize_ein
from verification.platform import QueryRuntimeConfig as LegacyQueryRuntimeConfig
from verification.platform import build_resource_name as legacy_build_resource_name
from verification.query import verify_nonprofit as legacy_verify_nonprofit
from verification.state_registry import StateRegistryLookupService as LegacyStateRegistryLookupService
from verification_platform import capability_module_names, resolve_legacy_module_path
from verification_platform.entity_resolution import normalize_ein
from verification_platform.filing_ingestion import Form990IngestService
from verification_platform.organization_verification import verify_nonprofit
from verification_platform.platform_contracts import QueryRuntimeConfig, build_resource_name
from verification_platform.source_connectors import SourceCatalog


def test_verification_platform_capability_modules_import_cleanly():
    for module_name in capability_module_names():
        module = importlib.import_module(module_name)
        assert module is not None


def test_legacy_module_mapping_is_explicit_and_stable():
    assert resolve_legacy_module_path("verification_platform.organization_verification") == (
        "verification.query",
        "verification.decision",
        "verification.evidence",
        "verification.policy",
        "verification.scoring",
    )
    assert resolve_legacy_module_path("verification_platform.platform_contracts") == (
        "verification.core",
        "verification.platform",
    )
    assert resolve_legacy_module_path("verification_platform.entity_resolution.ein_validation") == (
        "verification.normalization.ein",
    )
    assert resolve_legacy_module_path("verification_platform.organization_verification.organization_lookup") == (
        "verification.query.nonprofit_lookup",
    )


def test_new_namespace_re_exports_legacy_verification_objects():
    assert verify_nonprofit is legacy_verify_nonprofit
    assert normalize_ein is legacy_normalize_ein
    assert Form990IngestService is LegacyForm990IngestService
    assert QueryRuntimeConfig is LegacyQueryRuntimeConfig
    assert build_resource_name is legacy_build_resource_name


def test_new_namespace_keeps_runtime_behavior_unchanged():
    assert normalize_ein("12-3456789") == legacy_normalize_ein("12-3456789") == "123456789"
    assert build_resource_name(purpose="profiles", environment="dev") == legacy_build_resource_name(
        purpose="profiles",
        environment="dev",
    )


def test_registry_and_source_connector_namespaces_resolve_capability_exports():
    registry_module = importlib.import_module("verification_platform.nonprofit_registry")
    connector_module = importlib.import_module("verification_platform.source_connectors")

    assert registry_module.StateRegistryLookupService is LegacyStateRegistryLookupService
    assert connector_module.SourceCatalog is SourceCatalog

