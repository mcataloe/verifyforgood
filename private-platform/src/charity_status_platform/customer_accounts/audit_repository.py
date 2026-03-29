from __future__ import annotations

import base64
import json
from typing import Any

import boto3

from .audit_logging import AuditLogRepository, AuditRecord, AuditEventType
from .dynamodb_identity import IDENTITY_TABLE_NAME

AUDIT_GLOBAL_PARTITION_KEY = "AUDIT#IDENTITY"


class DynamoAuditLogRepository(AuditLogRepository):
    def __init__(
        self,
        table_name: str = IDENTITY_TABLE_NAME,
        dynamodb_resource: Any | None = None,
        table: Any | None = None,
    ) -> None:
        self._table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(table_name)

    def create(self, record: AuditRecord) -> AuditRecord:
        self._table.put_item(Item=_audit_item(record))
        return record

    def list_for_organization(self, organization_id: str) -> list[AuditRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": f"ORG#{organization_id}",
                ":prefix": "AUDIT#",
            },
        )
        items = response.get("Items") or []
        return [_audit_from_item(item) for item in items if item.get("type") == "AUDIT"]

    def list_for_organization_page(
        self,
        organization_id: str,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[AuditRecord], str | None]:
        query_kwargs: dict[str, Any] = {
            "KeyConditionExpression": "pk = :pk AND begins_with(sk, :prefix)",
            "ExpressionAttributeValues": {
                ":pk": f"ORG#{organization_id}",
                ":prefix": "AUDIT#",
            },
            "Limit": limit,
            "ScanIndexForward": False,
        }
        exclusive_start_key = _decode_cursor(cursor, organization_id=organization_id)
        if exclusive_start_key is not None:
            query_kwargs["ExclusiveStartKey"] = exclusive_start_key
        response = self._table.query(**query_kwargs)
        items = response.get("Items") or []
        records = [_audit_from_item(item) for item in items if item.get("type") == "AUDIT"]
        next_cursor = _encode_cursor(response.get("LastEvaluatedKey"))
        return records, next_cursor

    def list_identity_events(self) -> list[AuditRecord]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={
                ":pk": AUDIT_GLOBAL_PARTITION_KEY,
                ":prefix": "AUDIT#",
            },
        )
        items = response.get("Items") or []
        return [_audit_from_item(item) for item in items if item.get("type") == "AUDIT"]


def _audit_item(record: AuditRecord) -> dict[str, Any]:
    partition_key = (
        f"ORG#{record.organization_id}"
        if record.organization_id
        else AUDIT_GLOBAL_PARTITION_KEY
    )
    return {
        "pk": partition_key,
        "sk": f"AUDIT#{record.timestamp}#{record.audit_id}",
        "type": "AUDIT",
        "audit_id": record.audit_id,
        "event_type": record.event_type.value,
        "actor_user_id": record.actor_user_id,
        "organization_id": record.organization_id,
        "target_user_id": record.target_user_id,
        "timestamp": record.timestamp,
        "metadata": dict(record.metadata),
    }


def _audit_from_item(item: dict[str, Any]) -> AuditRecord:
    return AuditRecord(
        audit_id=str(item.get("audit_id") or ""),
        event_type=AuditEventType(str(item.get("event_type") or AuditEventType.USER_REGISTRATION.value)),
        actor_user_id=_optional_string(item.get("actor_user_id")),
        organization_id=_optional_string(item.get("organization_id")),
        target_user_id=_optional_string(item.get("target_user_id")),
        timestamp=str(item.get("timestamp") or ""),
        metadata=dict(item.get("metadata") or {}),
    )


def _optional_string(value: Any) -> str | None:
    candidate = str(value or "").strip()
    return candidate or None


def _encode_cursor(key: dict[str, Any] | None) -> str | None:
    if not isinstance(key, dict):
        return None
    payload = {
        "pk": str(key.get("pk") or ""),
        "sk": str(key.get("sk") or ""),
    }
    if not payload["pk"] or not payload["sk"]:
        return None
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: str | None, *, organization_id: str) -> dict[str, str] | None:
    candidate = str(cursor or "").strip()
    if not candidate:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(candidate.encode("utf-8")).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("cursor is invalid") from exc
    pk = str((payload or {}).get("pk") or "")
    sk = str((payload or {}).get("sk") or "")
    expected_pk = f"ORG#{organization_id}"
    if pk != expected_pk or not sk.startswith("AUDIT#"):
        raise ValueError("cursor is invalid")
    return {"pk": pk, "sk": sk}
