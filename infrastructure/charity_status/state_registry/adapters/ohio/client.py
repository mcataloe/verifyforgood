from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Callable

from charity_status.state_registry.contracts import RawStateRegistryRecord
from charity_status.state_registry.errors import StateRegistryError
from charity_status.state_registry.portal_html import extract_table_records

SEARCH_URL = "https://businesssearch.ohiosos.gov/"
TABLE_ID = "ohioSearchResults"


class OhioRegistryClient:
    def __init__(
        self,
        *,
        search_url: str = SEARCH_URL,
        timeout_seconds: int = 20,
        response_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._search_url = search_url
        self._timeout_seconds = timeout_seconds
        self._response_loader = response_loader

    def search(self, *, normalized_name: str) -> list[RawStateRegistryRecord]:
        if not normalized_name:
            return []
        html = self._response_loader(normalized_name) if self._response_loader else self._request_html(normalized_name)
        return _parse_ohio_search_results(html)

    def _request_html(self, normalized_name: str) -> str:
        params = urllib.parse.urlencode({"name": normalized_name})
        request = urllib.request.Request(
            f"{self._search_url}?{params}",
            headers={"User-Agent": "CharityStatusAPI/1.0", "Accept": "text/html"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise StateRegistryError(f"Ohio registry request failed with status {response.status}")
                return response.read().decode("utf-8", errors="ignore")
        except StateRegistryError:
            raise
        except Exception as exc:
            raise StateRegistryError(f"Ohio registry request failed: {exc}") from exc


def _parse_ohio_search_results(html: str) -> list[RawStateRegistryRecord]:
    records = []
    for row in extract_table_records(html, table_id=TABLE_ID):
        records.append(
            {
                "entity_number": row.get("Charter Number").text if row.get("Charter Number") else None,
                "entity_name": row.get("Business Name").text if row.get("Business Name") else None,
                "detail_href": row.get("Business Name").href if row.get("Business Name") else None,
                "status": row.get("Status").text if row.get("Status") else None,
                "entity_type": row.get("Entity Type").text if row.get("Entity Type") else None,
                "formation_date": row.get("Date Filed").text if row.get("Date Filed") else None,
            }
        )
    return [record for record in records if any(record.values())]
