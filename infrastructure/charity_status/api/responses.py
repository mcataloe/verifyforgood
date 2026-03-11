from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


_HEADERS = {
    "Content-Type": "application/json",
}


def json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps(payload, default=_json_default),
    }


def error_response(status_code: int, message: str) -> dict[str, Any]:
    return json_response(status_code, {"message": message})


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
