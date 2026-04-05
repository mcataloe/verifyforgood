from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from charity_status.auth import build_api_key_record

from .audit_logging import AuditEventType, AuditLogService
from .identity_models import ApiKeyRecord, ApiKeyStatus, MembershipRole, MembershipStatus
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


@dataclass(frozen=True)
class ApiKeyResponse:
    key_id: int | str
    organization_id: int | str
    display_name: str
    created_at: str
    created_by_user_id: int | str
    status: str
    last_used_at: str | None

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "key_id": self.key_id,
            "organization_id": self.organization_id,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "created_by_user_id": self.created_by_user_id,
            "status": self.status,
            "last_used_at": self.last_used_at,
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
                created_at=created_at,
                created_by_user_id=actor_user_id,
                status=ApiKeyStatus.ACTIVE,
                last_used_at=None,
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
                    "status": persisted.status.value,
                },
            )

        return ApiKeyCreateResponse(api_key=_to_response(persisted), secret=plaintext)

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
        created_at=record.created_at,
        created_by_user_id=record.created_by_user_id,
        status=record.status.value,
        last_used_at=record.last_used_at,
    )


def _validate_display_name(value: str) -> str:
    candidate = str(value or "").strip()
    if len(candidate) < 2:
        raise ApiKeyManagementError("display_name must be at least 2 characters")
    return candidate


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
