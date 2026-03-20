from __future__ import annotations

import json
from pathlib import Path


def test_split_plan_has_expected_sections():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    assert "public_repo" in payload
    assert "private_repo" in payload
    assert "infra_repo" in payload
    assert "dependency_rules" in payload
    assert "migration_sequence" in payload


def test_repo_target_architecture_doc_exists():
    doc = Path("docs/repo-target-architecture.md")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "All billing stays private-platform" in text
    assert "What Should Be Done First" in text


def test_split_plan_referenced_paths_exist():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    include_paths = []
    for section in ("public_repo", "private_repo", "infra_repo"):
        include_paths.extend(payload.get(section, {}).get("include", []))
        include_paths.extend(payload.get(section, {}).get("candidate_modules", []))
        include_paths.extend(payload.get(section, {}).get("mixed_before_extract", []))

    include_paths.extend(payload.get("entrypoints", []))
    include_paths.extend(payload.get("highest_risk_refactors", []))

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
