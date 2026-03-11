from __future__ import annotations

import json
from typing import Any


_HEADERS = {
    "Content-Type": "application/json",
}


def json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": _HEADERS,
        "body": json.dumps(payload),
    }


def error_response(status_code: int, message: str) -> dict[str, Any]:
    return json_response(status_code, {"message": message})
