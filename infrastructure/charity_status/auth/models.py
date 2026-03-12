from __future__ import annotations

from dataclasses import dataclass

from charity_status.billing.models import EntitlementSet


@dataclass(frozen=True)
class ApiPlan:
    plan_id: str
    monthly_limit: int
    entitlements: EntitlementSet


@dataclass(frozen=True)
class ApiKeyPrincipal:
    key_id: str
    account_id: str
    workspace_id: str
    plan: ApiPlan
    scopes: tuple[str, ...]
