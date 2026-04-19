from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse

DEFAULT_APP_NAME = "verification-platform"
DEFAULT_PUBLIC_BRAND_NAME = "VerifyForGood"
DEFAULT_SUPPORT_EMAIL = "support@verifyforgood.com"
DEFAULT_DOMAIN = "verifyforgood.com"
DEFAULT_USER_AGENT_VERSION = "1.0"
_USER_AGENT_TOKEN = re.compile(r"[^a-z0-9._-]+")


@dataclass(frozen=True)
class BrandingConfig:
    app_name: str = DEFAULT_APP_NAME
    public_brand_name: str = DEFAULT_PUBLIC_BRAND_NAME
    support_email: str = DEFAULT_SUPPORT_EMAIL
    domain: str = DEFAULT_DOMAIN

    def user_agent(self, *, version: str = DEFAULT_USER_AGENT_VERSION) -> str:
        token = _user_agent_token(self.app_name)
        return f"{token}/{version}"

    def customer_account_label(self, account_id: str) -> str:
        return f"{self.public_brand_name} account {account_id}"

    def homepage_url(self) -> str:
        return f"https://{_normalize_domain(self.domain)}"

    def support_details(self) -> dict[str, str]:
        return {
            "brand_name": self.public_brand_name,
            "support_email": self.support_email,
            "domain": self.domain,
            "homepage_url": self.homepage_url(),
        }


def load_branding_config(env: Mapping[str, str] | None = None) -> BrandingConfig:
    source = env if env is not None else os.environ
    return BrandingConfig(
        app_name=_clean_text(source.get("APP_NAME")) or DEFAULT_APP_NAME,
        public_brand_name=_clean_text(source.get("PUBLIC_BRAND_NAME")) or DEFAULT_PUBLIC_BRAND_NAME,
        support_email=_clean_text(source.get("SUPPORT_EMAIL")) or DEFAULT_SUPPORT_EMAIL,
        domain=_normalize_domain(source.get("DOMAIN")) or DEFAULT_DOMAIN,
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


def _normalize_domain(value: str | None) -> str:
    candidate = _clean_text(value)
    if not candidate:
        return DEFAULT_DOMAIN
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.netloc or parsed.path or "").strip().strip("/").lower()
    return host or DEFAULT_DOMAIN


__all__ = [
    "DEFAULT_APP_NAME",
    "DEFAULT_PUBLIC_BRAND_NAME",
    "DEFAULT_SUPPORT_EMAIL",
    "DEFAULT_DOMAIN",
    "DEFAULT_USER_AGENT_VERSION",
    "BrandingConfig",
    "load_branding_config",
    "default_runtime_user_agent",
]
