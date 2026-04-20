from __future__ import annotations

import json
import pathlib
import sys

from verification.api import (
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
    from verification_platform.runtime import (
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
    from verification_platform.runtime import ENTRYPOINTS, entrypoint_by_surface

    assert {item.surface for item in ENTRYPOINTS} == {
        "public_api",
        "profile_refresh_job",
        "eo_ingest_job",
        "monthly_ingest_job",
    }

    public_api = entrypoint_by_surface("public_api")
    assert public_api.import_path == "verification_backend.api.runtime.handle_api_event"
    assert public_api.runtime_kind == "api_handler"

    for entrypoint in ENTRYPOINTS:
        module_path = ROOT / (entrypoint.current_module.replace(".", "/") + ".py")
        assert module_path.exists(), f"Missing live entrypoint module: {entrypoint.current_module}"
        assert entrypoint.target_service_area == "runtime"


def test_split_plan_tracks_shared_contracts_and_test_layers():
    payload = json.loads((ROOT / "split-plan.json").read_text(encoding="utf-8"))

    assert payload["shared_contracts"] == [
        "infrastructure/verification/api/routes.py",
        "infrastructure/verification/api/responses.py",
        "infrastructure/verification/core/interfaces.py",
        "private-platform/src/verification_platform/runtime/backend_contracts.py",
        "private-platform/src/verification_platform/runtime/entrypoints.py",
    ]

    test_layers = payload["test_layers"]
    assert test_layers["public_core_unit"] == ["public-core/tests/"]
    assert test_layers["private_platform_unit"] == ["private-platform/tests/"]
    assert test_layers["integration_and_compatibility"] == ["tests/"]

    operational_layers = payload["operational_layers"]
    assert operational_layers["frontend"]["root"] == "frontend/"
    assert operational_layers["backend"]["root"] == "backend/"
    assert operational_layers["infrastructure"]["root"] == "infrastructure/"

    backend_targets = payload["backend_runtime_targets"]
    assert backend_targets["public_api"]["current_handler"] == "verification_backend.api.runtime.handle_api_event"
    assert backend_targets["public_api"]["target_directory"] == "backend/api/"
    assert backend_targets["profile_refresh_job"]["target_directory"] == "backend/worker/"
    assert backend_targets["monthly_ingest_job"]["target_directory"] == "backend/ingest-task/"
    assert backend_targets["runtime_shared_contracts"]["target_directory"] == "backend/shared/"


def test_backend_stage1_docs_and_test_readmes_exist():
    readiness_doc = ROOT / "docs" / "backend-stage1-readiness.md"
    backend_doc = ROOT / "backend" / "README.md"
    backend_pyproject = ROOT / "backend" / "pyproject.toml"
    backend_api_doc = ROOT / "backend" / "api" / "README.md"
    backend_worker_doc = ROOT / "backend" / "worker" / "README.md"
    backend_ingest_doc = ROOT / "backend" / "ingest-task" / "README.md"
    backend_shared_doc = ROOT / "backend" / "shared" / "README.md"
    backend_api_dockerfile = ROOT / "backend" / "api" / "Dockerfile"
    backend_worker_dockerfile = ROOT / "backend" / "worker" / "Dockerfile"
    backend_ingest_dockerfile = ROOT / "backend" / "ingest-task" / "Dockerfile"
    backend_tests_doc = ROOT / "backend" / "tests" / "README.md"
    private_platform_pyproject = ROOT / "private-platform" / "pyproject.toml"
    tests_doc = ROOT / "tests" / "README.md"
    public_tests_doc = ROOT / "public-core" / "tests" / "README.md"
    private_tests_doc = ROOT / "private-platform" / "tests" / "README.md"

    assert readiness_doc.exists()
    assert backend_doc.exists()
    assert backend_pyproject.exists()
    assert backend_api_doc.exists()
    assert backend_worker_doc.exists()
    assert backend_ingest_doc.exists()
    assert backend_shared_doc.exists()
    assert backend_api_dockerfile.exists()
    assert backend_worker_dockerfile.exists()
    assert backend_ingest_dockerfile.exists()
    assert backend_tests_doc.exists()
    assert private_platform_pyproject.exists()
    assert tests_doc.exists()
    assert public_tests_doc.exists()
    assert private_tests_doc.exists()

    readiness_text = readiness_doc.read_text(encoding="utf-8")
    assert "Entrypoint Ownership Map" in readiness_text
    assert "Runtime Extraction Targets" in readiness_text
    assert "Current misplaced runtime ownership still stranded in `infrastructure/`" in readiness_text
    assert "`backend/api/`" in readiness_text
    assert "`backend/worker/`" in readiness_text
    assert "`backend/ingest-task/`" in readiness_text
    assert "`backend/shared/`" in readiness_text
    assert "first-class setuptools workspace" in readiness_text
    assert "the installed runtime import root is `verification_backend`" in readiness_text
    assert "`backend/.env.local`" in readiness_text
    assert "`PLATFORM_POSTGRES_URL`" in readiness_text
    assert "`backend/api` -> ALB-backed ECS service" in readiness_text
    assert "`backend/worker` -> private ECS service placeholder" in readiness_text
    assert "`backend/ingest-task` -> ECS task-style runtime" in readiness_text
    assert "local-first Form 990 workspace architecture contract" in readiness_text
    assert "`FORM990_WORKSPACE_DIR`" in readiness_text
    assert "`archives/`, `extracted/`, `logs/`, and `state/`" in readiness_text
    assert "thin rollback/import shim" in readiness_text
    assert "workspace-plus-PostgreSQL Form 990 monthly runtime" in readiness_text
    assert "Shared Contract Guidance" in readiness_text
    assert "Remaining Blockers Before Frontend Scaffolding" in readiness_text

    backend_text = backend_doc.read_text(encoding="utf-8")
    assert "executable backend runtime host layer" in backend_text
    assert "`backend/api/`" in backend_text
    assert "`backend/worker/`" in backend_text
    assert "`backend/ingest-task/`" in backend_text
    assert "`backend/shared/`" in backend_text
    assert "python -m pip install -e .\\public-core -e .\\private-platform -e .\\backend" in backend_text
    assert "python -m verification_backend.ingest_task.cli monthly-worker" in backend_text
    assert "verification_backend.shared.local_dev db-upgrade" in backend_text
    assert "verification_platform" in backend_text
    assert "backend/api/Dockerfile" in backend_text
    assert "provisionable ECS service slot" in backend_text
    assert "backend/ingest-task/Dockerfile" in backend_text
    assert "FORM990_WORKSPACE_DIR" in backend_ingest_doc.read_text(encoding="utf-8")
    assert "local-first Form 990 workspace model" in backend_ingest_doc.read_text(encoding="utf-8")

    backend_api_text = backend_api_doc.read_text(encoding="utf-8")
    assert "verification_backend.api.runtime" in backend_api_text
    assert "thin rollback and compatibility import path" in backend_api_text
    assert "backend/.env.local" in backend_api_text
    assert "Container build/run" in backend_api_text

    backend_worker_text = backend_worker_doc.read_text(encoding="utf-8")
    assert "private-subnet ECS service" in backend_worker_text
    assert "disabled-by-default service slot" in backend_worker_text

    tests_text = tests_doc.read_text(encoding="utf-8")
    assert "public-core/tests/" in tests_text
    assert "private-platform/tests/" in tests_text
    assert "integration and compatibility" in tests_text.lower()


