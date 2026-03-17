from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    id: str
    name: str
    status: str
    created_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class ManagedApiKey:
    key_id: str
    account_id: str
    status: str
    created_at: str
    plan: str
    scopes: tuple[str, ...]
    rate_limit_profile: str

    def to_dict(self) -> dict[str, object]:
        return {
            "key_id": self.key_id,
            "account_id": self.account_id,
            "status": self.status,
            "created_at": self.created_at,
            "plan": self.plan,
            "scopes": list(self.scopes),
            "rate_limit_profile": self.rate_limit_profile,
        }


@dataclass
class ManagedOAuthClient:
    client_id: str
    account_id: str
    status: str
    created_at: str
    plan: str
    scopes: tuple[str, ...]
    rate_limit_profile: str

    def to_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "account_id": self.account_id,
            "status": self.status,
            "created_at": self.created_at,
            "plan": self.plan,
            "scopes": list(self.scopes),
            "rate_limit_profile": self.rate_limit_profile,
        }
