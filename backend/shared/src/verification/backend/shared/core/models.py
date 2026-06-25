from __future__ import annotations

from dataclasses import dataclass, field

from verification.backend.shared.billing.models import Entitlement, Subscription


@dataclass
class AuthContext:
    account_id: str | None = None
    credential_id: str | None = None
    auth_method: str = "anonymous"
    plan: str | None = None
    scopes: tuple[str, ...] = ()
    rate_limit_profile: str | None = None
    workspace_id: str | None = None
    subject: str = "anonymous"
    subscription: Subscription | None = None
    entitlements: Entitlement | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def plan_id(self) -> str | None:
        return self.plan

    @property
    def api_key_id(self) -> str | None:
        if self.auth_method != "api_key":
            return None
        return self.credential_id

