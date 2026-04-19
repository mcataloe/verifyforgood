from __future__ import annotations

from copy import deepcopy
from typing import Any

from verification.billing.feature_gating import build_upgrade_hints
from verification.billing.models import Entitlement


class ResponseShapingService:
    def shape_verification_response(self, payload: dict[str, Any], entitlements: Entitlement | None) -> dict[str, Any]:
        if entitlements is None:
            return payload

        shaped = deepcopy(payload)
        missing_features: list[str] = []

        if not entitlements.has_feature("financial_trends"):
            missing_features.append("financial_trends")
            shaped.pop("scores", None)
            shaped.pop("filing_summary", None)

        if not entitlements.has_feature("benchmarking"):
            missing_features.append("benchmarking")
            shaped.pop("score_explanation", None)
            shaped.pop("evidence", None)

        if not entitlements.has_feature("risk_flags"):
            missing_features.append("risk_flags")
            shaped.pop("state_compliance", None)
            shaped.pop("external_signals", None)
            _pop_nested(shaped, "decision", "risk_flags")

        if not entitlements.has_feature("state_registry"):
            missing_features.append("state_registry")
            _filter_provider_records(shaped)
            _pop_nested(shaped, "integration_evaluation")
            _pop_nested(shaped, "score_explanation", "integration_policy")

        if not entitlements.has_feature("monitoring"):
            missing_features.append("monitoring")
            shaped.pop("audit", None)

        if missing_features:
            shaped["upgrade_hints"] = build_upgrade_hints(sorted(set(missing_features)))
        return shaped


def _pop_nested(payload: dict[str, Any], *path: str) -> None:
    current: Any = payload
    for index, key in enumerate(path):
        if not isinstance(current, dict) or key not in current:
            return
        if index == len(path) - 1:
            current.pop(key, None)
            return
        current = current.get(key)


def _filter_provider_records(payload: dict[str, Any]) -> None:
    enrichment = payload.get("enrichment")
    if isinstance(enrichment, dict):
        providers = enrichment.get("providers")
        if isinstance(providers, list):
            enrichment["providers"] = [provider for provider in providers if not _is_state_registry_provider(provider)]
        failures = enrichment.get("failures")
        if isinstance(failures, list):
            enrichment["failures"] = [failure for failure in failures if not _is_state_registry_provider(failure)]


def _is_state_registry_provider(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    name = str(item.get("integration_id") or item.get("provider") or item.get("name") or "").strip().lower()
    return name.startswith("state_registry")

