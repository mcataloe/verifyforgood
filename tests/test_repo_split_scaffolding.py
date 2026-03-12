from __future__ import annotations

import json
from pathlib import Path


def test_split_plan_has_expected_sections():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    assert "public_repo" in payload
    assert "private_repo" in payload
    assert "infra_repo" in payload


def test_split_plan_referenced_paths_exist():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    include_paths = []
    for section in ("public_repo", "private_repo", "infra_repo"):
        include_paths.extend(payload.get(section, {}).get("include", []))

    # Validate concrete paths only; wildcard patterns are validated by convention.
    concrete = [entry for entry in include_paths if "*" not in entry]
    for entry in concrete:
        assert Path(entry).exists(), f"Missing scaffold path: {entry}"
