from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

DEFAULT_APP_NAME = "verification-platform"
DEFAULT_PUBLIC_BRAND_NAME = "Verification Platform"
DEFAULT_USER_AGENT_VERSION = "1.0"
_USER_AGENT_TOKEN = re.compile(r"[^a-z0-9._-]+")


@dataclass(frozen=True)
class BrandingConfig:
    app_name: str = DEFAULT_APP_NAME
    public_brand_name: str = DEFAULT_PUBLIC_BRAND_NAME

    def user_agent(self, *, version: str = DEFAULT_USER_AGENT_VERSION) -> str:
        token = _user_agent_token(self.app_name)
        return f"{token}/{version}"

    def customer_account_label(self, account_id: str) -> str:
        return f"{self.public_brand_name} account {account_id}"


def load_branding_config(env: Mapping[str, str] | None = None) -> BrandingConfig:
    source = env if env is not None else os.environ
    return BrandingConfig(
        app_name=_clean_text(source.get("APP_NAME")) or DEFAULT_APP_NAME,
        public_brand_name=_clean_text(source.get("PUBLIC_BRAND_NAME")) or DEFAULT_PUBLIC_BRAND_NAME,
    )


def default_runtime_user_agent(
    env: Mapping[str, str] | None = None,
    *,
    version: str = DEFAULT_USER_AGENT_VERSION,
) -> str:
    return load_branding_config(env).user_agent(version=version)


def _user_agent_token(value: str) -> str:
    normalized = _USER_AGENT_TOKEN.sub("-", str(value or "").strip().lower()).strip("-")
    return normalized or DEFAULT_APP_NAME


def _clean_text(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


__all__ = [
    "DEFAULT_APP_NAME",
    "DEFAULT_PUBLIC_BRAND_NAME",
    "DEFAULT_USER_AGENT_VERSION",
    "BrandingConfig",
    "load_branding_config",
    "default_runtime_user_agent",
]
