from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from verification.backend.shared.branding import BrandingConfig, load_branding_config

from .audit_logging import AuditEventType, AuditLogRepository, AuditRecord
from .identity_repositories import OrganizationRepository
from .support_tickets import (
    SupportDeliveryMode,
    SupportIssueReporting,
    SupportTicketDeliveryStatus,
    SupportTicketEmailDelivery,
    SupportTicketEmailRequest,
    SupportTicketRecord,
    SupportTicketRepository,
)

SUPPORT_REQUEST_CATEGORIES = {
    "account_access",
    "billing",
    "api",
    "data_quality",
    "nonprofit_access",
    "recommendation",
    "settings",
    "other",
}


class OrganizationSupportError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class OrganizationSupportContext:
    support_contact: dict[str, str]
    account_context: dict[str, str | None]
    product_links: dict[str, str]
    issue_reporting: SupportIssueReporting

    def to_dict(self) -> dict[str, Any]:
        return {
            "support_contact": dict(self.support_contact),
            "account_context": dict(self.account_context),
            "product_links": dict(self.product_links),
            "issue_reporting": self.issue_reporting.to_dict(),
        }


@dataclass(frozen=True)
class OrganizationSupportReceipt:
    support_request_id: str
    submitted_at: str
    status: str
    delivery_mode: SupportDeliveryMode
    support_email: str

    def to_dict(self) -> dict[str, str]:
        return {
            "support_request_id": self.support_request_id,
            "submitted_at": self.submitted_at,
            "status": self.status,
            "delivery_mode": self.delivery_mode.value,
            "support_email": self.support_email,
        }


class OrganizationSupportService:
    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        audits: AuditLogRepository,
        support_tickets: SupportTicketRepository | None = None,
        email_delivery: SupportTicketEmailDelivery | None = None,
        branding: BrandingConfig | None = None,
    ) -> None:
        self._organizations = organizations
        self._audits = audits
        self._support_tickets = support_tickets
        self._email_delivery = email_delivery
        self._branding = branding or load_branding_config()

    def get_support_context(
        self,
        *,
        organization_id: str,
        account_id: str,
        workspace_id: str,
        current_plan: str,
        membership_role: str | None,
    ) -> OrganizationSupportContext:
        organization = self._require_organization(organization_id)
        support_email = self._branding.support_email
        delivery_mode = self._delivery_mode()
        return OrganizationSupportContext(
            support_contact={
                "brand_name": self._branding.public_brand_name,
                "support_email": support_email,
                "homepage_url": self._branding.homepage_url(),
                "support_mailto": f"mailto:{support_email}",
            },
            account_context={
                "organization_name": organization.name,
                "organization_id": organization.organization_id,
                "account_id": account_id,
                "workspace_id": workspace_id,
                "contact_email": organization.contact_email,
                "current_plan": current_plan,
                "membership_role": membership_role,
            },
            product_links={
                "api_access_hash": "#/api-access?nav=customer-admin-api",
                "usage_hash": "#/usage-billing?nav=customer-admin-usage",
                "billing_hash": "#/usage-billing?nav=customer-admin-billing",
                "homepage_url": self._branding.homepage_url(),
            },
            issue_reporting=SupportIssueReporting(
                delivery_mode=delivery_mode,
                honesty_notice=(
                    "Support requests are recorded and emailed for follow-up. "
                    "There is no customer-visible ticket tracking yet."
                )
                if delivery_mode is SupportDeliveryMode.RECORDED_AND_EMAILED
                else (
                    "Support requests are recorded for follow-up. "
                    "There is no customer-visible ticket tracking yet."
                ),
                urgent_contact_notice=(
                    f"For urgent issues, contact {support_email} directly."
                ),
            ),
        )

    def submit_support_request(
        self,
        *,
        organization_id: str,
        account_id: str,
        workspace_id: str,
        actor_user_id: str,
        current_plan: str,
        membership_role: str | None,
        payload: dict[str, Any],
    ) -> OrganizationSupportReceipt:
        organization = self._require_organization(organization_id)
        parsed = _parse_support_request_payload(payload)
        submitted_at = _utc_now()
        support_request_id = f"support_{secrets.token_hex(12)}"
        delivery_mode = self._delivery_mode()

        if self._support_tickets is not None and self._email_delivery is not None:
            self._support_tickets.create(
                SupportTicketRecord(
                    ticket_id=None,
                    support_request_id=support_request_id,
                    organization_id=organization_id,
                    actor_user_id=actor_user_id,
                    account_id=account_id,
                    workspace_id=workspace_id,
                    category=parsed["category"],
                    subject=parsed["subject"],
                    description=parsed["description"],
                    reply_email=parsed["reply_email"],
                    watchers=tuple(parsed["watchers"]),
                    route_hash=parsed["route_hash"],
                    user_agent=parsed["user_agent"],
                    current_plan=current_plan,
                    membership_role=membership_role,
                    delivery_mode=delivery_mode,
                    delivery_provider=self._email_delivery.provider_name,
                    delivery_status=SupportTicketDeliveryStatus.PENDING,
                    delivery_recipient=self._email_delivery.delivery_recipient,
                    provider_message_id=None,
                    delivery_error=None,
                    created_at=submitted_at,
                )
            )

        try:
            self._record_audit_event(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                account_id=account_id,
                workspace_id=workspace_id,
                current_plan=current_plan,
                membership_role=membership_role,
                organization_name=organization.name,
                support_request_id=support_request_id,
                submitted_at=submitted_at,
                parsed=parsed,
            )
        except Exception as exc:  # noqa: BLE001
            if self._support_tickets is not None and self._email_delivery is not None:
                self._support_tickets.mark_failed(
                    support_request_id,
                    delivery_error="Support request audit record could not be created",
                )
            raise OrganizationSupportError(
                "Support request could not be recorded",
                status_code=502,
            ) from exc

        if self._support_tickets is not None and self._email_delivery is not None:
            try:
                email_result = self._email_delivery.send(
                    SupportTicketEmailRequest(
                        support_request_id=support_request_id,
                        organization_id=str(organization_id),
                        organization_name=organization.name,
                        actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
                        account_id=account_id,
                        workspace_id=workspace_id,
                        current_plan=current_plan,
                        membership_role=membership_role,
                        category=parsed["category"],
                        subject=parsed["subject"],
                        description=parsed["description"],
                        reply_email=parsed["reply_email"],
                        watchers=tuple(parsed["watchers"]),
                        route_hash=parsed["route_hash"],
                        user_agent=parsed["user_agent"],
                        support_email=self._branding.support_email,
                        submitted_at=submitted_at,
                    )
                )
                self._support_tickets.mark_sent(
                    support_request_id,
                    provider_message_id=email_result.provider_message_id,
                    delivery_recipient=email_result.delivery_recipient,
                    emailed_at=_utc_now(),
                )
            except Exception as exc:  # noqa: BLE001
                self._support_tickets.mark_failed(
                    support_request_id,
                    delivery_error=str(exc),
                )
                raise OrganizationSupportError(
                    "Support request was recorded but email delivery failed",
                    status_code=502,
                ) from exc

        return OrganizationSupportReceipt(
            support_request_id=support_request_id,
            submitted_at=submitted_at,
            status="received",
            delivery_mode=delivery_mode,
            support_email=self._branding.support_email,
        )

    def _require_organization(self, organization_id: str):
        organization = self._organizations.get(organization_id)
        if organization is None:
            raise OrganizationSupportError(
                "Organization support context could not be found",
                status_code=404,
            )
        return organization

    def _delivery_mode(self) -> SupportDeliveryMode:
        if self._support_tickets is not None and self._email_delivery is not None:
            return self._email_delivery.delivery_mode
        return SupportDeliveryMode.RECORDED_ONLY

    def _record_audit_event(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        account_id: str,
        workspace_id: str,
        current_plan: str,
        membership_role: str | None,
        organization_name: str,
        support_request_id: str,
        submitted_at: str,
        parsed: dict[str, Any],
    ) -> None:
        self._audits.create(
            AuditRecord(
                audit_id=support_request_id,
                event_type=AuditEventType.SUPPORT_REQUEST_SUBMITTED,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                timestamp=submitted_at,
                metadata={
                    "account_id": account_id,
                    "category": parsed["category"],
                    "current_plan": current_plan,
                    "membership_role": membership_role,
                    "organization_name": organization_name,
                    "reply_email": parsed["reply_email"],
                    "watchers": parsed["watchers"],
                    "route_hash": parsed["route_hash"],
                    "subject": parsed["subject"],
                    "submitted_at": submitted_at,
                    "support_request_id": support_request_id,
                    "user_agent": parsed["user_agent"],
                    "workspace_id": workspace_id,
                    "description_length": parsed["description_length"],
                },
            )
        )


def _parse_support_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OrganizationSupportError("Request body must be a JSON object")

    allowed_fields = {
        "category",
        "subject",
        "description",
        "reply_email",
        "watchers",
        "context",
    }
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise OrganizationSupportError(
            f"Unsupported support request field(s): {', '.join(unknown_fields)}"
        )

    category = _clean_text(payload.get("category"), limit=64)
    if category not in SUPPORT_REQUEST_CATEGORIES:
        raise OrganizationSupportError(
            "category must be one of account_access, billing, api, data_quality, nonprofit_access, recommendation, settings, or other"
        )

    subject = _clean_text(payload.get("subject"), limit=160)
    if not subject or len(subject) < 3:
        raise OrganizationSupportError("subject must be at least 3 characters")

    description = _clean_text(payload.get("description"), limit=4000)
    if not description or len(description) < 10:
        raise OrganizationSupportError("description must be at least 10 characters")

    reply_email = _validate_optional_email(payload.get("reply_email"))
    watchers = _validate_optional_email_list(payload.get("watchers"))
    context = payload.get("context")
    if context is not None and not isinstance(context, dict):
        raise OrganizationSupportError("context must be an object when provided")
    context = context or {}

    route_hash = _clean_text(
        context.get("current_route_hash", context.get("route_hash")),
        limit=200,
    )
    user_agent = _clean_text(context.get("user_agent"), limit=300)

    return {
        "category": category,
        "subject": subject,
        "description": description,
        "reply_email": reply_email,
        "watchers": watchers,
        "route_hash": route_hash,
        "user_agent": user_agent,
        "description_length": len(description),
    }


def _clean_text(value: Any, *, limit: int) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    return candidate[:limit]


def _validate_optional_email(value: Any) -> str | None:
    candidate = _clean_text(value, limit=254)
    if candidate is None:
        return None
    if not _looks_like_email(candidate):
        raise OrganizationSupportError("reply_email must be a valid email address")
    return candidate


def _validate_optional_email_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OrganizationSupportError("watchers must be an array of email addresses")

    watchers: list[str] = []
    for item in value[:20]:
        candidate = _clean_text(item, limit=254)
        if candidate is None:
            continue
        if not _looks_like_email(candidate):
            raise OrganizationSupportError("watchers must contain only valid email addresses")
        normalized = candidate.lower()
        if normalized not in watchers:
            watchers.append(normalized)
    return watchers


def _looks_like_email(value: str) -> bool:
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        return False
    local, domain = value.split("@", 1)
    return "." in domain and bool(local.strip()) and bool(domain.strip())


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
