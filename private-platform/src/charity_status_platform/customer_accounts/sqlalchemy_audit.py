from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session, sessionmaker

from .audit_logging import AuditEventType, AuditLogRepository, AuditRecord
from .sqlalchemy_db import customer_accounts_session_scope
from .sqlalchemy_models import OrganizationAuditLogModel


class SqlAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, record: AuditRecord) -> AuditRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            session.add(_audit_model(record))
            session.flush()
        return record

    def list_for_organization(self, organization_id: str) -> list[AuditRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(_organization_audit_query(organization_id)).all()
            return [_audit_record(model) for model in models]

    def list_for_organization_page(
        self,
        organization_id: str,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[AuditRecord], str | None]:
        with customer_accounts_session_scope(self._session_factory) as session:
            query = _organization_audit_query(organization_id)
            if cursor:
                timestamp, audit_id = _decode_cursor(cursor, organization_id=organization_id)
                query = query.where(
                    or_(
                        OrganizationAuditLogModel.timestamp < timestamp,
                        and_(
                            OrganizationAuditLogModel.timestamp == timestamp,
                            OrganizationAuditLogModel.audit_id < audit_id,
                        ),
                    )
                )
            models = session.scalars(query.limit(limit + 1)).all()
            page_items = models[:limit]
            next_cursor = None
            if len(models) > limit:
                last = page_items[-1]
                next_cursor = _encode_cursor(last.organization_id, last.timestamp, last.audit_id)
            return [_audit_record(model) for model in page_items], next_cursor

    def list_identity_events(self) -> list[AuditRecord]:
        with customer_accounts_session_scope(self._session_factory) as session:
            models = session.scalars(
                select(OrganizationAuditLogModel)
                .where(OrganizationAuditLogModel.organization_id.is_(None))
                .order_by(desc(OrganizationAuditLogModel.timestamp), desc(OrganizationAuditLogModel.audit_id))
            ).all()
            return [_audit_record(model) for model in models]


def _organization_audit_query(organization_id: str):
    return (
        select(OrganizationAuditLogModel)
        .where(OrganizationAuditLogModel.organization_id == organization_id)
        .order_by(desc(OrganizationAuditLogModel.timestamp), desc(OrganizationAuditLogModel.audit_id))
    )


def _audit_model(record: AuditRecord) -> OrganizationAuditLogModel:
    return OrganizationAuditLogModel(
        audit_id=record.audit_id,
        event_type=record.event_type.value,
        actor_user_id=record.actor_user_id,
        organization_id=record.organization_id,
        target_user_id=record.target_user_id,
        timestamp=_parse_timestamp(record.timestamp),
        metadata_json=dict(record.metadata),
    )


def _audit_record(model: OrganizationAuditLogModel) -> AuditRecord:
    return AuditRecord(
        audit_id=model.audit_id,
        event_type=AuditEventType(model.event_type),
        actor_user_id=model.actor_user_id,
        organization_id=model.organization_id,
        target_user_id=model.target_user_id,
        timestamp=_format_timestamp(model.timestamp),
        metadata=dict(model.metadata_json or {}),
    )


def _parse_timestamp(value: str) -> datetime:
    normalized = str(value or "").strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _encode_cursor(organization_id: str | None, timestamp: datetime, audit_id: str) -> str:
    payload = {
        "organization_id": organization_id or "",
        "timestamp": _format_timestamp(timestamp),
        "audit_id": audit_id,
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: str, *, organization_id: str) -> tuple[datetime, str]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("cursor is invalid") from exc
    cursor_org_id = str((payload or {}).get("organization_id") or "")
    timestamp = str((payload or {}).get("timestamp") or "")
    audit_id = str((payload or {}).get("audit_id") or "")
    if cursor_org_id != organization_id or not timestamp or not audit_id:
        raise ValueError("cursor is invalid")
    return _parse_timestamp(timestamp), audit_id
