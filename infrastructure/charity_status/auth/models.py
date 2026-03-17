from __future__ import annotations

from dataclasses import dataclass

from charity_status.billing.models import EntitlementSet


@dataclass(frozen=True)
class ApiPlan:
    plan_id: str
    monthly_limit: int
    entitlements: EntitlementSet


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    credential_id: str
    account_id: str
    workspace_id: str
    plan: ApiPlan
    scopes: tuple[str, ...]
    auth_method: str
    rate_limit_profile: str


@dataclass(frozen=True)
class ApiKeyPrincipal(AuthenticatedPrincipal):
    @property
    def key_id(self) -> str:
        return self.credential_id


@dataclass(frozen=True)
class OAuthClientPrincipal(AuthenticatedPrincipal):
    @property
    def client_id(self) -> str:
        return self.credential_id
