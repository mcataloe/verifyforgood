from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Any

from charity_status.form990.index import extract_index_items, parse_index_records
from charity_status.form990.models import Form990IndexRecord

YEAR_PATTERN = re.compile(r"(20[0-9]{2})")


@dataclass(frozen=True)
class SourceArchive:
    source_year: str
    source_archive: str
    index_url: str


def discover_archives(catalog: list[dict[str, Any]], mode: str, now_year: int, reconciliation_all_years: bool = False) -> list[SourceArchive]:
    archives: list[SourceArchive] = []
    for item in catalog:
        url = str(item.get("index_url") or "").strip()
        if not url:
            continue
        archive_name = str(item.get("archive_name") or item.get("source_archive") or _archive_name_from_url(url))
        year = str(item.get("year") or item.get("source_year") or _year_from_any(url) or _year_from_any(archive_name) or "")
        if not year:
            continue
        archives.append(SourceArchive(source_year=year, source_archive=archive_name, index_url=url))

    if mode == "bootstrap" or reconciliation_all_years:
        return sorted(archives, key=lambda item: (item.source_year, item.source_archive))
    current = str(now_year)
    previous = str(max(1900, now_year - 1))
    return [item for item in archives if item.source_year in {current, previous}]


def fetch_index_records(index_url: str, source_year: str, source_archive: str, timeout_seconds: int = 60) -> list[Form990IndexRecord]:
    request = urllib.request.Request(index_url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"index download failed with status {response.status}")
        body = response.read()
    rows = _parse_index_payload(index_url, body)
    records = parse_index_records(rows)
    return [
        Form990IndexRecord(
            ein=record.ein,
            tax_year=record.tax_year,
            filing_date=record.filing_date,
            return_type=record.return_type,
            irs_object_id=record.irs_object_id,
            xml_url=record.xml_url,
            source_year=source_year,
            source_archive=source_archive,
            source_signature=_signature_for(record, source_year=source_year, source_archive=source_archive),
        )
        for record in records
    ]


def _parse_index_payload(index_url: str, body: bytes) -> list[dict[str, Any]]:
    lower_url = index_url.lower()
    if lower_url.endswith(".csv"):
        return _parse_csv_rows(body)
    text = body.decode("utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _parse_csv_rows(body)
    return extract_index_items(payload)


def _parse_csv_rows(body: bytes) -> list[dict[str, Any]]:
    text = body.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = [dict(row) for row in reader]
    if _rows_look_valid(rows):
        return rows
    return _parse_csv_rows_positional(text)


def _rows_look_valid(rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return False
    sample = rows[0]
    keys = {str(key).strip().lower() for key in sample.keys()}
    expected = {"ein", "taxyr", "tax_yr", "returntype", "return_type", "objectid", "object_id", "url", "xml_url"}
    return len(keys.intersection(expected)) >= 2


def _parse_csv_rows_positional(text: str) -> list[dict[str, Any]]:
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
        if not ein:
            continue
        parsed.append(
            {
                "EIN": ein,
                "TaxYr": tax_year or None,
                "ReturnType": return_type or None,
                "ObjectId": object_id or None,
                "URL": _default_xml_url(object_id) if object_id else None,
            }
        )
    return parsed


def _default_xml_url(object_id: str) -> str:
    return f"https://apps.irs.gov/pub/epostcard/cor/{object_id}_public.xml"


def _year_from_any(value: str) -> str | None:
    match = YEAR_PATTERN.search(str(value))
    return match.group(1) if match else None


def _archive_name_from_url(url: str) -> str:
    return str(url).rstrip("/").split("/")[-1] or "unknown_archive"


def _signature_for(record: Form990IndexRecord, source_year: str, source_archive: str) -> str:
    parts = [
        record.ein or "",
        record.tax_year or "",
        record.filing_date or "",
        record.return_type or "",
        record.irs_object_id or "",
        record.xml_url or "",
        source_year,
        source_archive,
    ]
    return "|".join(parts)
