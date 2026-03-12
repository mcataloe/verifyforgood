from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitlementSet:
    batch_verification: bool = False
    advanced_source_visibility: bool = False
    monitoring_change_events: bool = False
    premium_compliance_risk: bool = False


@dataclass(frozen=True)
class SubscriptionPlan:
    plan_id: str
    monthly_request_limit: int
    included_units: int
    overage_unit_price_usd_micros: int
    entitlements: EntitlementSet


@dataclass(frozen=True)
class Account:
    account_id: str
    plan: SubscriptionPlan


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    account_id: str


@dataclass(frozen=True)
class UsageMeter:
    account_id: str
    period_key: str
    used_units: int


@dataclass(frozen=True)
class MonthlyQuotaPeriod:
    period_key: str
    limit_units: int
    used_units: int
    remaining_units: int
