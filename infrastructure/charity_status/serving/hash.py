from __future__ import annotations

import hashlib
import json
from typing import Any


def calculate_source_hash(source_inputs: dict[str, Any]) -> str:
    canonical = _canonicalize(source_inputs)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key]) for key in sorted(value.keys())}
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value
