from __future__ import annotations

import urllib.request

from charity_status.branding import default_runtime_user_agent
from charity_status.state_registry.errors import StateRegistryError

DEFAULT_TIMEOUT_SECONDS = 30


class KentuckyBulkDataClient:
    def __init__(
        self,
        *,
        companies_url: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str | None = None,
    ) -> None:
        self._companies_url = str(companies_url or "").strip() or None
        self._timeout_seconds = timeout_seconds
        self._user_agent = str(user_agent or default_runtime_user_agent()).strip()

    def fetch_companies_snapshot(self) -> str:
        if not self._companies_url:
            raise StateRegistryError("Kentucky companies_url is required to fetch bulk company data")
        request = urllib.request.Request(
            self._companies_url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "text/plain, text/tab-separated-values, */*",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise StateRegistryError(f"Kentucky bulk data request failed with status {response.status}")
                return response.read().decode("utf-8-sig")
        except StateRegistryError:
            raise
        except Exception as exc:
            raise StateRegistryError(f"Kentucky bulk data request failed: {exc}") from exc
