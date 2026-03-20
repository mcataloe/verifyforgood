from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from infrastructure.charity_status.normalization import compare_names, format_ein, map_irs_status, normalize_ein
from infrastructure.charity_status.sources import ProviderCapability, SourceCategory, default_us_source_catalog


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CORE_SRC = ROOT / "public-core" / "src"


def _run_public_core_snippet(snippet: str) -> dict[str, object]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PUBLIC_CORE_SRC)
    result = subprocess.run(
        [sys.executable, "-c", snippet],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
        env=env,
    )
    return json.loads(result.stdout)


def test_public_core_normalization_imports_without_infrastructure_setup():
    payload = _run_public_core_snippet(
        """
import json
from charity_status.normalization import compare_names, format_ein, map_irs_status, normalize_ein

print(json.dumps({
    "normalized_ein": normalize_ein("12-3456789"),
    "formatted_ein": format_ein("123456789"),
    "irs_status": map_irs_status("1"),
    "name_match": compare_names("Helping Hands", "Helping Hands Inc.")["match_confidence"],
}))
"""
    )

    assert payload == {
        "normalized_ein": "123456789",
        "formatted_ein": "12-3456789",
        "irs_status": "active",
        "name_match": "normalized",
    }


def test_public_core_normalization_matches_current_runtime_behavior():
    payload = _run_public_core_snippet(
        """
import json
from charity_status.normalization import compare_names, format_ein, map_irs_status, normalize_ein

print(json.dumps({
    "normalized_ein": normalize_ein("12-3456789"),
    "formatted_ein": format_ein("123456789"),
    "irs_status": map_irs_status("1"),
    "match": compare_names("Helping Hands", "Helping Hands Inc."),
}))
"""
    )

    assert payload["normalized_ein"] == normalize_ein("12-3456789")
    assert payload["formatted_ein"] == format_ein("123456789")
    assert payload["irs_status"] == map_irs_status("1")
    assert payload["match"] == compare_names("Helping Hands", "Helping Hands Inc.")


def test_public_core_sources_import_without_infrastructure_setup():
    payload = _run_public_core_snippet(
        """
import json
from charity_status.sources import ProviderCapability, SourceCategory, default_us_source_catalog

catalog = default_us_source_catalog([
    ProviderCapability(
        provider_name="state_registry_mock",
        categories=[SourceCategory.COMPLIANCE],
        source_ids=["state_registry.compliance"],
        us_only=True,
    )
])

print(json.dumps(catalog.to_dict()))
"""
    )

    assert payload["us_only"] is True
    assert payload["sources"][0]["source_id"] == "state_registry.compliance"
    assert payload["provider_capabilities"][0]["provider_name"] == "state_registry_mock"


def test_public_core_sources_match_current_runtime_behavior():
    payload = _run_public_core_snippet(
        """
import json
from charity_status.sources import ProviderCapability, SourceCategory, default_us_source_catalog

catalog = default_us_source_catalog([
    ProviderCapability(
        provider_name="state_registry_mock",
        categories=[SourceCategory.COMPLIANCE],
        source_ids=["state_registry.compliance"],
        us_only=True,
    )
])

print(json.dumps(catalog.to_dict()))
"""
    )

    runtime_catalog = default_us_source_catalog(
        [
            ProviderCapability(
                provider_name="state_registry_mock",
                categories=[SourceCategory.COMPLIANCE],
                source_ids=["state_registry.compliance"],
                us_only=True,
            )
        ]
    )

    assert payload == runtime_catalog.to_dict()


def test_public_core_schema_modules_import_cleanly():
    payload = _run_public_core_snippet(
        """
import json
from charity_status.evidence import EvidenceFactor
from charity_status.policy import PolicyDefinition, PolicyRule

factor = EvidenceFactor(
    key="eligibility_status",
    category="eligibility_compliance",
    polarity="positive",
    severity="low",
    value="ELIGIBLE",
    message="Deterministic check",
)
policy = PolicyDefinition(
    policy_id="demo",
    rules=[
        PolicyRule(
            rule_id="demo_rule",
            description="Demo rule",
            when={"max_overall_score": 100},
            outcome="manual_review",
        )
    ],
)

print(json.dumps({
    "factor": factor.to_dict(),
    "policy_id": policy.policy_id,
    "rule_count": len(policy.rules),
}))
"""
    )

    assert payload["factor"]["key"] == "eligibility_status"
    assert payload["policy_id"] == "demo"
    assert payload["rule_count"] == 1


def test_public_core_extracted_modules_do_not_reference_private_platform_or_sdk_dependencies():
    extracted_root = PUBLIC_CORE_SRC / "charity_status"
    forbidden_tokens = (
        "charity_status_platform",
        "charity_status.billing",
        "charity_status.auth",
        "charity_status.control_plane",
        "boto3",
        "stripe",
    )

    for path in extracted_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in text, f"{path} unexpectedly references forbidden dependency token {token!r}"
