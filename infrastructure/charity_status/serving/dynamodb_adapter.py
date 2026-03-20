from __future__ import annotations

from typing import Any

import boto3

from charity_status.serving.keys import profile_pk, profile_sk
from charity_status.serving.storage_serialization import to_dynamodb_types


class DynamoProfileStore:
    def __init__(self, table_name: str, dynamodb_resource: Any | None = None, table: Any | None = None) -> None:
        self._table_name = table_name
        self._resource = None if table is not None else (dynamodb_resource or boto3.resource("dynamodb"))
        self._table = table if table is not None else self._resource.Table(table_name)

    def get_profile(self, ein: str) -> dict[str, Any] | None:
        response = self._table.get_item(Key={"pk": profile_pk(ein), "sk": profile_sk()})
        return response.get("Item")

    def put_profile(self, item: dict[str, Any]) -> None:
        self._table.put_item(Item=to_dynamodb_types(item))
