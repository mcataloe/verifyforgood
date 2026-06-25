from __future__ import annotations

from typing import Any

from verification.backend.shared.models import NonprofitResponse
from verification.backend.shared.normalization import (
    format_ein,
    map_deductibility,
    map_entity_type,
    map_irs_status,
    map_ntee_category,
    recent_990_on_file,
)


MODEL_INFO = {
    "version": "1.0.0",
    "source": "irs.eo_bmf",
}


def map_organization_record(ein: str, row: dict[str, Any]) -> NonprofitResponse:
    normalized_row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
    irs_status = map_irs_status(normalized_row.get("status"))
    deductibility = map_deductibility(normalized_row.get("deductibility"))
    entity_type = map_entity_type(normalized_row.get("subsection"))
    ntee_category = map_ntee_category(normalized_row.get("ntee_cd"))
    recent_990 = recent_990_on_file(normalized_row.get("tax_period"))

    verification = {
        "ein_valid": True,
        "irs_status": irs_status,
        "tax_deductible": deductibility,
        "entity_type": entity_type,
        "country": "US",
        "state": _none_if_blank(normalized_row.get("state")),
        "revoked": irs_status == "inactive",
        "ntee_category": ntee_category,
        "recent_990_on_file": recent_990,
    }

    organization = {
        "name": _none_if_blank(normalized_row.get("name")) or "Unknown",
        "ein": format_ein(ein),
    }

    source_record = {
        "ein": ein,
        "subsection": _none_if_blank(normalized_row.get("subsection")),
        "status": _none_if_blank(normalized_row.get("status")),
        "deductibility": _none_if_blank(normalized_row.get("deductibility")),
        "ntee_cd": _none_if_blank(normalized_row.get("ntee_cd")),
        "tax_period": _none_if_blank(normalized_row.get("tax_period")),
        "asset_amt": _none_if_blank(normalized_row.get("asset_amt")),
        "income_amt": _none_if_blank(normalized_row.get("income_amt")),
        "revenue_amt": _none_if_blank(normalized_row.get("revenue_amt")),
    }

    return NonprofitResponse(
        organization=organization,
        verification=verification,
        scores={},
        model=MODEL_INFO,
        source_record=source_record,
    )


def _none_if_blank(value: Any) -> Any:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


map_nonprofit_record = map_organization_record


__all__ = [
    "MODEL_INFO",
    "map_nonprofit_record",
    "map_organization_record",
]

