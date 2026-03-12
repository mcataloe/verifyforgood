from __future__ import annotations

import json
import urllib.request
from typing import Any

from charity_status.form990.models import Form990IndexRecord


def parse_index_records(payload: list[dict[str, Any]]) -> list[Form990IndexRecord]:
    records: list[Form990IndexRecord] = []
    for item in payload:
        normalized = _normalize_index_item(item)
        records.append(
            Form990IndexRecord(
                ein=_to_str(normalized.get("ein")),
                tax_year=_to_str(normalized.get("tax_year")),
                filing_date=_to_str(normalized.get("filing_date")),
                return_type=_to_str(normalized.get("return_type")),
                irs_object_id=_to_str(normalized.get("irs_object_id")),
                xml_url=_to_str(normalized.get("xml_url")),
                source_year=_to_str(normalized.get("source_year")),
                source_archive=_to_str(normalized.get("source_archive")),
                source_signature=_to_str(normalized.get("source_signature")),
            )
        )
    return records


def fetch_index_payload(index_url: str, timeout_seconds: int = 60) -> list[dict[str, Any]]:
    request = urllib.request.Request(index_url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"index download failed with status {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    return extract_index_items(payload)


def extract_index_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    candidate_lists = [
        payload.get("records"),
        payload.get("filings"),
        payload.get("Filings"),
        payload.get("Filings990"),
    ]
    for candidate in candidate_lists:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def _normalize_index_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ein": _first(item, "ein", "EIN"),
        "tax_year": _first(item, "tax_year", "taxYr", "TaxYr", "tax_year"),
        "filing_date": _first(item, "filing_date", "filingDt", "FilingDt"),
        "return_type": _first(item, "return_type", "returnType", "ReturnType"),
        "irs_object_id": _first(item, "irs_object_id", "object_id", "objectId", "ObjectId"),
        "xml_url": _first(item, "xml_url", "xmlUrl", "URL", "url"),
        "source_year": _first(item, "source_year", "SourceYear"),
        "source_archive": _first(item, "source_archive", "SourceArchive"),
        "source_signature": _first(item, "source_signature", "SourceSignature"),
    }


def _first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item.get(key) is not None:
            return item.get(key)
    return None


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
