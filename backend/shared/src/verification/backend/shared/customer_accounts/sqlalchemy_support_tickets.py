from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .sqlalchemy_db import customer_accounts_session_scope
from .sqlalchemy_models import OrganizationSupportTicketModel
from .support_tickets import (
    SupportDeliveryMode,
    SupportTicketDeliveryStatus,
    SupportTicketRecord,
    SupportTicketRepository,
)


class SqlAlchemySupportTicketRepository(SupportTicketRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, record: SupportTicketRecord) -> SupportTicketRecord:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _support_ticket_model(record)
            session.add(model)
            session.flush()
            session.refresh(model)
            return _support_ticket_record(model)

    def mark_sent(
        self,
        support_request_id: str,
        *,
        provider_message_id: str | None,
        delivery_recipient: str,
        emailed_at: str,
    ) -> SupportTicketRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _lookup_support_ticket(session, support_request_id)
            if model is None:
                return None
            model.delivery_status = SupportTicketDeliveryStatus.SENT.value
            model.delivery_recipient = str(delivery_recipient or "").strip()
            model.provider_message_id = str(provider_message_id or "").strip() or None
            model.delivery_error = None
            model.emailed_at = _parse_timestamp(emailed_at)
            session.flush()
            return _support_ticket_record(model)

    def mark_failed(
        self,
        support_request_id: str,
        *,
        delivery_error: str,
    ) -> SupportTicketRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _lookup_support_ticket(session, support_request_id)
            if model is None:
                return None
            model.delivery_status = SupportTicketDeliveryStatus.FAILED.value
            model.delivery_error = str(delivery_error or "").strip()[:4000] or "Unknown delivery failure"
            session.flush()
            return _support_ticket_record(model)

    def get_by_support_request_id(
        self,
        support_request_id: str,
    ) -> SupportTicketRecord | None:
        with customer_accounts_session_scope(self._session_factory) as session:
            model = _lookup_support_ticket(session, support_request_id)
            return None if model is None else _support_ticket_record(model)


def _lookup_support_ticket(session: Session, support_request_id: str) -> OrganizationSupportTicketModel | None:
    normalized = str(support_request_id or "").strip()
    if not normalized:
        return None
    return session.scalar(
        select(OrganizationSupportTicketModel)
        .where(OrganizationSupportTicketModel.support_request_id == normalized)
        .limit(1)
    )


def _support_ticket_model(record: SupportTicketRecord) -> OrganizationSupportTicketModel:
    kwargs = {
        "support_request_id": record.support_request_id,
        "organization_id": _require_int_id(record.organization_id, field_name="organization_id"),
        "actor_user_id": _normalize_int_id(record.actor_user_id),
        "account_id": record.account_id,
        "workspace_id": record.workspace_id,
        "category": record.category,
        "subject": record.subject,
        "description": record.description,
        "reply_email": record.reply_email,
        "watchers_json": list(record.watchers),
        "route_hash": record.route_hash,
        "user_agent": record.user_agent,
        "current_plan": record.current_plan,
        "membership_role": record.membership_role,
        "delivery_mode": record.delivery_mode.value,
        "delivery_provider": record.delivery_provider,
        "delivery_status": record.delivery_status.value,
        "delivery_recipient": record.delivery_recipient,
        "provider_message_id": record.provider_message_id,
        "delivery_error": record.delivery_error,
        "created_at": _parse_timestamp(record.created_at),
        "emailed_at": _parse_timestamp(record.emailed_at) if record.emailed_at else None,
    }
    if record.ticket_id is not None:
        kwargs["ticket_id"] = int(record.ticket_id)
    return OrganizationSupportTicketModel(**kwargs)


def _support_ticket_record(model: OrganizationSupportTicketModel) -> SupportTicketRecord:
    return SupportTicketRecord(
        ticket_id=model.ticket_id,
        support_request_id=model.support_request_id,
        organization_id=model.organization_id,
        actor_user_id=model.actor_user_id,
        account_id=model.account_id,
        workspace_id=model.workspace_id,
        category=model.category,
        subject=model.subject,
        description=model.description,
        reply_email=model.reply_email,
        watchers=tuple(model.watchers_json or []),
        route_hash=model.route_hash,
        user_agent=model.user_agent,
        current_plan=model.current_plan,
        membership_role=model.membership_role,
        delivery_mode=SupportDeliveryMode(model.delivery_mode),
        delivery_provider=model.delivery_provider,
        delivery_status=SupportTicketDeliveryStatus(model.delivery_status),
        delivery_recipient=model.delivery_recipient,
        provider_message_id=model.provider_message_id,
        delivery_error=model.delivery_error,
        created_at=_format_timestamp(model.created_at) or "",
        emailed_at=_format_timestamp(model.emailed_at),
    )


def _normalize_int_id(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    normalized = str(value).strip()
    if not normalized or not normalized.isdigit():
        return None
    return int(normalized)


def _require_int_id(value: int | str | None, *, field_name: str) -> int:
    normalized = _normalize_int_id(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be a numeric identifier")
    return normalized


def _parse_timestamp(value: str) -> datetime:
    normalized = str(value or "").strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


__all__ = ["SqlAlchemySupportTicketRepository"]
