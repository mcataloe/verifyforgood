from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuthContext:
    subject: str = "anonymous"
    scopes: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    account_id: str | None = None
    workspace_id: str | None = None
    api_key_id: str | None = None
    plan_id: str | None = None
