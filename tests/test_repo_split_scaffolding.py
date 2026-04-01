from __future__ import annotations

import json
from pathlib import Path


def test_split_plan_has_expected_sections():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    assert "operational_layers" in payload
    assert "public_repo" in payload
    assert "private_repo" in payload
    assert "infra_repo" in payload
    assert "shared_contracts" in payload
    assert "backend_runtime_targets" in payload
    assert "test_layers" in payload
    assert "dependency_rules" in payload
    assert "migration_sequence" in payload


def test_repo_target_architecture_doc_exists():
    doc = Path("docs/repo-target-architecture.md")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "All billing stays private-platform" in text
    assert "Backend Runtime Ownership Targets" in text
    assert "`backend/` becomes the executable runtime host layer" in text
    assert "What Should Be Done First" in text

    readiness = Path("docs/backend-stage1-readiness.md")
    assert readiness.exists()
    readiness_text = readiness.read_text(encoding="utf-8")
    assert "Entrypoint Ownership Map" in readiness_text
    assert "Shared Contract Guidance" in readiness_text
    assert "Runtime Extraction Targets" in readiness_text


def test_package_scaffolding_roots_exist():
    backend_root = Path("backend")
    backend_api = Path("backend/api")
    backend_worker = Path("backend/worker")
    backend_ingest = Path("backend/ingest-task")
    backend_shared = Path("backend/shared")
    public_root = Path("public-core/src/charity_status")
    private_root = Path("private-platform/src/charity_status_platform")
    infrastructure_doc = Path("infrastructure/README.md")
    public_tests = Path("public-core/tests/README.md")
    private_tests = Path("private-platform/tests/README.md")
    root_tests = Path("tests/README.md")

    assert backend_root.exists()
    assert (backend_root / "README.md").exists()
    assert backend_api.exists()
    assert (backend_api / "README.md").exists()
    assert backend_worker.exists()
    assert (backend_worker / "README.md").exists()
    assert backend_ingest.exists()
    assert (backend_ingest / "README.md").exists()
    assert backend_shared.exists()
    assert (backend_shared / "README.md").exists()

    assert public_root.exists()
    assert (public_root / "__init__.py").exists()
    assert (public_root / "README.md").exists()

    assert private_root.exists()
    assert (private_root / "__init__.py").exists()
    assert (private_root / "README.md").exists()

    assert infrastructure_doc.exists()
    assert public_tests.exists()
    assert private_tests.exists()
    assert root_tests.exists()


def test_package_scaffolding_docs_define_boundaries():
    backend_text = Path("backend/README.md").read_text(encoding="utf-8")
    public_text = Path("public-core/src/charity_status/README.md").read_text(encoding="utf-8")
    private_text = Path("private-platform/src/charity_status_platform/README.md").read_text(encoding="utf-8")
    infrastructure_text = Path("infrastructure/README.md").read_text(encoding="utf-8")
    tests_text = Path("tests/README.md").read_text(encoding="utf-8")

    assert "future executable runtime host layer" in backend_text
    assert "backend/` may depend on `public-core/` and `private-platform/`" in backend_text

    assert "Forbidden contents" in public_text
    assert "Dependency direction" in public_text
    assert "platform billing" in public_text

    assert "Forbidden contents" in private_text
    assert "Dependency direction" in private_text
    assert "may depend on `charity_status`" in private_text

    assert "Target role" in infrastructure_text
    assert "deployment/config/wiring only" in infrastructure_text

    assert "public-core/tests/" in tests_text
    assert "private-platform/tests/" in tests_text
    assert "compatibility" in tests_text.lower()


def test_split_plan_records_operational_layers_and_backend_targets():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))

    layers = payload["operational_layers"]
    assert layers["frontend"]["root"] == "frontend/"
    assert layers["backend"]["root"] == "backend/"
    assert layers["infrastructure"]["root"] == "infrastructure/"
    assert layers["backend"]["subdirectories"] == [
        "backend/api/",
        "backend/worker/",
        "backend/ingest-task/",
        "backend/shared/",
    ]

    targets = payload["backend_runtime_targets"]
    assert targets["public_api"]["target_directory"] == "backend/api/"
    assert targets["profile_refresh_job"]["target_directory"] == "backend/worker/"
    assert targets["eo_ingest_job"]["target_directory"] == "backend/ingest-task/"
    assert targets["form990_ingest_job"]["target_directory"] == "backend/ingest-task/"
    assert targets["form990_orchestrator"]["target_directory"] == "backend/ingest-task/"
    assert targets["form990_worker"]["target_directory"] == "backend/ingest-task/"
    assert targets["runtime_shared_contracts"]["target_directory"] == "backend/shared/"


def test_split_plan_referenced_paths_exist():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    include_paths = []
    for section in ("public_repo", "private_repo", "infra_repo"):
        include_paths.extend(payload.get(section, {}).get("include", []))
        include_paths.extend(payload.get(section, {}).get("candidate_modules", []))
        include_paths.extend(payload.get(section, {}).get("mixed_before_extract", []))
        for paths in payload.get(section, {}).get("service_areas", {}).values():
            include_paths.extend(paths)

    include_paths.extend(payload.get("entrypoints", []))
    include_paths.extend(payload.get("shared_contracts", []))
    include_paths.extend(payload.get("highest_risk_refactors", []))
    for layer in payload.get("operational_layers", {}).values():
        if isinstance(layer, dict):
            include_paths.extend(layer.get("subdirectories", []))
    for paths in payload.get("test_layers", {}).values():
        include_paths.extend(paths)
    for entry in payload.get("backend_runtime_targets", {}).values():
        include_paths.extend(entry.get("current_paths", []))
        target_directory = entry.get("target_directory")
        if target_directory:
            include_paths.append(target_directory)

    # Validate concrete paths only; wildcard patterns are validated by convention.
    flattened = []
    for entry in include_paths:
        if isinstance(entry, list):
            flattened.extend(entry)
        else:
            flattened.append(entry)
    concrete = [entry for entry in flattened if "*" not in entry]
    for entry in concrete:
        assert Path(entry).exists(), f"Missing scaffold path: {entry}"


def test_split_plan_keeps_billing_private():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    public_candidates = payload["public_repo"].get("candidate_modules", [])
    private_candidates = payload["private_repo"].get("candidate_modules", [])
    assert "infrastructure/charity_status/billing/" not in public_candidates
    assert "infrastructure/charity_status/billing/" in private_candidates
