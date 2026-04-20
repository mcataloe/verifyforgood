from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


from verification_platform.customer_accounts import (  # noqa: E402
    SupportTicketEmailRequest,
    build_support_ticket_email_delivery,
    load_support_ticket_email_config,
)
from verification_platform.customer_accounts.support_tickets import (  # noqa: E402
    GmailSmtpSupportTicketEmailDelivery,
)


def test_load_support_ticket_email_config_defaults_disabled():
    config = load_support_ticket_email_config({})

    assert config.enabled is False
    assert config.provider == "gmail_smtp"


def test_load_support_ticket_email_config_requires_required_values_when_enabled():
    try:
        load_support_ticket_email_config({"SUPPORT_TICKET_EMAIL_ENABLED": "true"})
    except ValueError as exc:
        assert str(exc) == "SUPPORT_TICKET_EMAIL_TO is required when SUPPORT_TICKET_EMAIL_ENABLED=true"
    else:
        assert False, "Expected support ticket email config validation error"


def test_build_support_ticket_email_delivery_returns_none_when_disabled():
    assert build_support_ticket_email_delivery({}) is None


def test_gmail_smtp_support_delivery_builds_message_and_sends(monkeypatch):
    captured: dict[str, object] = {}

    class _FakeSmtp:
        def __init__(self, host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, username, password):
            captured["username"] = username
            captured["password"] = password

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr("verification_platform.customer_accounts.support_tickets.smtplib.SMTP", _FakeSmtp)

    delivery = build_support_ticket_email_delivery(
        {
            "SUPPORT_TICKET_EMAIL_ENABLED": "true",
            "SUPPORT_TICKET_EMAIL_PROVIDER": "gmail_smtp",
            "SUPPORT_TICKET_EMAIL_TO": "support@example.com",
            "SUPPORT_TICKET_EMAIL_FROM": "sender@example.com",
            "SUPPORT_TICKET_SMTP_HOST": "smtp.gmail.com",
            "SUPPORT_TICKET_SMTP_PORT": "587",
            "SUPPORT_TICKET_SMTP_USERNAME": "sender@example.com",
            "SUPPORT_TICKET_SMTP_APP_PASSWORD": "app-password",
            "SUPPORT_TICKET_SMTP_STARTTLS": "true",
            "SUPPORT_TICKET_SMTP_TIMEOUT_SECONDS": "15",
        }
    )

    assert isinstance(delivery, GmailSmtpSupportTicketEmailDelivery)
    result = delivery.send(
        SupportTicketEmailRequest(
            support_request_id="support_req_123",
            organization_id="org_1",
            organization_name="Portal Test Org",
            actor_user_id="101",
            account_id="acct_1",
            workspace_id="ws_1",
            current_plan="growth",
            membership_role="admin",
            category="recommendation",
            subject="Token issue",
            description="The API token request is failing with a 401 response.",
            reply_email="submitter@example.org",
            watchers=("ops@example.org", "reviewer@example.org"),
            route_hash="#/settings?nav=customer-admin-settings",
            user_agent="Portal Browser",
            support_email="support@verifyforgood.com",
            submitted_at="2026-04-20T00:00:00+00:00",
        )
    )

    message = captured["message"]
    assert captured["host"] == "smtp.gmail.com"
    assert captured["port"] == 587
    assert captured["timeout"] == 15
    assert captured["starttls"] is True
    assert captured["username"] == "sender@example.com"
    assert captured["password"] == "app-password"
    assert message["To"] == "support@example.com"
    assert message["From"] == "sender@example.com"
    assert message["Reply-To"] == "submitter@example.org"
    assert message["Cc"] == "ops@example.org, reviewer@example.org"
    assert "The API token request is failing with a 401 response." in message.get_content()
    assert result.delivery_recipient == "support@example.com"
    assert result.provider_message_id is not None
