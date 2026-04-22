from __future__ import annotations

import base64
import json
from typing import Any

from verification.normalization import format_ein, map_irs_status


def search_nonprofit_summaries(
    client: Any,
    name_query: str,
    limit: int,
    state: str | None = None,
    subsection: str | None = None,
    active_only: bool = False,
    cursor: str | None = None,
) -> tuple[int, dict[str, Any]]:
    cursor_name, cursor_ein = _decode_cursor(cursor)
    _, rows = client.search_nonprofits(
        name_query=name_query,
        limit=limit,
        state=state,
        subsection=subsection,
        active_only=active_only,
        cursor_name=cursor_name,
        cursor_ein=cursor_ein,
    )
    page_rows = rows[:limit]
    items = [_to_summary(row) for row in page_rows]
    has_more = len(rows) > limit
    if not has_more and len(page_rows) == limit and page_rows:
        last = page_rows[-1]
        _, probe_rows = client.search_nonprofits(
            name_query=name_query,
            limit=1,
            state=state,
            subsection=subsection,
            active_only=active_only,
            cursor_name=str(last.get("name") or ""),
            cursor_ein=str(last.get("ein") or ""),
        )
        has_more = bool(probe_rows)
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = _encode_cursor(str(last.get("name") or ""), str(last.get("ein") or ""))

    return 200, {
        "query": {"name": name_query, "state": state, "subsection": subsection, "active_only": active_only},
        "pagination": {"limit": limit, "next_cursor": next_cursor},
        "items": items,
    }


def _to_summary(row: dict[str, Any]) -> dict[str, Any]:
    ein = str(row.get("ein") or "")
    return {
        "ein": format_ein(ein) if len(ein) == 9 and ein.isdigit() else ein,
        "ein_normalized": ein,
        "name": row.get("name"),
        "state": row.get("state"),
        "subsection": row.get("subsection"),
        "irs_status": map_irs_status(row.get("status")),
        "active": map_irs_status(row.get("status")) == "active",
        "tax_period": row.get("tax_period"),
    }


def _encode_cursor(name: str, ein: str) -> str:
    payload = json.dumps({"name": name, "ein": ein}, separators=(",", ":"), ensure_ascii=True)
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str | None) -> tuple[str | None, str | None]:
    if not cursor:
        return None, None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return None, None
        name = payload.get("name")
        ein = payload.get("ein")
        if isinstance(name, str) and isinstance(ein, str):
            return name, ein
    except Exception:
        return None, None
    return None, None

