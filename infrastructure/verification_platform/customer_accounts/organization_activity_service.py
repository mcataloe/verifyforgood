from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audit_logging import AuditEventType, AuditLogRepository, AuditRecord
from .identity_repositories import UserRepository


class OrganizationActivityError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class OrganizationActivityItem:
    activity_id: str
    occurred_at: str
    event_type: str
    category: str
    title: str
    description: str
    actor: dict[str, str | None]
    target: dict[str, str | None]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "occurred_at": self.occurred_at,
            "event_type": self.event_type,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "actor": dict(self.actor),
            "target": dict(self.target),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class OrganizationActivityPage:
    items: list[OrganizationActivityItem]
    next_cursor: str | None
    has_more: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
        }


class OrganizationActivityService:
    def __init__(
        self,
        *,
        audits: AuditLogRepository,
        users: UserRepository,
    ) -> None:
        self._audits = audits
        self._users = users

    def list_activity(
        self,
        *,
        organization_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> OrganizationActivityPage:
        if limit < 1 or limit > 100:
            raise OrganizationActivityError("limit must be between 1 and 100")
        records, next_cursor = self._audits.list_for_organization_page(
            organization_id,
            limit=limit,
            cursor=cursor,
        )
        return OrganizationActivityPage(
            items=[self._summarize(record) for record in records],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )

    def _summarize(self, record: AuditRecord) -> OrganizationActivityItem:
        actor = self._resolve_user(record.actor_user_id)
        target = self._resolve_user(record.target_user_id)
        category, title, description, metadata = _summarize_event(record)
        return OrganizationActivityItem(
            activity_id=record.audit_id,
            occurred_at=record.timestamp,
            event_type=record.event_type.value,
            category=category,
            title=title,
            description=description,
            actor=actor,
            target=target,
            metadata=metadata,
        )

    def _resolve_user(self, user_id: str | None) -> dict[str, str | None]:
        if not user_id:
            return {"user_id": None, "display_name": None, "email": None}
        user = self._users.get(user_id)
        if user is None:
            return {"user_id": user_id, "display_name": None, "email": None}
        return {
            "user_id": user.user_id,
            "display_name": user.full_name or _masked_email(user.email),
            "email": _masked_email(user.email),
        }


def _summarize_event(
    record: AuditRecord,
) -> tuple[str, str, str, dict[str, Any]]:
    metadata = record.metadata or {}
    if record.event_type is AuditEventType.API_KEY_CREATION:
        display_name = _clean_text(metadata.get("display_name"), fallback="API key")
        status = _clean_text(metadata.get("status"), fallback="active")
        return (
            "api_keys",
            "API key created",
            f"{display_name} was created for this organization.",
            {
                "display_name": display_name,
                "key_id": _clean_text(metadata.get("key_id")),
                "status": status,
            },
        )
    if record.event_type is AuditEventType.API_KEY_REVOCATION:
        display_name = _clean_text(metadata.get("display_name"), fallback="API key")
        status = _clean_text(metadata.get("status"), fallback="revoked")
        return (
            "api_keys",
            "API key revoked",
            f"{display_name} was revoked.",
            {
                "display_name": display_name,
                "key_id": _clean_text(metadata.get("key_id")),
                "status": status,
            },
        )
    if record.event_type is AuditEventType.MEMBERSHIP_ROLE_CHANGE:
        role = _clean_text(metadata.get("role"), fallback="updated")
        status = _clean_text(metadata.get("status"), fallback="active")
        return (
            "membership",
            "Member role updated",
            f"Membership role changed to {role}.",
            {"role": role, "status": status},
        )
    if record.event_type is AuditEventType.MEMBER_REMOVAL:
        return (
            "membership",
            "Member removed",
            "A member was removed from the organization.",
            {},
        )
    if record.event_type is AuditEventType.INVITATION_CREATION:
        role = _clean_text(metadata.get("role"), fallback="user")
        status = _clean_text(metadata.get("status"), fallback="pending")
        email = _masked_email(metadata.get("email"))
        return (
            "invitations",
            "Invitation sent",
            f"An invitation was created for {email or 'a teammate'}.",
            {
                "email": email,
                "role": role,
                "status": status,
                "expires_at": _clean_text(metadata.get("expires_at")),
                "invitation_id": _clean_text(metadata.get("invitation_id")),
            },
        )
    if record.event_type is AuditEventType.INVITATION_ACCEPTANCE:
        role = _clean_text(metadata.get("role"), fallback="user")
        email = _masked_email(metadata.get("email"))
        return (
            "invitations",
            "Invitation accepted",
            f"{email or 'A teammate'} accepted an invitation.",
            {
                "email": email,
                "role": role,
                "invitation_id": _clean_text(metadata.get("invitation_id")),
            },
        )
    if record.event_type is AuditEventType.ORGANIZATION_SETTINGS_UPDATE:
        changed_fields = _string_list(metadata.get("changed_fields"))
        changed_sections = _string_list(metadata.get("changed_sections"))
        changed_summary = ", ".join(changed_fields or changed_sections) or "organization settings"
        return (
            "organization_settings",
            "Organization settings updated",
            f"Updated {changed_summary}.",
            {
                "changed_fields": changed_fields,
                "changed_sections": changed_sections,
            },
        )
    if record.event_type is AuditEventType.ORGANIZATION_DELETION:
        return (
            "organization_settings",
            "Organization deleted",
            "The organization was deleted and is no longer available in the portal.",
            {
                "organization_name": _clean_text(metadata.get("organization_name")),
                "slug": _clean_text(metadata.get("slug")),
                "deleted_at": _clean_text(metadata.get("deleted_at")),
                "deleted_by_user_id": _clean_text(metadata.get("deleted_by_user_id")),
            },
        )
    if record.event_type is AuditEventType.SUPPORT_REQUEST_SUBMITTED:
        category = _clean_text(metadata.get("category"), fallback="other")
        subject = _clean_text(metadata.get("subject"), fallback="support request")
        return (
            "support",
            "Support request submitted",
            f"Submitted a {category} support request: {subject}.",
            {
                "category": category,
                "reply_email": _masked_email(metadata.get("reply_email")),
                "watchers": _masked_email_list(metadata.get("watchers")),
                "support_request_id": _clean_text(metadata.get("support_request_id")),
            },
        )
    if record.event_type is AuditEventType.ORGANIZATION_CREATION:
        return (
            "organization_settings",
            "Organization created",
            "The organization was created and initial admin access was granted.",
            {
                "organization_name": _clean_text(metadata.get("organization_name")),
                "slug": _clean_text(metadata.get("slug")),
            },
        )
    if record.event_type in {
        AuditEventType.NONPROFIT_LOOKUP,
        AuditEventType.NONPROFIT_SEARCH,
        AuditEventType.NONPROFIT_FILINGS_ACCESS,
        AuditEventType.NONPROFIT_SOURCE_ACCESS,
    }:
        return _summarize_nonprofit_event(record)
    return (
        "organization_settings",
        "Activity recorded",
        "An organization event was recorded.",
        {},
    )


def _summarize_nonprofit_event(
    record: AuditRecord,
) -> tuple[str, str, str, dict[str, Any]]:
    metadata = record.metadata or {}
    if record.event_type is AuditEventType.NONPROFIT_LOOKUP:
        ein = _clean_text(metadata.get("ein"))
        return (
            "nonprofit_access",
            "Nonprofit lookup",
            f"Viewed nonprofit details for EIN {ein or 'unknown'}." if ein else "Viewed nonprofit details.",
            {
                "ein": ein,
                "response_sources": _string_list(metadata.get("response_sources")),
            },
        )
    if record.event_type is AuditEventType.NONPROFIT_SEARCH:
        result_count = _safe_int(metadata.get("result_count"))
        return (
            "nonprofit_access",
            "Nonprofit search",
            f"Ran a nonprofit search that returned {result_count} result{'s' if result_count != 1 else ''}.",
            {
                "result_count": result_count,
                "query_state": _clean_text(metadata.get("query_state")),
                "query_subsection": _clean_text(metadata.get("query_subsection")),
            },
        )
    if record.event_type is AuditEventType.NONPROFIT_FILINGS_ACCESS:
        ein = _clean_text(metadata.get("ein"))
        filing_count = _safe_int(metadata.get("filing_count"))
        return (
            "nonprofit_access",
            "Filings viewed",
            f"Viewed {filing_count} filing{'s' if filing_count != 1 else ''} for EIN {ein or 'unknown'}.",
            {"ein": ein, "filing_count": filing_count},
        )
    ein = _clean_text(metadata.get("ein"))
    source_name = _clean_text(metadata.get("source_name"))
    return (
        "nonprofit_access",
        "Source data viewed",
        f"Viewed source activity for EIN {ein or 'unknown'}" + (f" using {source_name}." if source_name else "."),
        {
            "ein": ein,
            "source_name": source_name,
            "response_sources": _string_list(metadata.get("response_sources")),
        },
    )


def _clean_text(value: Any, *, fallback: str | None = None) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return fallback
    return candidate[:200]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    results: list[str] = []
    for item in value:
        candidate = _clean_text(item)
        if candidate:
            results.append(candidate)
    return results


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _masked_email(value: Any) -> str | None:
    candidate = str(value or "").strip().lower()
    if not candidate or "@" not in candidate:
        return None
    local, domain = candidate.split("@", 1)
    if not local:
        return f"***@{domain}"
    if len(local) == 1:
        return f"{local}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _masked_email_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    results: list[str] = []
    for item in value:
        masked = _masked_email(item)
        if masked:
            results.append(masked)
    return results
