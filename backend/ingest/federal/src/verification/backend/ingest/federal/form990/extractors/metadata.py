from __future__ import annotations

from typing import Any

from verification.backend.ingest.federal.form990.parser import ParsedXml
from verification.backend.ingest.federal.form990.resolver import resolve_field


def extract_metadata_fields(parsed_xml: ParsedXml) -> dict[str, Any]:
    root = parsed_xml.root
    amended_text = resolve_field(root, "amended_return")

    return {
        "ein": resolve_field(root, "ein"),
        "tax_year": resolve_field(root, "tax_year"),
        "tax_period_begin": resolve_field(root, "tax_period_begin"),
        "tax_period_end": resolve_field(root, "tax_period_end"),
        "filing_date": resolve_field(root, "filing_date"),
        "amended_return": _parse_nullable_bool(amended_text),
        "return_type": resolve_field(root, "return_type"),
    }


def _parse_nullable_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None

