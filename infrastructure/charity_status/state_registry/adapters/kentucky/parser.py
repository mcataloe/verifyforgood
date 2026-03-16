from __future__ import annotations

import csv
import io
from typing import Any

from charity_status.state_registry.contracts import RawStateRegistryRecord


def parse_kentucky_companies_tsv(payload: str) -> list[RawStateRegistryRecord]:
    text = str(payload or "")
    if not text.strip():
        return []

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows: list[RawStateRegistryRecord] = []
    for row in reader:
        normalized = {str(key or "").strip(): _clean(value) for key, value in row.items() if str(key or "").strip()}
        if not normalized:
            continue
        rows.append(normalized)
    return rows


def build_kentucky_companies_index(rows: list[RawStateRegistryRecord]) -> dict[str, RawStateRegistryRecord]:
    indexed: dict[str, RawStateRegistryRecord] = {}
    for row in rows:
        external_id = kentucky_external_entity_id(row)
        if external_id:
            indexed[external_id] = dict(row)
    return indexed


def kentucky_external_entity_id(row: dict[str, Any]) -> str | None:
    id_value = _clean(row.get("ID"))
    comptype = _clean(row.get("comptype"))
    compseq = _clean(row.get("compseq"))
    if not id_value or not comptype or not compseq:
        return None
    return f"{id_value}:{comptype}:{compseq}"


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
