from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from verification.enrichments.organization_settings_service import (
    AccountBillingSettings,
    OrganizationIntegrationSettings,
    OrganizationIntegrationSettingsDocument,
    OrganizationIntegrationSettingsService,
    OrganizationIntegrationSettingsValidationError,
)

from .audit_logging import AuditEventType, AuditLogService
from .identity_models import OrganizationRecord
from .identity_repositories import (
    DuplicateOrganizationSlugError,
    OrganizationRepository,
)


class OrganizationSettingsNotFoundError(LookupError):
    status_code = 404


@dataclass(frozen=True)
class OrganizationProfileSettings:
    organization_id: str
    display_name: str
    slug: str
    contact_email: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_record(cls, organization: OrganizationRecord) -> "OrganizationProfileSettings":
        return cls(
            organization_id=organization.organization_id,
            display_name=organization.name,
            slug=organization.slug,
            contact_email=organization.contact_email,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "organizationId": self.organization_id,
            "displayName": self.display_name,
            "slug": self.slug,
            "contactEmail": self.contact_email,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


@dataclass(frozen=True)
class OrganizationSettingsDocument:
    workspace_id: str | None
    account_id: str | None
    organization: OrganizationProfileSettings
    integration_settings: OrganizationIntegrationSettings
    billing_settings: AccountBillingSettings
    source: str
    updated_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "account_id": self.account_id,
            "organization": self.organization.to_dict(),
            "integrations": self.integration_settings.to_dict(),
            "billing": self.billing_settings.to_dict(),
            "source": self.source,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class OrganizationProfileUpdate:
    display_name: str
    slug: str
    contact_email: str | None


class OrganizationSettingsService:
    def __init__(
        self,
        *,
        integration_settings: OrganizationIntegrationSettingsService,
        organizations: OrganizationRepository,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self._integration_settings = integration_settings
        self._organizations = organizations
        self._audit_log_service = audit_log_service

    def get_settings(
        self,
        *,
        organization_id: str,
        workspace_id: str | None,
        account_id: str | None,
    ) -> OrganizationSettingsDocument:
        organization = self._require_organization(organization_id)
        settings_document = self._integration_settings.get_settings(
            workspace_id=workspace_id,
            account_id=account_id,
        )
        return self._compose_document(
            organization=organization,
            settings_document=settings_document,
        )

    def update_settings(
        self,
        *,
        organization_id: str,
        workspace_id: str | None,
        account_id: str | None,
        payload: dict[str, Any],
        actor_user_id: str | None = None,
    ) -> OrganizationSettingsDocument:
        organization = self._require_organization(organization_id)
        has_organization_payload = "organization" in payload
        has_settings_payload = "integrations" in payload or "billing" in payload
        if not has_organization_payload and not has_settings_payload:
            raise OrganizationIntegrationSettingsValidationError(
                "Request body must include organization, integrations, or billing object"
            )

        updated_at = _utc_now()
        changed_fields: list[str] = []
        changed_sections: list[str] = []
        if has_organization_payload:
            profile_update = self._parse_profile_payload(
                payload.get("organization"), current=organization
            )
            changed_fields = _profile_changed_fields(
                current=organization, update=profile_update
            )
            try:
                persisted = self._organizations.update_profile(
                    organization_id,
                    name=profile_update.display_name,
                    slug=profile_update.slug,
                    contact_email=profile_update.contact_email,
                    updated_at=updated_at,
                )
            except DuplicateOrganizationSlugError:
                raise OrganizationIntegrationSettingsValidationError(
                    "organization.slug is already in use"
                ) from None
            if persisted is None:
                raise OrganizationSettingsNotFoundError("Organization was not found")
            organization = persisted

        settings_document = self._integration_settings.get_settings(
            workspace_id=workspace_id,
            account_id=account_id,
        )
        previous_billing_settings = settings_document.billing_settings
        if has_settings_payload:
            if "billing" in payload:
                changed_sections.append("billing")
            if "integrations" in payload:
                changed_sections.append("integrations")
            settings_document = self._integration_settings.update_settings(
                workspace_id=workspace_id,
                account_id=account_id,
                payload={key: value for key, value in payload.items() if key in {"integrations", "billing"}},
            )
        document = self._compose_document(
            organization=organization,
            settings_document=settings_document,
        )
        if self._audit_log_service is not None and (changed_fields or changed_sections):
            self._audit_log_service.record_event(
                event_type=AuditEventType.ORGANIZATION_SETTINGS_UPDATE,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                metadata={
                    "changed_fields": changed_fields,
                    "changed_sections": changed_sections,
                },
            )
        if (
            self._audit_log_service is not None
            and "billing" in changed_sections
            and previous_billing_settings.allow_overage != document.billing_settings.allow_overage
        ):
            self._audit_log_service.record_event(
                event_type=(
                    AuditEventType.BILLING_OVERAGE_ENABLED
                    if document.billing_settings.allow_overage
                    else AuditEventType.BILLING_OVERAGE_DISABLED
                ),
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                metadata={
                    "previous_allow_overage": previous_billing_settings.allow_overage,
                    "new_allow_overage": document.billing_settings.allow_overage,
                },
            )
        return document

    def _compose_document(
        self,
        *,
        organization: OrganizationRecord,
        settings_document: OrganizationIntegrationSettingsDocument,
    ) -> OrganizationSettingsDocument:
        return OrganizationSettingsDocument(
            workspace_id=settings_document.workspace_id or organization.organization_id,
            account_id=settings_document.account_id or organization.organization_id,
            organization=OrganizationProfileSettings.from_record(organization),
            integration_settings=settings_document.integration_settings,
            billing_settings=settings_document.billing_settings,
            source=settings_document.source,
            updated_at=_latest_updated_at(settings_document.updated_at, organization.updated_at),
        )

    def _parse_profile_payload(
        self,
        payload: Any,
        *,
        current: OrganizationRecord,
    ) -> OrganizationProfileUpdate:
        if not isinstance(payload, dict):
            raise OrganizationIntegrationSettingsValidationError("organization must be an object")
        allowed_fields = {
            "displayName",
            "display_name",
            "contactEmail",
            "contact_email",
            "slug",
        }
        unknown_fields = sorted(str(key) for key in payload.keys() if key not in allowed_fields)
        if unknown_fields:
            raise OrganizationIntegrationSettingsValidationError(
                f"Unsupported organization field(s): {', '.join(unknown_fields)}"
            )
        display_name = current.name
        if "displayName" in payload or "display_name" in payload:
            display_name = _validate_display_name(
                payload.get("displayName", payload.get("display_name"))
            )
        contact_email = current.contact_email
        if "contactEmail" in payload or "contact_email" in payload:
            contact_email = _validate_contact_email(
                payload.get("contactEmail", payload.get("contact_email"))
            )
        slug = current.slug
        if "slug" in payload:
            slug = _validate_slug(payload.get("slug"), fallback_display_name=display_name)
        return OrganizationProfileUpdate(
            display_name=display_name,
            slug=slug,
            contact_email=contact_email,
        )

    def _require_organization(self, organization_id: str) -> OrganizationRecord:
        organization = self._organizations.get(organization_id)
        if organization is None:
            raise OrganizationSettingsNotFoundError("Organization was not found")
        return organization


def _validate_display_name(value: Any) -> str:
    candidate = str(value or "").strip()
    if len(candidate) < 2:
        raise OrganizationIntegrationSettingsValidationError(
            "organization.displayName must be at least 2 characters"
        )
    return candidate


def _validate_contact_email(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    if not candidate:
        return None
    if not _EMAIL_PATTERN.fullmatch(candidate):
        raise OrganizationIntegrationSettingsValidationError("organization.contactEmail must be a valid email address")
    return candidate


def _validate_slug(value: Any, *, fallback_display_name: str) -> str:
    candidate = str(
        fallback_display_name if value is None else value
    ).strip().lower()
    slug_value = re.sub(r"[^a-z0-9]+", "-", candidate).strip("-")
    if len(slug_value) < 2:
        raise OrganizationIntegrationSettingsValidationError(
            "organization.slug must contain at least 2 alphanumeric characters"
        )
    return slug_value


def _latest_updated_at(*values: str | None) -> str | None:
    candidates = [str(value).strip() for value in values if str(value or "").strip()]
    if not candidates:
        return None
    return max(candidates)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _profile_changed_fields(
    *,
    current: OrganizationRecord,
    update: OrganizationProfileUpdate,
) -> list[str]:
    changed: list[str] = []
    if current.name != update.display_name:
        changed.append("display_name")
    if current.slug != update.slug:
        changed.append("slug")
    if current.contact_email != update.contact_email:
        changed.append("contact_email")
    return changed


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

