from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Callable

from verification.branding import default_runtime_user_agent
from verification.state_registry.contracts import RawStateRegistryRecord
from verification.state_registry.errors import StateRegistryError
from verification.state_registry.portal_html import extract_table_records

SEARCH_URL = "https://esos.nv.gov/EntitySearch/OnlineEntitySearch"
TABLE_ID = "entitySearchResults"


class NevadaRegistryClient:
    def __init__(
        self,
        *,
        search_url: str = SEARCH_URL,
        timeout_seconds: int = 20,
        response_loader: Callable[[str], str] | None = None,
        user_agent: str | None = None,
    ) -> None:
        self._search_url = search_url
        self._timeout_seconds = timeout_seconds
        self._response_loader = response_loader
        self._user_agent = str(user_agent or default_runtime_user_agent()).strip()

    def search(self, *, normalized_name: str) -> list[RawStateRegistryRecord]:
        if not normalized_name:
            return []
        html = self._response_loader(normalized_name) if self._response_loader else self._request_html(normalized_name)
        return _parse_nevada_search_results(html)

    def _request_html(self, normalized_name: str) -> str:
        params = urllib.parse.urlencode({"BusinessName": normalized_name})
        request = urllib.request.Request(
            f"{self._search_url}?{params}",
            headers={"User-Agent": self._user_agent, "Accept": "text/html"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise StateRegistryError(f"Nevada registry request failed with status {response.status}")
                html = response.read().decode("utf-8", errors="ignore")
                if "Incapsula incident" in html:
                    raise StateRegistryError("Nevada registry blocked automated access")
                return html
        except StateRegistryError:
            raise
        except Exception as exc:
            raise StateRegistryError(f"Nevada registry request failed: {exc}") from exc


def _parse_nevada_search_results(html: str) -> list[RawStateRegistryRecord]:
    records = []
    for row in extract_table_records(html, table_id=TABLE_ID):
        records.append(
            {
                "entity_name": row.get("Entity Name").text if row.get("Entity Name") else None,
                "detail_href": row.get("Entity Name").href if row.get("Entity Name") else None,
                "entity_number": row.get("Entity Number").text if row.get("Entity Number") else None,
                "status": row.get("Status").text if row.get("Status") else None,
                "entity_type": row.get("Entity Type").text if row.get("Entity Type") else None,
                "formation_date": row.get("Formation Date").text if row.get("Formation Date") else None,
            }
        )
    return [record for record in records if any(record.values())]

