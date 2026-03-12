from __future__ import annotations

from dataclasses import asdict
from typing import Any

from charity_status.form990.models import Form990IndexRecord


def to_manifest_entries(records: list[Form990IndexRecord]) -> list[dict[str, Any]]:
    return [asdict(record) for record in records]


def diff_manifest_entries(current: list[Form990IndexRecord], previous_entries: list[dict[str, Any]]) -> tuple[list[Form990IndexRecord], list[Form990IndexRecord], int]:
    previous_by_object: dict[str, dict[str, Any]] = {}
    for entry in previous_entries:
        key = str(entry.get("irs_object_id") or "")
        if not key:
            continue
        previous_by_object[key] = entry

    new_records: list[Form990IndexRecord] = []
    changed_records: list[Form990IndexRecord] = []
    unchanged = 0
    for record in current:
        object_id = record.irs_object_id or ""
        if not object_id:
            changed_records.append(record)
            continue
        previous = previous_by_object.get(object_id)
        if previous is None:
            new_records.append(record)
            continue
        if str(previous.get("source_signature") or "") != str(record.source_signature or ""):
            changed_records.append(record)
        else:
            unchanged += 1
    return new_records, changed_records, unchanged
