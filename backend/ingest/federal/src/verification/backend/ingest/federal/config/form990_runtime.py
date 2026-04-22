"""Shared configuration helpers for backend-owned Form 990 runtimes."""

from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() == "true"


def env_optional_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.lower() == "true"


__all__ = ["env_bool", "env_optional_bool"]
