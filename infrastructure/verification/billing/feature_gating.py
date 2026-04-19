from __future__ import annotations

from verification.api import normalize_route_key
from verification.billing.models import Entitlement
from verification.billing.service import route_capability, route_feature_flag


FEATURE_UPGRADE_PLANS: dict[str, str] = {
    "risk_flags": "growth",
    "financial_trends": "growth",
    "benchmarking": "growth",
    "state_registry": "pro",
    "monitoring": "pro",
}

CAPABILITY_UPGRADE_PLANS: dict[str, str] = {
    "batch_verification": "growth",
    "organization_settings": "pro",
}


def build_upgrade_hint(feature_flag: str) -> str:
    upgrade_plan = recommended_upgrade_plan(feature_flag=feature_flag)
    return f"available_on_{upgrade_plan}"


def build_upgrade_hints(feature_flags: list[str] | tuple[str, ...]) -> dict[str, str]:
    return {feature_flag: build_upgrade_hint(feature_flag) for feature_flag in feature_flags}


def recommended_upgrade_plan(*, feature_flag: str | None = None, capability: str | None = None) -> str:
    if feature_flag:
        return FEATURE_UPGRADE_PLANS.get(feature_flag, "enterprise")
    if capability:
        return CAPABILITY_UPGRADE_PLANS.get(capability, "enterprise")
    return "enterprise"


def missing_route_requirement(entitlements: Entitlement, route_key: str) -> tuple[str, str] | None:
    normalized_route = normalize_route_key(route_key)
    required_feature = route_feature_flag(normalized_route)
    if required_feature and not entitlements.has_feature(required_feature):
        return "feature_flag", required_feature
    required_capability = route_capability(normalized_route)
    if required_capability and not entitlements.allows_capability(required_capability):
        return "capability", required_capability
    return None

