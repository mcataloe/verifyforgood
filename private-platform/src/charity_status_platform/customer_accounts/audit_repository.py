from __future__ import annotations

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
