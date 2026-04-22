from __future__ import annotations

from decimal import Decimal
from typing import Any


def to_dynamodb_types(value: Any) -> Any:
    if isinstance(value, float):
        # Use string conversion for deterministic Decimal representation.
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: to_dynamodb_types(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [to_dynamodb_types(nested) for nested in value]
    if isinstance(value, tuple):
        return tuple(to_dynamodb_types(nested) for nested in value)
    return value
