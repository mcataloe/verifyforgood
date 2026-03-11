from __future__ import annotations

from decimal import Decimal
from typing import Any

import boto3

from charity_status.serving.keys import profile_pk, profile_sk


class DynamoProfileStore:
    def __init__(self, table_name: str, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name
        self._resource = dynamodb_resource or boto3.resource("dynamodb")
        self._table = self._resource.Table(table_name)

    def get_profile(self, ein: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"pk": profile_pk(ein), "sk": profile_sk()})
        return response.get("Item")

    def put_profile(self, item: dict[str, Any]) -> None:
        self._table.put_item(Item=_to_dynamodb_types(item))


def _to_dynamodb_types(value: Any) -> Any:
    if isinstance(value, float):
        # Use string conversion for deterministic Decimal representation.
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb_types(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_types(nested) for nested in value]
    if isinstance(value, tuple):
        return tuple(_to_dynamodb_types(nested) for nested in value)
    return value
