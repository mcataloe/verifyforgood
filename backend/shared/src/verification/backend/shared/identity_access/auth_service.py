from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

try:
    import bcrypt
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in minimal envs
    bcrypt = None

from verification.backend.shared.auth import AuthenticationError
from verification.backend.shared.customer_accounts.audit_logging import AuditEventType, AuditLogService
from verification.backend.shared.customer_accounts.identity_models import IdentityProviderType, UserRecord
from verification.backend.shared.customer_accounts.identity_repositories import DuplicateUserEmailError, UserRepository


class PortalAuthValidationError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class UserCreateRequest:
    email: str
    password: str
    full_name: str | None = None


@dataclass(frozen=True)
class UserLoginRequest:
    email: str
    password: str


@dataclass(frozen=True)
class UserResponse:
    user_id: str
    email: str
    full_name: str | None
    created_at: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class AuthenticatedUserSession:
    user: UserResponse
    access_token: str
    token_type: str = "Bearer"

    def to_dict(self) -> dict[str, object]:
        return {
            "user": self.user.to_dict(),
            "access_token": self.access_token,
            "token_type": self.token_type,
        }


class PasswordHasher(Protocol):
    def hash_password(self, password: str) -> str:
        ...

    def verify_password(self, password: str, stored_hash: str) -> bool:
        ...


class BearerTokenCodec(Protocol):
    def issue_token(self, user: UserRecord) -> str:
        ...

    def decode_token(self, token: str) -> str:
        ...


@dataclass(frozen=True)
class ProvisionedIdentity:
    identity_provider_type: IdentityProviderType
    password_hash: str | None = None
    external_subject_id: str | None = None


class IdentityProviderService(Protocol):
    identity_provider_type: IdentityProviderType

    def provision_identity(self, *, password: str | None = None, external_subject_id: str | None = None) -> ProvisionedIdentity:
        ...

    def authenticate(self, *, user: UserRecord, password: str | None = None) -> bool:
        ...


class BcryptPasswordHasher:
    def hash_password(self, password: str) -> str:
        encoded = _validate_password(password).encode("utf-8")
        if bcrypt is None:
            salt = secrets.token_bytes(16)
            derived = hashlib.pbkdf2_hmac("sha256", encoded, salt, 600_000)
            return f"pbkdf2_sha256${_b64url_encode(salt)}${_b64url_encode(derived)}"
        return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")

    def verify_password(self, password: str, stored_hash: str) -> bool:
        if bcrypt is None:
            try:
                scheme, encoded_salt, encoded_hash = str(stored_hash or "").split("$", 2)
            except ValueError:
                return False
            if scheme != "pbkdf2_sha256":
                return False
            expected = hashlib.pbkdf2_hmac(
                "sha256",
                str(password or "").encode("utf-8"),
                _b64url_decode(encoded_salt),
                600_000,
            )
            return hmac.compare_digest(_b64url_encode(expected), encoded_hash)
        return bcrypt.checkpw(str(password or "").encode("utf-8"), stored_hash.encode("utf-8"))


class LocalPasswordIdentityProviderService:
    identity_provider_type = IdentityProviderType.LOCAL_PASSWORD

    def __init__(self, password_hasher: PasswordHasher) -> None:
        self._password_hasher = password_hasher

    def provision_identity(self, *, password: str | None = None, external_subject_id: str | None = None) -> ProvisionedIdentity:
        if external_subject_id is not None:
            raise PortalAuthValidationError("external_subject_id is not supported for local password identities")
        return ProvisionedIdentity(
            identity_provider_type=self.identity_provider_type,
            password_hash=self._password_hasher.hash_password(str(password or "")),
            external_subject_id=None,
        )

    def authenticate(self, *, user: UserRecord, password: str | None = None) -> bool:
        if user.identity_provider_type is not IdentityProviderType.LOCAL_PASSWORD:
            return False
        if not user.password_hash:
            return False
        return self._password_hasher.verify_password(str(password or ""), user.password_hash)


class HmacBearerTokenCodec:
    def __init__(self, secret: str, token_ttl_seconds: int = 86400) -> None:
        normalized_secret = str(secret or "").strip()
        if not normalized_secret:
            raise ValueError("Auth token secret is required")
        self._secret = normalized_secret.encode("utf-8")
        self._token_ttl_seconds = max(60, int(token_ttl_seconds))

    def issue_token(self, user: UserRecord) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._token_ttl_seconds)
        payload = {
            "sub": user.user_id,
            "email": user.normalized_email,
            "exp": int(expires_at.timestamp()),
        }
        encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = hmac.new(self._secret, encoded_payload.encode("utf-8"), hashlib.sha256).digest()
        return f"{encoded_payload}.{_b64url_encode(signature)}"

    def decode_token(self, token: str) -> str:
        encoded_payload, encoded_signature = _split_token(token)
        expected = _b64url_encode(hmac.new(self._secret, encoded_payload.encode("utf-8"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, encoded_signature):
            raise AuthenticationError("Invalid bearer token")
        try:
            payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationError("Invalid bearer token") from exc
        expiry = int(payload.get("exp") or 0)
        if expiry <= int(datetime.now(timezone.utc).timestamp()):
            raise AuthenticationError("Bearer token expired")
        user_id = str(payload.get("sub") or "").strip()
        if not user_id:
            raise AuthenticationError("Invalid bearer token")
        return user_id


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        token_codec: BearerTokenCodec,
        audit_log_service: AuditLogService | None = None,
        identity_provider_services: tuple[IdentityProviderService, ...] | None = None,
    ) -> None:
        self._users = users
        self._token_codec = token_codec
        self._audit_log_service = audit_log_service
        default_local_provider = LocalPasswordIdentityProviderService(password_hasher)
        configured = identity_provider_services or (default_local_provider,)
        self._identity_providers = {provider.identity_provider_type: provider for provider in configured}
        self._local_password_provider = self._identity_providers.get(IdentityProviderType.LOCAL_PASSWORD)
        if self._local_password_provider is None:
            self._local_password_provider = default_local_provider
            self._identity_providers[IdentityProviderType.LOCAL_PASSWORD] = default_local_provider

    def register_user(self, request: UserCreateRequest) -> AuthenticatedUserSession:
        normalized_email = _validate_email(request.email)
        created_at = _utc_now()
        provisioned = self._local_password_provider.provision_identity(password=request.password)
        user = UserRecord(
            user_id=f"user_{secrets.token_hex(16)}",
            email=normalized_email,
            normalized_email=normalized_email,
            full_name=_optional_name(request.full_name),
            created_at=created_at,
            updated_at=created_at,
            password_hash=provisioned.password_hash,
            identity_provider_type=provisioned.identity_provider_type,
            external_subject_id=provisioned.external_subject_id,
        )
        try:
            persisted = self._users.create(user)
        except DuplicateUserEmailError:
            raise PortalAuthValidationError("Email is already registered") from None
        if self._audit_log_service is not None:
            self._audit_log_service.record_event(
                event_type=AuditEventType.USER_REGISTRATION,
                actor_user_id=persisted.user_id,
                organization_id=None,
                target_user_id=persisted.user_id,
                metadata={
                    "email": persisted.email,
                    "full_name": persisted.full_name,
                },
                timestamp=created_at,
            )
        return self._session_for_user(persisted)

    def login_user(self, request: UserLoginRequest) -> AuthenticatedUserSession:
        normalized_email = _validate_email(request.email)
        _validate_password(request.password)
        user = self._users.get_by_email(normalized_email)
        if user is None:
            raise AuthenticationError("Invalid email or password")
        provider = self._identity_providers.get(user.identity_provider_type)
        if provider is None:
            raise AuthenticationError("Invalid email or password")
        if not provider.authenticate(user=user, password=request.password):
            raise AuthenticationError("Invalid email or password")
        return self._session_for_user(user)

    def get_current_user(self, authorization_header: str) -> UserResponse:
        token = _extract_bearer_token(authorization_header)
        user_id = self._token_codec.decode_token(token)
        user = self._users.get(user_id)
        if user is None:
            raise AuthenticationError("Authenticated user was not found")
        return _to_user_response(user)

    def _session_for_user(self, user: UserRecord) -> AuthenticatedUserSession:
        return AuthenticatedUserSession(
            user=_to_user_response(user),
            access_token=self._token_codec.issue_token(user),
        )


def _to_user_response(user: UserRecord) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
    )


def _validate_email(email: str) -> str:
    normalized = str(email or "").strip().lower()
    if not normalized or "@" not in normalized:
        raise PortalAuthValidationError("email must be a valid email address")
    return normalized


def _validate_password(password: str) -> str:
    candidate = str(password or "")
    if len(candidate.strip()) < 8:
        raise PortalAuthValidationError("password must be at least 8 characters")
    return candidate


def _optional_name(full_name: str | None) -> str | None:
    candidate = str(full_name or "").strip()
    return candidate or None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _extract_bearer_token(header_value: str) -> str:
    value = str(header_value or "").strip()
    if not value.lower().startswith("bearer "):
        raise AuthenticationError("Missing bearer token")
    token = value[7:].strip()
    if not token:
        raise AuthenticationError("Missing bearer token")
    return token


def _split_token(token: str) -> tuple[str, str]:
    parts = str(token or "").split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise AuthenticationError("Invalid bearer token")
    return parts[0], parts[1]


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")

