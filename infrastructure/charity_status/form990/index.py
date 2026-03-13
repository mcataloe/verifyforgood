from __future__ import annotations

import json
import re
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
    normalized_item = _canonicalize_keys(item)
    object_id = _first(normalized_item, "irsobjectid", "objectid")
    xml_url = _first(normalized_item, "xmlurl", "url")
    if not xml_url and object_id:
        xml_url = _default_xml_url(str(object_id))
    return {
        "ein": _first(normalized_item, "ein"),
        "tax_year": _first(normalized_item, "taxyear", "taxyr"),
        "filing_date": _first(normalized_item, "filingdate", "filingdt"),
        "return_type": _first(normalized_item, "returntype", "formtype"),
        "irs_object_id": object_id,
        "xml_url": xml_url,
        "source_year": _first(normalized_item, "sourceyear"),
        "source_archive": _first(normalized_item, "sourcearchive"),
        "source_signature": _first(normalized_item, "sourcesignature"),
    }


def _canonicalize_keys(item: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in item.items():
        canonical = _canonical_key(str(key))
        if canonical and canonical not in normalized and value is not None:
            normalized[canonical] = value
    return normalized


def _canonical_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(key).strip().lower())


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


def _default_xml_url(object_id: str) -> str:
    return f"https://apps.irs.gov/pub/epostcard/cor/{object_id}_public.xml"
