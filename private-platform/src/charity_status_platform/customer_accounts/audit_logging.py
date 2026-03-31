from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol


class AuditEventType(str, Enum):
    USER_REGISTRATION = "user_registration"
    ORGANIZATION_CREATION = "organization_creation"
    ORGANIZATION_DELETION = "organization_deletion"
    ORGANIZATION_SETTINGS_UPDATE = "organization_settings_update"
    SUPPORT_REQUEST_SUBMITTED = "support_request_submitted"
    MEMBERSHIP_ROLE_CHANGE = "membership_role_change"
    MEMBER_REMOVAL = "member_removal"
    INVITATION_CREATION = "invitation_creation"
    INVITATION_ACCEPTANCE = "invitation_acceptance"
    API_KEY_CREATION = "api_key_creation"
    API_KEY_REVOCATION = "api_key_revocation"
    NONPROFIT_LOOKUP = "nonprofit_lookup"
    NONPROFIT_SEARCH = "nonprofit_search"
    NONPROFIT_FILINGS_ACCESS = "nonprofit_filings_access"
    NONPROFIT_SOURCE_ACCESS = "nonprofit_source_access"


@dataclass(frozen=True)
class AuditRecord:
    audit_id: str
    event_type: AuditEventType
    actor_user_id: str | None
    organization_id: str | None
    target_user_id: str | None
    timestamp: str
    metadata: dict[str, Any]


class AuditLogRepository(Protocol):
    def create(self, record: AuditRecord) -> AuditRecord:
        ...

    def list_for_organization(self, organization_id: str) -> list[AuditRecord]:
        ...

    def list_for_organization_page(
        self,
        organization_id: str,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[AuditRecord], str | None]:
        ...

    def list_identity_events(self) -> list[AuditRecord]:
        ...


class AuditLogService:
    def __init__(
        self,
        *,
        repository: AuditLogRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._logger = logger or logging.getLogger(__name__)

    def record_event(
        self,
        *,
        event_type: AuditEventType,
        actor_user_id: str | None,
        organization_id: str | None,
        target_user_id: str | None,
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> AuditRecord | None:
        record = AuditRecord(
            audit_id=f"audit_{secrets.token_hex(16)}",
            event_type=event_type,
            actor_user_id=_optional_string(actor_user_id),
            organization_id=_optional_string(organization_id),
            target_user_id=_optional_string(target_user_id),
            timestamp=timestamp or _utc_now(),
            metadata=dict(metadata or {}),
        )
        try:
            return self._repository.create(record)
        except Exception:  # noqa: BLE001
            self._logger.exception(
                "identity_audit_log_failed",
                extra={
                    "audit_event_type": record.event_type.value,
                    "actor_user_id": record.actor_user_id,
                    "organization_id": record.organization_id,
                    "target_user_id": record.target_user_id,
                },
            )
            return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _optional_string(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    return candidate or None
