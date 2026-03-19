from __future__ import annotations

import json
import re
import urllib.request
from typing import Any, Iterable

from charity_status.form990.models import Form990IndexRecord


def parse_index_records(payload: list[dict[str, Any]]) -> list[Form990IndexRecord]:
    return [_index_item_to_record(item) for item in payload]


def fetch_index_payload(index_url: str, timeout_seconds: int = 60) -> list[dict[str, Any]]:
    request = urllib.request.Request(index_url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"index download failed with status {response.status}")
        payload = response.read()
    return parse_index_source_payload(index_url, payload)


def parse_index_source_payload(index_url: str, body: bytes) -> list[dict[str, Any]]:
    lower_url = index_url.lower()
    if lower_url.endswith(".csv"):
        return _parse_csv_rows(body)
    text = body.decode("utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _parse_csv_rows(body)
    return extract_index_items(payload)


def iter_index_records_from_source(index_url: str, body: bytes) -> Iterable[Form990IndexRecord]:
    lower_url = index_url.lower()
    if lower_url.endswith(".csv"):
        for row in _iter_csv_rows(body):
            yield _index_item_to_record(row)
        return
    for row in parse_index_source_payload(index_url, body):
        yield _index_item_to_record(row)


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


def _index_item_to_record(item: dict[str, Any]) -> Form990IndexRecord:
    normalized = _normalize_index_item(item)
    return Form990IndexRecord(
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


def _parse_csv_rows(body: bytes) -> list[dict[str, Any]]:
    rows = list(_iter_csv_rows(body))
    return rows


def _iter_csv_rows(body: bytes) -> Iterable[dict[str, Any]]:
    import csv
    import io

    text = body.decode("utf-8-sig")
    stream = io.StringIO(text)
    reader = csv.DictReader(stream)
    try:
        first_row_raw = next(reader)
    except StopIteration:
        for row in _parse_csv_rows_positional(text):
            yield row
        return
    first_row = dict(first_row_raw)
    if _row_looks_valid(first_row):
        yield first_row
        for row in reader:
            yield dict(row)
        return
    for row in _parse_csv_rows_positional(text):
        yield row


def _row_looks_valid(sample: dict[str, Any]) -> bool:
    keys = {str(key).strip().lower() for key in sample.keys()}
    expected = {"ein", "taxyr", "tax_yr", "returntype", "return_type", "objectid", "object_id", "url", "xml_url"}
    return len(keys.intersection(expected)) >= 2


def _parse_csv_rows_positional(text: str) -> list[dict[str, Any]]:
    import csv
    import io

    parsed: list[dict[str, Any]] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 8:
            continue
        first = str(row[0]).strip()
        if not first or not first.startswith("."):
            continue
        ein = str(row[1]).strip()
        tax_year = str(row[3]).strip()
        return_type = str(row[5]).strip()
        object_id = str(row[7]).strip()
        source_archive = str(row[8]).strip() if len(row) > 8 else ""
        if not ein:
            continue
        parsed.append(
            {
                "EIN": ein,
                "TaxYr": tax_year or None,
                "ReturnType": return_type or None,
                "ObjectId": object_id or None,
                "URL": _default_xml_url(object_id) if object_id else None,
                "SourceArchive": source_archive or None,
            }
        )
    return parsed
