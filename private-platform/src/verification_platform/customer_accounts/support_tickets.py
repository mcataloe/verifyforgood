from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid
from enum import Enum
from typing import Mapping, Protocol


class SupportDeliveryMode(str, Enum):
    RECORDED_ONLY = "recorded_only"
    RECORDED_AND_EMAILED = "recorded_and_emailed"


class SupportTicketDeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class SupportIssueReporting:
    delivery_mode: SupportDeliveryMode
    honesty_notice: str
    urgent_contact_notice: str

    def to_dict(self) -> dict[str, str]:
        return {
            "delivery_mode": self.delivery_mode.value,
            "honesty_notice": self.honesty_notice,
            "urgent_contact_notice": self.urgent_contact_notice,
        }


@dataclass(frozen=True)
class SupportTicketRecord:
    ticket_id: int | None
    support_request_id: str
    organization_id: int | str
    actor_user_id: int | str | None
    account_id: str | None
    workspace_id: str | None
    category: str
    subject: str
    description: str
    reply_email: str | None
    watchers: tuple[str, ...]
    route_hash: str | None
    user_agent: str | None
    current_plan: str | None
    membership_role: str | None
    delivery_mode: SupportDeliveryMode
    delivery_provider: str
    delivery_status: SupportTicketDeliveryStatus
    delivery_recipient: str
    provider_message_id: str | None
    delivery_error: str | None
    created_at: str
    emailed_at: str | None = None


class SupportTicketRepository(Protocol):
    def create(self, record: SupportTicketRecord) -> SupportTicketRecord:
        ...

    def mark_sent(
        self,
        support_request_id: str,
        *,
        provider_message_id: str | None,
        delivery_recipient: str,
        emailed_at: str,
    ) -> SupportTicketRecord | None:
        ...

    def mark_failed(
        self,
        support_request_id: str,
        *,
        delivery_error: str,
    ) -> SupportTicketRecord | None:
        ...

    def get_by_support_request_id(
        self,
        support_request_id: str,
    ) -> SupportTicketRecord | None:
        ...


@dataclass(frozen=True)
class SupportTicketEmailRequest:
    support_request_id: str
    organization_id: str
    organization_name: str
    actor_user_id: str | None
    account_id: str | None
    workspace_id: str | None
    current_plan: str | None
    membership_role: str | None
    category: str
    subject: str
    description: str
    reply_email: str | None
    watchers: tuple[str, ...]
    route_hash: str | None
    user_agent: str | None
    support_email: str
    submitted_at: str


@dataclass(frozen=True)
class SupportTicketEmailResult:
    provider_name: str
    provider_message_id: str | None
    delivery_recipient: str


class SupportTicketEmailDelivery(Protocol):
    @property
    def provider_name(self) -> str:
        ...

    @property
    def delivery_mode(self) -> SupportDeliveryMode:
        ...

    @property
    def delivery_recipient(self) -> str:
        ...

    def send(self, request: SupportTicketEmailRequest) -> SupportTicketEmailResult:
        ...


@dataclass(frozen=True)
class SupportTicketEmailConfig:
    enabled: bool = False
    provider: str = "gmail_smtp"
    to: str = ""
    from_email: str = ""
    subject_prefix: str = "[Verification Support]"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_app_password: str = ""
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = 15


def load_support_ticket_email_config(
    env: Mapping[str, str] | None = None,
) -> SupportTicketEmailConfig:
    source = env if env is not None else os.environ
    enabled = _mapping_bool(source, "SUPPORT_TICKET_EMAIL_ENABLED", False)
    provider = _mapping_text(source, "SUPPORT_TICKET_EMAIL_PROVIDER", "gmail_smtp") or "gmail_smtp"
    config = SupportTicketEmailConfig(
        enabled=enabled,
        provider=provider,
        to=_mapping_text(source, "SUPPORT_TICKET_EMAIL_TO"),
        from_email=_mapping_text(source, "SUPPORT_TICKET_EMAIL_FROM"),
        subject_prefix=_mapping_text(source, "SUPPORT_TICKET_EMAIL_SUBJECT_PREFIX", "[Verification Support]")
        or "[Verification Support]",
        smtp_host=_mapping_text(source, "SUPPORT_TICKET_SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com",
        smtp_port=_mapping_int(source, "SUPPORT_TICKET_SMTP_PORT", 587),
        smtp_username=_mapping_text(source, "SUPPORT_TICKET_SMTP_USERNAME"),
        smtp_app_password=_mapping_text(source, "SUPPORT_TICKET_SMTP_APP_PASSWORD"),
        smtp_starttls=_mapping_bool(source, "SUPPORT_TICKET_SMTP_STARTTLS", True),
        smtp_timeout_seconds=_mapping_int(source, "SUPPORT_TICKET_SMTP_TIMEOUT_SECONDS", 15),
    )
    if not config.enabled:
        return config
    if config.provider != "gmail_smtp":
        raise ValueError("SUPPORT_TICKET_EMAIL_PROVIDER must be gmail_smtp when support ticket email is enabled")
    for key, value in (
        ("SUPPORT_TICKET_EMAIL_TO", config.to),
        ("SUPPORT_TICKET_EMAIL_FROM", config.from_email),
        ("SUPPORT_TICKET_SMTP_HOST", config.smtp_host),
        ("SUPPORT_TICKET_SMTP_USERNAME", config.smtp_username),
        ("SUPPORT_TICKET_SMTP_APP_PASSWORD", config.smtp_app_password),
    ):
        if not str(value or "").strip():
            raise ValueError(f"{key} is required when SUPPORT_TICKET_EMAIL_ENABLED=true")
    if not _looks_like_email(config.to):
        raise ValueError("SUPPORT_TICKET_EMAIL_TO must be a valid email address when SUPPORT_TICKET_EMAIL_ENABLED=true")
    if not _looks_like_email(config.from_email):
        raise ValueError("SUPPORT_TICKET_EMAIL_FROM must be a valid email address when SUPPORT_TICKET_EMAIL_ENABLED=true")
    if not _looks_like_email(config.smtp_username):
        raise ValueError("SUPPORT_TICKET_SMTP_USERNAME must be a valid email address when SUPPORT_TICKET_EMAIL_ENABLED=true")
    if int(config.smtp_port) < 1:
        raise ValueError("SUPPORT_TICKET_SMTP_PORT must be at least 1 when SUPPORT_TICKET_EMAIL_ENABLED=true")
    if int(config.smtp_timeout_seconds) < 1:
        raise ValueError("SUPPORT_TICKET_SMTP_TIMEOUT_SECONDS must be at least 1 when SUPPORT_TICKET_EMAIL_ENABLED=true")
    return config


def build_support_ticket_email_delivery(
    env: Mapping[str, str] | None = None,
    *,
    config: SupportTicketEmailConfig | None = None,
) -> SupportTicketEmailDelivery | None:
    resolved = config or load_support_ticket_email_config(env)
    if not resolved.enabled:
        return None
    return GmailSmtpSupportTicketEmailDelivery(resolved)


class GmailSmtpSupportTicketEmailDelivery:
    def __init__(self, config: SupportTicketEmailConfig) -> None:
        self._config = config

    @property
    def provider_name(self) -> str:
        return self._config.provider

    @property
    def delivery_mode(self) -> SupportDeliveryMode:
        return SupportDeliveryMode.RECORDED_AND_EMAILED

    @property
    def delivery_recipient(self) -> str:
        return self._config.to

    def send(self, request: SupportTicketEmailRequest) -> SupportTicketEmailResult:
        message = self._build_message(request)
        with smtplib.SMTP(
            self._config.smtp_host,
            self._config.smtp_port,
            timeout=self._config.smtp_timeout_seconds,
        ) as client:
            if self._config.smtp_starttls:
                client.starttls()
            client.login(self._config.smtp_username, self._config.smtp_app_password)
            client.send_message(message)
        return SupportTicketEmailResult(
            provider_name=self.provider_name,
            provider_message_id=str(message.get("Message-Id") or "").strip() or None,
            delivery_recipient=self.delivery_recipient,
        )

    def _build_message(self, request: SupportTicketEmailRequest) -> EmailMessage:
        message = EmailMessage()
        message["To"] = self._config.to
        message["From"] = self._config.from_email
        message["Subject"] = (
            f"{self._config.subject_prefix} [{request.category}] {request.subject}"
        ).strip()
        message["Message-Id"] = make_msgid(domain=_message_id_domain(self._config.from_email))
        if request.reply_email:
            message["Reply-To"] = request.reply_email
        if request.watchers:
            message["Cc"] = ", ".join(request.watchers)
        message.set_content(_render_support_ticket_email_body(request))
        return message


def _render_support_ticket_email_body(request: SupportTicketEmailRequest) -> str:
    watcher_text = ", ".join(request.watchers) if request.watchers else "(none)"
    return "\n".join(
        [
            "A new support ticket was submitted.",
            "",
            f"Support request ID: {request.support_request_id}",
            f"Submitted at: {request.submitted_at}",
            f"Category: {request.category}",
            f"Subject: {request.subject}",
            "",
            "Organization context:",
            f"- Organization name: {request.organization_name}",
            f"- Organization ID: {request.organization_id}",
            f"- Account ID: {request.account_id or '(none)'}",
            f"- Workspace ID: {request.workspace_id or '(none)'}",
            f"- Current plan: {request.current_plan or '(none)'}",
            f"- Membership role: {request.membership_role or '(none)'}",
            "",
            "Submitter context:",
            f"- Actor user ID: {request.actor_user_id or '(none)'}",
            f"- Reply email: {request.reply_email or '(none)'}",
            f"- Watchers: {watcher_text}",
            f"- Route hash: {request.route_hash or '(none)'}",
            f"- User agent: {request.user_agent or '(none)'}",
            "",
            "Customer-facing support contact:",
            f"- Support email: {request.support_email}",
            "",
            "Description:",
            request.description,
        ]
    )


def _mapping_text(source: Mapping[str, str], key: str, default: str = "") -> str:
    return str(source.get(key, default) or default).strip()


def _mapping_bool(source: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = source.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _mapping_int(source: Mapping[str, str], key: str, default: int) -> int:
    raw = _mapping_text(source, key)
    return default if raw == "" else int(raw)


def _looks_like_email(value: str) -> bool:
    candidate = str(value or "").strip()
    if "@" not in candidate or candidate.startswith("@") or candidate.endswith("@"):
        return False
    local, domain = candidate.split("@", 1)
    return "." in domain and bool(local.strip()) and bool(domain.strip())


def _message_id_domain(value: str) -> str:
    candidate = str(value or "").strip()
    if "@" in candidate:
        return candidate.split("@", 1)[1].strip() or "localhost"
    return "localhost"


__all__ = [
    "GmailSmtpSupportTicketEmailDelivery",
    "SupportDeliveryMode",
    "SupportIssueReporting",
    "SupportTicketDeliveryStatus",
    "SupportTicketEmailConfig",
    "SupportTicketEmailDelivery",
    "SupportTicketEmailRequest",
    "SupportTicketEmailResult",
    "SupportTicketRecord",
    "SupportTicketRepository",
    "build_support_ticket_email_delivery",
    "load_support_ticket_email_config",
]
