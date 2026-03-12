from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiPlan:
    plan_id: str
    monthly_limit: int


@dataclass(frozen=True)
class ApiKeyPrincipal:
    key_id: str
    account_id: str
    workspace_id: str
    plan: ApiPlan
    scopes: tuple[str, ...]
