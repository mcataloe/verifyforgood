from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Callable

from verification.backend.shared.branding import default_runtime_user_agent
from verification.backend.ingest.state.contracts import RawStateRegistryRecord
from verification.backend.ingest.state.errors import StateRegistryError
from verification.backend.ingest.state.portal_html import extract_table_records

SEARCH_URL = "https://apps.dos.ny.gov/publicInquiry/"
TABLE_ID = "nySearchResults"


class NewYorkRegistryClient:
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
        return _parse_new_york_search_results(html)

    def _request_html(self, normalized_name: str) -> str:
        params = urllib.parse.urlencode({"searchText": normalized_name})
        request = urllib.request.Request(
            f"{self._search_url}?{params}",
            headers={"User-Agent": self._user_agent, "Accept": "text/html"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise StateRegistryError(f"New York registry request failed with status {response.status}")
                return response.read().decode("utf-8", errors="ignore")
        except StateRegistryError:
            raise
        except Exception as exc:
            raise StateRegistryError(f"New York registry request failed: {exc}") from exc


def _parse_new_york_search_results(html: str) -> list[RawStateRegistryRecord]:
    records = []
    for row in extract_table_records(html, table_id=TABLE_ID):
        records.append(
            {
                "dos_id": row.get("DOS ID").text if row.get("DOS ID") else None,
                "entity_name": row.get("Entity Name").text if row.get("Entity Name") else None,
                "detail_href": row.get("Entity Name").href if row.get("Entity Name") else None,
                "status": row.get("Current Entity Status").text if row.get("Current Entity Status") else None,
                "entity_type": row.get("Entity Type").text if row.get("Entity Type") else None,
                "formation_date": row.get("Initial DOS Filing Date").text if row.get("Initial DOS Filing Date") else None,
            }
        )
    return [record for record in records if any(record.values())]

