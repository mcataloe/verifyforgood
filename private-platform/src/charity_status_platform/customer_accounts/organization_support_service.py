from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from charity_status.branding import BrandingConfig, load_branding_config

from .audit_logging import AuditEventType, AuditLogRepository, AuditRecord
from .identity_repositories import OrganizationRepository

SUPPORT_REQUEST_CATEGORIES = {
    "account_access",
    "billing",
    "api",
    "data_quality",
    "nonprofit_access",
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
    issue_reporting: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "support_contact": dict(self.support_contact),
            "account_context": dict(self.account_context),
            "product_links": dict(self.product_links),
            "issue_reporting": dict(self.issue_reporting),
        }


@dataclass(frozen=True)
class OrganizationSupportReceipt:
    support_request_id: str
    submitted_at: str
    status: str
    delivery_mode: str
    support_email: str

    def to_dict(self) -> dict[str, str]:
        return {
            "support_request_id": self.support_request_id,
            "submitted_at": self.submitted_at,
            "status": self.status,
            "delivery_mode": self.delivery_mode,
            "support_email": self.support_email,
        }


class OrganizationSupportService:
    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        audits: AuditLogRepository,
        branding: BrandingConfig | None = None,
    ) -> None:
        self._organizations = organizations
        self._audits = audits
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
            issue_reporting={
                "delivery_mode": "recorded_only",
                "honesty_notice": (
                    "Support requests are recorded for follow-up. "
                    "There is no customer-visible ticket tracking yet."
                ),
                "urgent_contact_notice": (
                    f"For urgent issues, contact {support_email} directly."
                ),
            },
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

        try:
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
                        "organization_name": organization.name,
                        "reply_email": parsed["reply_email"],
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
        except Exception as exc:  # noqa: BLE001
            raise OrganizationSupportError(
                "Support request could not be recorded",
                status_code=502,
            ) from exc

        return OrganizationSupportReceipt(
            support_request_id=support_request_id,
            submitted_at=submitted_at,
            status="received",
            delivery_mode="recorded_only",
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


def _parse_support_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OrganizationSupportError("Request body must be a JSON object")

    allowed_fields = {"category", "subject", "description", "reply_email", "context"}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise OrganizationSupportError(
            f"Unsupported support request field(s): {', '.join(unknown_fields)}"
        )

    category = _clean_text(payload.get("category"), limit=64)
    if category not in SUPPORT_REQUEST_CATEGORIES:
        raise OrganizationSupportError(
            "category must be one of account_access, billing, api, data_quality, nonprofit_access, settings, or other"
        )

    subject = _clean_text(payload.get("subject"), limit=160)
    if not subject or len(subject) < 3:
        raise OrganizationSupportError("subject must be at least 3 characters")

    description = _clean_text(payload.get("description"), limit=4000)
    if not description or len(description) < 10:
        raise OrganizationSupportError("description must be at least 10 characters")

    reply_email = _validate_optional_email(payload.get("reply_email"))
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
        "reply_email": reply_email,
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
    if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
        raise OrganizationSupportError("reply_email must be a valid email address")
    local, domain = candidate.split("@", 1)
    if "." not in domain or not local.strip() or not domain.strip():
        raise OrganizationSupportError("reply_email must be a valid email address")
    return candidate


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
