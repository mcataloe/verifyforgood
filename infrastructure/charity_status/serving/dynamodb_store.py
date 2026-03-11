from __future__ import annotations

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
        self._table.put_item(Item=item)
