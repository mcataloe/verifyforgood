from __future__ import annotations

import json
import pathlib
import sys

from charity_status.api import (
    API_RELEASE,
    API_VERSION,
    API_VERSION_PREFIX,
    DeprecationMetadata,
    ResponseContext,
    build_response_context,
    error_response,
    json_response,
    normalize_route_key,
    strip_version_prefix,
    version_path,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


def test_runtime_contract_exports_match_live_backend_contracts():
    from charity_status_platform.runtime import (
        API_RELEASE as platform_api_release,
        API_VERSION as platform_api_version,
        API_VERSION_PREFIX as platform_api_version_prefix,
        DeprecationMetadata as platform_deprecation_metadata,
        ResponseContext as platform_response_context,
        build_response_context as platform_build_response_context,
        error_response as platform_error_response,
        json_response as platform_json_response,
        normalize_route_key as platform_normalize_route_key,
        strip_version_prefix as platform_strip_version_prefix,
        version_path as platform_version_path,
    )

    assert platform_api_version == API_VERSION
    assert platform_api_release == API_RELEASE
    assert platform_api_version_prefix == API_VERSION_PREFIX
    assert platform_deprecation_metadata is DeprecationMetadata
    assert platform_response_context is ResponseContext
    assert platform_build_response_context is build_response_context
    assert platform_json_response is json_response
    assert platform_error_response is error_response
    assert platform_normalize_route_key is normalize_route_key
    assert platform_strip_version_prefix is strip_version_prefix
    assert platform_version_path is version_path


def test_runtime_entrypoint_map_covers_live_backend_handlers():
    from charity_status_platform.runtime import ENTRYPOINTS, entrypoint_by_surface

    assert {item.surface for item in ENTRYPOINTS} == {
        "public_api",
        "profile_refresh_job",
        "eo_ingest_job",
        "form990_ingest_job",
        "form990_orchestrator",
        "form990_worker",
    }

    public_api = entrypoint_by_surface("public_api")
    assert public_api.import_path == "infrastructure.lambda_query.handler"
    assert public_api.runtime_kind == "api_handler"

    for entrypoint in ENTRYPOINTS:
        module_path = ROOT / (entrypoint.current_module.replace(".", "/") + ".py")
        assert module_path.exists(), f"Missing live entrypoint module: {entrypoint.current_module}"
        assert entrypoint.target_service_area == "runtime"


def test_split_plan_tracks_shared_contracts_and_test_layers():
    payload = json.loads((ROOT / "split-plan.json").read_text(encoding="utf-8"))

    assert payload["shared_contracts"] == [
        "infrastructure/charity_status/api/routes.py",
        "infrastructure/charity_status/api/responses.py",
        "infrastructure/charity_status/core/interfaces.py",
        "private-platform/src/charity_status_platform/runtime/backend_contracts.py",
        "private-platform/src/charity_status_platform/runtime/entrypoints.py",
    ]

    test_layers = payload["test_layers"]
    assert test_layers["public_core_unit"] == ["public-core/tests/"]
    assert test_layers["private_platform_unit"] == ["private-platform/tests/"]
    assert test_layers["integration_and_compatibility"] == ["tests/"]


def test_backend_stage1_docs_and_test_readmes_exist():
    readiness_doc = ROOT / "docs" / "backend-stage1-readiness.md"
    tests_doc = ROOT / "tests" / "README.md"
    public_tests_doc = ROOT / "public-core" / "tests" / "README.md"
    private_tests_doc = ROOT / "private-platform" / "tests" / "README.md"

    assert readiness_doc.exists()
    assert tests_doc.exists()
    assert public_tests_doc.exists()
    assert private_tests_doc.exists()

    readiness_text = readiness_doc.read_text(encoding="utf-8")
    assert "Entrypoint Ownership Map" in readiness_text
    assert "Shared Contract Guidance" in readiness_text
    assert "Remaining Blockers Before Frontend Scaffolding" in readiness_text

    tests_text = tests_doc.read_text(encoding="utf-8")
    assert "public-core/tests/" in tests_text
    assert "private-platform/tests/" in tests_text
    assert "integration and compatibility" in tests_text.lower()
