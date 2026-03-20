from __future__ import annotations

import json
from pathlib import Path


def test_split_plan_has_expected_sections():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    assert "public_repo" in payload
    assert "private_repo" in payload
    assert "infra_repo" in payload
    assert "shared_contracts" in payload
    assert "test_layers" in payload
    assert "dependency_rules" in payload
    assert "migration_sequence" in payload


def test_repo_target_architecture_doc_exists():
    doc = Path("docs/repo-target-architecture.md")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "All billing stays private-platform" in text
    assert "What Should Be Done First" in text

    readiness = Path("docs/backend-stage1-readiness.md")
    assert readiness.exists()
    readiness_text = readiness.read_text(encoding="utf-8")
    assert "Entrypoint Ownership Map" in readiness_text
    assert "Shared Contract Guidance" in readiness_text


def test_package_scaffolding_roots_exist():
    public_root = Path("public-core/src/charity_status")
    private_root = Path("private-platform/src/charity_status_platform")
    infrastructure_doc = Path("infrastructure/README.md")
    public_tests = Path("public-core/tests/README.md")
    private_tests = Path("private-platform/tests/README.md")
    root_tests = Path("tests/README.md")

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
    public_text = Path("public-core/src/charity_status/README.md").read_text(encoding="utf-8")
    private_text = Path("private-platform/src/charity_status_platform/README.md").read_text(encoding="utf-8")
    infrastructure_text = Path("infrastructure/README.md").read_text(encoding="utf-8")
    tests_text = Path("tests/README.md").read_text(encoding="utf-8")

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
    for paths in payload.get("test_layers", {}).values():
        include_paths.extend(paths)

    # Validate concrete paths only; wildcard patterns are validated by convention.
    concrete = [entry for entry in include_paths if "*" not in entry]
    for entry in concrete:
        assert Path(entry).exists(), f"Missing scaffold path: {entry}"


def test_split_plan_keeps_billing_private():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    public_candidates = payload["public_repo"].get("candidate_modules", [])
    private_candidates = payload["private_repo"].get("candidate_modules", [])
    assert "infrastructure/charity_status/billing/" not in public_candidates
    assert "infrastructure/charity_status/billing/" in private_candidates
