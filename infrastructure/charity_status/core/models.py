from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthContext:
    subject: str = "anonymous"
    scopes: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
