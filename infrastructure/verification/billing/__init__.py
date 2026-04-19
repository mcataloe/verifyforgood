from importlib import import_module

from .models import (
    Account,
    Entitlement,
    FEATURE_FLAGS,
    MonthlyQuotaPeriod,
    ResolvedEntitlements,
    Subscription,
    SubscriptionPlan,
    TrialHistory,
    UsageMeter,
    Workspace,
)
from .catalog import PLAN_CATALOG_FEATURE_KEYS, PLAN_DISPLAY_NAMES, build_plan_catalog_entry, build_plan_catalog_payload
from .service import (
    DEFAULT_PLANS,
    DEFAULT_ENTITLEMENTS,
    EntitlementService,
    MeteringDecision,
    check_feature_entitlement,
    check_quota_and_calculate,
    monthly_period_for,
    quota_period_state,
    route_capability,
    route_feature_flag,
)
from .feature_gating import build_upgrade_hint, build_upgrade_hints, missing_route_requirement, recommended_upgrade_plan
from .plan_changes import BillingPlanChangeError, BillingPlanChangeService
from .response_shaping import ResponseShapingService
from .trials import TrialConfig, TrialLifecycleService, load_trial_config

__all__ = [
    "Account",
    "Workspace",
    "Subscription",
    "SubscriptionPlan",
    "TrialHistory",
    "Entitlement",
    "ResolvedEntitlements",
    "FEATURE_FLAGS",
    "UsageMeter",
    "MonthlyQuotaPeriod",
    "PLAN_CATALOG_FEATURE_KEYS",
    "PLAN_DISPLAY_NAMES",
    "DEFAULT_PLANS",
    "DEFAULT_ENTITLEMENTS",
    "EntitlementService",
    "MeteringDecision",
    "monthly_period_for",
    "quota_period_state",
    "route_capability",
    "route_feature_flag",
    "build_upgrade_hint",
    "build_upgrade_hints",
    "missing_route_requirement",
    "recommended_upgrade_plan",
    "BillingPlanChangeError",
    "BillingPlanChangeService",
    "HttpStripeCheckoutClient",
    "TrialConfig",
    "TrialLifecycleService",
    "load_trial_config",
    "ResponseShapingService",
    "BILLING_CUSTOMER_ENTITY",
    "BILLING_SUBSCRIPTION_ENTITY",
    "BILLING_EVENT_ENTITY",
    "PLAN_CATALOG_MAPPING_ENTITY",
    "BillingCustomerBootstrapResult",
    "BillingCustomerBootstrapService",
    "BillingCustomer",
    "BillingSubscription",
    "BillingEvent",
    "PlanCatalogMapping",
    "BillingCustomerRepository",
    "BillingSubscriptionRepository",
    "BillingEventRepository",
    "BillingService",
    "StripeBillingProvider",
    "StripeCustomerBootstrapProvider",
    "ConfiguredStripeBillingProvider",
    "BillingMappingError",
    "InMemoryBillingCustomerRepository",
    "InMemoryBillingSubscriptionRepository",
    "InMemoryBillingEventRepository",
    "ControlPlaneBillingCustomerRepository",
    "ControlPlaneBillingSubscriptionRepository",
    "ControlPlaneBillingEventRepository",
    "build_plan_catalog_entry",
    "build_plan_catalog_payload",
    "check_feature_entitlement",
    "check_quota_and_calculate",
]

_ORGANIZATION_BILLING_EXPORTS = {
    "BILLING_CUSTOMER_ENTITY",
    "BILLING_SUBSCRIPTION_ENTITY",
    "BILLING_EVENT_ENTITY",
    "PLAN_CATALOG_MAPPING_ENTITY",
    "BillingCustomerBootstrapResult",
    "BillingCustomerBootstrapService",
    "BillingCustomer",
    "BillingSubscription",
    "BillingEvent",
    "PlanCatalogMapping",
    "BillingCustomerRepository",
    "BillingSubscriptionRepository",
    "BillingEventRepository",
    "BillingService",
    "StripeBillingProvider",
    "StripeCustomerBootstrapProvider",
    "ConfiguredStripeBillingProvider",
    "BillingMappingError",
    "InMemoryBillingCustomerRepository",
    "InMemoryBillingSubscriptionRepository",
    "InMemoryBillingEventRepository",
    "ControlPlaneBillingCustomerRepository",
    "ControlPlaneBillingSubscriptionRepository",
    "ControlPlaneBillingEventRepository",
}


def __getattr__(name: str):
    if name == "HttpStripeCheckoutClient":
        return getattr(import_module(".checkout", __name__), name)
    if name in _ORGANIZATION_BILLING_EXPORTS:
        return getattr(import_module(".organization_billing", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
