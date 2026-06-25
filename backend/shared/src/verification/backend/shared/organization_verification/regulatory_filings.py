from __future__ import annotations

from typing import Any


def get_regulatory_filings(client: Any, ein: str) -> tuple[int, dict[str, Any]]:
    _, rows = client.list_form990_filings(ein)
    if not rows:
        return 200, {"ein": ein, "filings": []}

    filings = [
        {
            "tax_year": row.get("tax_year"),
            "form_type": row.get("return_type"),
            "filing_date": row.get("filing_date"),
            "amended": _to_bool(row.get("amended_return")),
            "parse_status": row.get("parse_status"),
        }
        for row in rows
    ]
    return 200, {"ein": ein, "filings": filings}


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1"}:
            return True
        if lowered in {"false", "0"}:
            return False
    return None


get_nonprofit_filings = get_regulatory_filings


__all__ = [
    "get_nonprofit_filings",
    "get_regulatory_filings",
]
