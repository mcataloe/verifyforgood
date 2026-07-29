from __future__ import annotations

import json
from pathlib import Path

from verification.backend.shared.billing import DEFAULT_ENTITLEMENTS, build_plan_catalog_payload
from verification.backend.shared.billing.service import CAPABILITY_BY_ROUTE, PLAN_CODE_ALIASES, PLAN_CODES, ROUTE_FEATURE_REQUIREMENTS


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs" / "product" / "plan-catalog.yaml"


def load_catalog() -> dict:
    # The file is intentionally JSON-compatible YAML so this validation does not
    # require adding PyYAML or another parser dependency.
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8-sig"))


def test_plan_catalog_structured_source_matches_backend_entitlements():
    catalog = load_catalog()

    assert tuple(catalog["plan_codes"]) == PLAN_CODES

    for plan_code in PLAN_CODES:
        expected = DEFAULT_ENTITLEMENTS[plan_code]
        documented = catalog["plans"][plan_code]

        assert documented["included_usage"]["monthly_requests"] == expected.monthly_request_limit
        assert documented["included_usage"]["batch_items"] == expected.batch_request_limit
        assert documented["included_usage"]["requests_per_minute"] == expected.requests_per_minute
        assert documented["overage_unit_price_usd_micros"] == expected.overage_unit_price_usd_micros
        assert tuple(documented["feature_flags"]) == expected.feature_flags
        assert tuple(documented["allowed_capabilities"]) == expected.allowed_capabilities


def test_plan_catalog_structured_source_matches_public_payload_projection():
    catalog = load_catalog()
    payload = build_plan_catalog_payload()
    documented_plans = catalog["plans"]

    assert [plan["plan_code"] for plan in payload["plans"]] == catalog["plan_codes"]

    for plan in payload["plans"]:
        plan_code = plan["plan_code"]
        documented = documented_plans[plan_code]

        assert plan["display_name"] == catalog["plan_display_names"][plan_code]
        assert plan["included_usage"] == documented["included_usage"]
        assert plan["per_request_pricing"] == {
            "amount_usd_micros": documented["overage_unit_price_usd_micros"],
            "currency_code": catalog["public_plan_catalog_payload"]["per_request_pricing_currency_code"],
            "unit": catalog["public_plan_catalog_payload"]["per_request_pricing_unit"],
        }

        expected_entitlements = DEFAULT_ENTITLEMENTS[plan_code]
        assert plan["feature_availability"] == {
            "verification": expected_entitlements.allows_capability("verification"),
            "risk_flags": expected_entitlements.has_feature("risk_flags"),
            "financial_trends": expected_entitlements.has_feature("financial_trends"),
            "benchmarking": expected_entitlements.has_feature("benchmarking"),
            "state_registry": expected_entitlements.has_feature("state_registry"),
            "monitoring": expected_entitlements.has_feature("monitoring"),
            "batch_verification": expected_entitlements.allows_capability("batch_verification"),
            "organization_settings": expected_entitlements.allows_capability("organization_settings"),
        }


def test_plan_catalog_structured_source_documents_aliases_and_route_gating():
    catalog = load_catalog()

    assert catalog["plan_aliases"] == PLAN_CODE_ALIASES
    assert catalog["route_capabilities"] == CAPABILITY_BY_ROUTE
    assert catalog["route_feature_requirements"] == ROUTE_FEATURE_REQUIREMENTS


def test_plan_catalog_structured_source_documents_trial_overage_and_subscription_policy():
    catalog = load_catalog()

    assert catalog["trial_behavior"] == {
        "duration_days": 14,
        "requires_credit_card": False,
        "starts_on": "first authenticated customer product request made with an issued credential",
        "trial_entitlement_plan_code": "growth",
        "underlying_billing_plan_code": "free",
        "creates_paid_subscription_automatically": False,
        "charges_customer_automatically": False,
        "fallback_after_expiry": "free",
    }

    assert catalog["overage_behavior"] == {
        "default_allow_overage": True,
        "disable_setting": "billing.allowOverage=false",
        "when_disabled_and_limit_exceeded": {"http_status": 429},
    }

    assert catalog["subscription_resolution"] == {
        "default_plan_when_missing": "free",
        "fallback_plan_when_inactive": "free",
        "active_statuses": ["active", "scheduled"],
        "pending_downgrade_behavior": "keep current active plan until pending effective date",
        "pending_cancellation_behavior": "keep current active plan until pending effective date",
    }
