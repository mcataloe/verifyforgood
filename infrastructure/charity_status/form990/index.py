from __future__ import annotations

from typing import Any

from charity_status.form990.models import Form990IndexRecord


def parse_index_records(payload: list[dict[str, Any]]) -> list[Form990IndexRecord]:
    records: list[Form990IndexRecord] = []
    for item in payload:
        records.append(
            Form990IndexRecord(
                ein=_to_str(item.get("ein")),
                tax_year=_to_str(item.get("tax_year")),
                filing_date=_to_str(item.get("filing_date")),
                return_type=_to_str(item.get("return_type")),
                irs_object_id=_to_str(item.get("irs_object_id")),
                xml_url=_to_str(item.get("xml_url")),
            )
        )
    return records


def _to_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
