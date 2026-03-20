from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from charity_status.branding import default_runtime_user_agent
from charity_status.state_registry.contracts import RawStateRegistryRecord
from charity_status.state_registry.errors import StateRegistryError

COLORADO_DATASET_ID = "4ykn-tg5h"
DEFAULT_BASE_URL = f"https://data.colorado.gov/resource/{COLORADO_DATASET_ID}.json"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_LIMIT = 10

_SELECT_FIELDS = [
    "entityid",
    "entityname",
    "entitystatus",
    "entitytype",
    "jurisdictonofformation",
    "entityformdate",
    "principalcity",
    "principalstate",
    "principalzipcode",
]


class ColoradoRegistryClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        app_token: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._app_token = app_token
        self._user_agent = str(user_agent or default_runtime_user_agent()).strip()

    def search(self, *, normalized_name: str, limit: int = DEFAULT_LIMIT) -> list[RawStateRegistryRecord]:
        if not normalized_name:
            return []
        like_value = normalized_name.replace("'", "''")
        params = {
            "$select": ",".join(_SELECT_FIELDS),
            "$limit": str(max(1, int(limit))),
            "$order": "entityname ASC",
            "$where": f"upper(entityname) like '%{like_value}%'",
        }
        return self._request(params)

    def fetch_by_entity_id(self, entity_id: str) -> RawStateRegistryRecord | None:
        normalized_id = str(entity_id or "").strip()
        if not normalized_id:
            return None
        rows = self._request({"$select": ",".join(_SELECT_FIELDS), "entityid": normalized_id, "$limit": "1"})
        return rows[0] if rows else None

    def _request(self, params: dict[str, str]) -> list[RawStateRegistryRecord]:
        query = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self._base_url}?{query}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise StateRegistryError(f"Colorado registry request failed with status {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
        except StateRegistryError:
            raise
        except Exception as exc:
            raise StateRegistryError(f"Colorado registry request failed: {exc}") from exc
        if not isinstance(payload, list):
            raise StateRegistryError("Colorado registry response must be a list")
        return [row for row in payload if isinstance(row, dict)]

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        if self._app_token:
            headers["X-App-Token"] = self._app_token
        return headers
