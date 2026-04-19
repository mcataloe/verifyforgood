from __future__ import annotations

from typing import Any

from .models import Entitlement
from .service import DEFAULT_ENTITLEMENTS, PLAN_CODES


PLAN_DISPLAY_NAMES: dict[str, str] = {
    "free": "Free",
    "starter": "Starter",
    "growth": "Growth",
    "pro": "Pro",
    "enterprise": "Enterprise",
}

PLAN_CATALOG_FEATURE_KEYS: tuple[str, ...] = (
    "verification",
    "risk_flags",
    "financial_trends",
    "benchmarking",
    "state_registry",
    "monitoring",
    "batch_verification",
    "organization_settings",
)


def build_plan_catalog_payload() -> dict[str, list[dict[str, Any]]]:
    return {
        "plans": [
            build_plan_catalog_entry(plan_code, DEFAULT_ENTITLEMENTS[plan_code])
            for plan_code in PLAN_CODES
        ]
    }


def build_plan_catalog_entry(plan_code: str, entitlements: Entitlement) -> dict[str, Any]:
    normalized_plan_code = str(plan_code or entitlements.plan_code or "free").strip().lower()
    return {
        "plan_code": normalized_plan_code,
        "display_name": PLAN_DISPLAY_NAMES.get(normalized_plan_code, normalized_plan_code.title()),
        "included_usage": {
            "monthly_requests": entitlements.monthly_request_limit,
            "batch_items": entitlements.batch_request_limit,
            "requests_per_minute": entitlements.requests_per_minute,
        },
        "per_request_pricing": {
            "amount_usd_micros": entitlements.overage_unit_price_usd_micros,
            "currency_code": "USD",
            "unit": "request",
        },
        "feature_availability": _feature_availability(entitlements),
    }


def _feature_availability(entitlements: Entitlement) -> dict[str, bool]:
    return {
        "verification": entitlements.allows_capability("verification"),
        "risk_flags": entitlements.has_feature("risk_flags"),
        "financial_trends": entitlements.has_feature("financial_trends"),
        "benchmarking": entitlements.has_feature("benchmarking"),
        "state_registry": entitlements.has_feature("state_registry"),
        "monitoring": entitlements.has_feature("monitoring"),
        "batch_verification": entitlements.allows_capability("batch_verification"),
        "organization_settings": entitlements.allows_capability("organization_settings"),
    }
