import importlib

from charity_status.form990 import Form990IngestService as LegacyForm990IngestService
from charity_status.normalization import normalize_ein as legacy_normalize_ein
from charity_status.platform import QueryRuntimeConfig as LegacyQueryRuntimeConfig
from charity_status.platform import build_resource_name as legacy_build_resource_name
from charity_status.query import verify_nonprofit as legacy_verify_nonprofit
from charity_status.state_registry import StateRegistryLookupService as LegacyStateRegistryLookupService
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
        "charity_status.query",
        "charity_status.decision",
        "charity_status.evidence",
        "charity_status.policy",
        "charity_status.scoring",
    )
    assert resolve_legacy_module_path("verification_platform.platform_contracts") == (
        "charity_status.core",
        "charity_status.platform",
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
