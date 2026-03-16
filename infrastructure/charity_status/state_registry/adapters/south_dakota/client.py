from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Callable

from charity_status.state_registry.contracts import RawStateRegistryRecord
from charity_status.state_registry.errors import StateRegistryError
from charity_status.state_registry.portal_html import extract_hidden_inputs, extract_table_records

SEARCH_URL = "https://sosenterprise.sd.gov/BusinessServices/Business/FilingSearch.aspx"
TABLE_ID = "sdSearchResults"


class SouthDakotaRegistryClient:
    def __init__(
        self,
        *,
        search_url: str = SEARCH_URL,
        timeout_seconds: int = 30,
        response_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._search_url = search_url
        self._timeout_seconds = timeout_seconds
        self._response_loader = response_loader

    def search(self, *, normalized_name: str) -> list[RawStateRegistryRecord]:
        if not normalized_name:
            return []
        html = self._response_loader(normalized_name) if self._response_loader else self._request_html(normalized_name)
        return _parse_south_dakota_search_results(html)

    def _request_html(self, normalized_name: str) -> str:
        initial_html = _read_text(_request(self._search_url, timeout_seconds=self._timeout_seconds))
        hidden_inputs = extract_hidden_inputs(initial_html)
        payload = {
            **hidden_inputs,
            "ctl00$MainContent$txtSearchValue": normalized_name,
            "ctl00$MainContent$searchOpt": "EntityName",
            "ctl00$MainContent$txtFilingId": "",
            "ctl00$MainContent$SearchButton": "Search",
        }
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            self._search_url,
            data=encoded,
            headers={
                "User-Agent": "CharityStatusAPI/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": self._search_url,
            },
            method="POST",
        )
        response_html = _read_text(_request(request, timeout_seconds=self._timeout_seconds))
        if "reCAPTCHA failed" in response_html:
            raise StateRegistryError("South Dakota registry blocked automated access with reCAPTCHA")
        return response_html


def _parse_south_dakota_search_results(html: str) -> list[RawStateRegistryRecord]:
    records = []
    for row in extract_table_records(html, table_id=TABLE_ID):
        records.append(
            {
                "entity_number": row.get("Business ID").text if row.get("Business ID") else None,
                "entity_name": row.get("Business Name").text if row.get("Business Name") else None,
                "detail_href": row.get("Business Name").href if row.get("Business Name") else None,
                "status": row.get("Status").text if row.get("Status") else None,
                "entity_type": row.get("Entity Type").text if row.get("Entity Type") else None,
                "formation_date": row.get("Date Filed").text if row.get("Date Filed") else None,
            }
        )
    return [record for record in records if any(record.values())]


def _request(target: str | urllib.request.Request, *, timeout_seconds: int):
    try:
        with urllib.request.urlopen(target, timeout=timeout_seconds) as response:
            if response.status >= 400:
                raise StateRegistryError(f"South Dakota registry request failed with status {response.status}")
            return response.read()
    except StateRegistryError:
        raise
    except Exception as exc:
        raise StateRegistryError(f"South Dakota registry request failed: {exc}") from exc


def _read_text(payload: bytes) -> str:
    return payload.decode("utf-8", errors="ignore")
