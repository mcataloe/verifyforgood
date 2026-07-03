from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from datetime import date, datetime, timezone

from verification.backend.shared.auth import build_api_key_record

from .audit_logging import AuditEventType, AuditLogService
from .identity_models import (
    ApiKeyPermissionLevel,
    ApiKeyRecord,
    ApiKeyStatus,
    MembershipRole,
    MembershipStatus,
)
from .identity_repositories import ApiKeyRepository, MembershipRepository, OrganizationRepository

DEFAULT_ORG_API_KEY_PLAN = "free"
DEFAULT_ORG_API_KEY_SCOPES = (
    "verify:read",
    "verify:write",
    "nonprofits:read",
    "sources:read",
    "compliance:read",
    "federal_awards:read",
)


class ApiKeyManagementError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class ApiKeyCreateRequest:
    display_name: str
    description: str = ""
    permission_level: str = ApiKeyPermissionLevel.FULL_ACCESS.value
    expires_at: str | None = None
    allowed_cidr: str | None = None


@dataclass(frozen=True)
class ApiKeyUpdateRequest:
    display_name: str
    description: str = ""


@dataclass(frozen=True)
class ApiKeyResponse:
    key_id: int | str
    organization_id: int | str
    display_name: str
    description: str
    created_at: str
    created_by_user_id: int | str
    status: str
    last_used_at: str | None
    permission_level: str
    expires_at: str | None
    allowed_cidr: str | None

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "key_id": self.key_id,
            "organization_id": self.organization_id,
            "display_name": self.display_name,
            "description": self.description,
            "created_at": self.created_at,
            "created_by_user_id": self.created_by_user_id,
            "status": self.status,
            "last_used_at": self.last_used_at,
            "permission_level": self.permission_level,
            "expires_at": self.expires_at,
            "allowed_cidr": self.allowed_cidr,
        }


@dataclass(frozen=True)
class ApiKeyCreateResponse:
    api_key: ApiKeyResponse
    secret: str

    def to_dict(self) -> dict[str, object]:
        return {"api_key": self.api_key.to_dict(), "secret": self.secret}


class ApiKeyService:
    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        memberships: MembershipRepository,
        api_keys: ApiKeyRepository,
        audit_log_service: AuditLogService | None = None,
    ) -> None:
        self._organizations = organizations
        self._memberships = memberships
        self._api_keys = api_keys
        self._audit_log_service = audit_log_service

    def list_keys(self, *, organization_id: str, actor_user_id: str) -> list[ApiKeyResponse]:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        return [_to_response(item) for item in self._api_keys.list_for_organization(organization_id)]

    def create_key(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        request: ApiKeyCreateRequest,
    ) -> ApiKeyCreateResponse:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        display_name = _validate_display_name(request.display_name)
        description = _validate_description(request.description)
        permission_level = _validate_permission_level(request.permission_level)
        expires_at = _validate_expires_at(request.expires_at)
        allowed_cidr = _validate_allowed_cidr(request.allowed_cidr)
        created_at = _utc_now()

        plaintext, stored = build_api_key_record(
            key_id="pending",
            secret=None,
            account_id=str(organization_id),
            workspace_id=str(organization_id),
            scopes=list(DEFAULT_ORG_API_KEY_SCOPES),
            plan_id=DEFAULT_ORG_API_KEY_PLAN,
            rate_limit_profile=DEFAULT_ORG_API_KEY_PLAN,
        )
        persisted = self._api_keys.create(
            ApiKeyRecord(
                key_id=None,
                organization_id=organization_id,
                hashed_key_value=stored.secret_hash,
                display_name=display_name,
                description=description,
                created_at=created_at,
                created_by_user_id=actor_user_id,
                status=ApiKeyStatus.ACTIVE,
                last_used_at=None,
                permission_level=permission_level,
                expires_at=expires_at,
                allowed_cidr=allowed_cidr,
            )
        )
        plaintext = f"csk_{persisted.key_id}.{plaintext.split('.', 1)[1]}"

        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.API_KEY_CREATION,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                metadata={
                    "key_id": persisted.key_id,
                    "display_name": persisted.display_name,
                    "description": persisted.description,
                    "status": persisted.status.value,
                    "permission_level": persisted.permission_level.value,
                    "expires_at": persisted.expires_at,
                    "allowed_cidr": persisted.allowed_cidr,
                },
            )

        return ApiKeyCreateResponse(api_key=_to_response(persisted), secret=plaintext)

    def update_key(
        self,
        *,
        organization_id: int | str,
        actor_user_id: int | str,
        key_id: int | str,
        request: ApiKeyUpdateRequest,
    ) -> ApiKeyResponse:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        updated = self._api_keys.update_metadata(
            organization_id,
            key_id,
            display_name=_validate_display_name(request.display_name),
            description=_validate_description(request.description),
        )
        if updated is None:
            raise ApiKeyManagementError("API key was not found in the current organization")

        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.ORGANIZATION_SETTINGS_UPDATE,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                metadata={
                    "changed_fields": ["api_key_display_name", "api_key_description"],
                    "changed_sections": ["api_keys"],
                    "display_name": updated.display_name,
                    "description": updated.description,
                    "key_id": updated.key_id,
                },
            )

        return _to_response(updated)

    def revoke_key(self, *, organization_id: int | str, actor_user_id: int | str, key_id: int | str) -> ApiKeyResponse:
        self._require_admin(organization_id=organization_id, user_id=actor_user_id)
        revoked = self._api_keys.revoke(organization_id, key_id, revoked_at=_utc_now())
        if revoked is None:
            raise ApiKeyManagementError("API key was not found in the current organization")

        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.API_KEY_REVOCATION,
                actor_user_id=actor_user_id,
                organization_id=organization_id,
                target_user_id=None,
                metadata={
                    "key_id": revoked.key_id,
                    "display_name": revoked.display_name,
                    "status": revoked.status.value,
                },
            )

        return _to_response(revoked)

    def _require_admin(self, *, organization_id: int | str, user_id: int | str) -> None:
        if self._organizations.get(organization_id) is None:
            raise ApiKeyManagementError("Current organization was not found")
        membership = self._memberships.get(organization_id, user_id)
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise ApiKeyManagementError("Active membership is required for this organization")
        if membership.role != MembershipRole.ADMIN:
            raise ApiKeyManagementError("Only organization admins may manage API keys")


def _to_response(record: ApiKeyRecord) -> ApiKeyResponse:
    return ApiKeyResponse(
        key_id=record.key_id,
        organization_id=record.organization_id,
        display_name=record.display_name,
        description=record.description,
        created_at=record.created_at,
        created_by_user_id=record.created_by_user_id,
        status=record.status.value,
        last_used_at=record.last_used_at,
        permission_level=record.permission_level.value,
        expires_at=record.expires_at,
        allowed_cidr=record.allowed_cidr,
    )


def _validate_display_name(value: str) -> str:
    candidate = str(value or "").strip()
    if len(candidate) < 2:
        raise ApiKeyManagementError("display_name must be at least 2 characters")
    return candidate


def _validate_description(value: str) -> str:
    candidate = str(value or "").strip()
    if len(candidate) > 500:
        raise ApiKeyManagementError("description must be 500 characters or fewer")
    return candidate


def _validate_permission_level(value: str | None) -> ApiKeyPermissionLevel:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return ApiKeyPermissionLevel.FULL_ACCESS
    try:
        return ApiKeyPermissionLevel(candidate)
    except ValueError as exc:
        allowed = ", ".join(level.value for level in ApiKeyPermissionLevel)
        raise ApiKeyManagementError(f"permission_level must be one of: {allowed}") from exc


def _validate_expires_at(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    try:
        parsed_date = date.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ApiKeyManagementError("expires_at must be an ISO-8601 date") from exc
    else:
        parsed = datetime(
            parsed_date.year, parsed_date.month, parsed_date.day, 23, 59, 59, tzinfo=timezone.utc
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed <= datetime.now(timezone.utc):
        raise ApiKeyManagementError("expires_at must be in the future")
    return parsed.replace(microsecond=0).isoformat()


def _validate_allowed_cidr(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    try:
        network = ipaddress.ip_network(candidate, strict=False)
    except ValueError as exc:
        raise ApiKeyManagementError("allowed_cidr must be valid CIDR notation") from exc
    return str(network)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

