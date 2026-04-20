from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


from verification_platform.customer_accounts import (  # noqa: E402
    AuditEventType,
    DynamoAuditLogRepository,
    DynamoOrganizationRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    OrganizationRecord,
    OrganizationSupportError,
    OrganizationSupportService,
    SupportDeliveryMode,
    SupportTicketDeliveryStatus,
    SupportTicketEmailRequest,
    SupportTicketEmailResult,
    SupportTicketRecord,
)


class _InMemorySupportTicketRepository:
    def __init__(self) -> None:
        self._records: dict[str, SupportTicketRecord] = {}
        self._next_id = 1

    def create(self, record: SupportTicketRecord) -> SupportTicketRecord:
        created = SupportTicketRecord(
            **{
                **record.__dict__,
                "ticket_id": self._next_id,
            }
        )
        self._records[created.support_request_id] = created
        self._next_id += 1
        return created

    def mark_sent(
        self,
        support_request_id: str,
        *,
        provider_message_id: str | None,
        delivery_recipient: str,
        emailed_at: str,
    ) -> SupportTicketRecord | None:
        record = self._records.get(support_request_id)
        if record is None:
            return None
        updated = SupportTicketRecord(
            **{
                **record.__dict__,
                "delivery_status": SupportTicketDeliveryStatus.SENT,
                "delivery_recipient": delivery_recipient,
                "provider_message_id": provider_message_id,
                "delivery_error": None,
                "emailed_at": emailed_at,
            }
        )
        self._records[support_request_id] = updated
        return updated

    def mark_failed(
        self,
        support_request_id: str,
        *,
        delivery_error: str,
    ) -> SupportTicketRecord | None:
        record = self._records.get(support_request_id)
        if record is None:
            return None
        updated = SupportTicketRecord(
            **{
                **record.__dict__,
                "delivery_status": SupportTicketDeliveryStatus.FAILED,
                "delivery_error": delivery_error,
            }
        )
        self._records[support_request_id] = updated
        return updated

    def get_by_support_request_id(self, support_request_id: str) -> SupportTicketRecord | None:
        return self._records.get(support_request_id)


class _RecordingEmailDelivery:
    provider_name = "gmail_smtp"
    delivery_mode = SupportDeliveryMode.RECORDED_AND_EMAILED
    delivery_recipient = "support@example.com"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[SupportTicketEmailRequest] = []

    def send(self, request: SupportTicketEmailRequest) -> SupportTicketEmailResult:
        self.requests.append(request)
        if self.fail:
            raise RuntimeError("smtp send failed")
        return SupportTicketEmailResult(
            provider_name=self.provider_name,
            provider_message_id="message-123",
            delivery_recipient=self.delivery_recipient,
        )


def _service(*, email_enabled: bool = False, fail_email: bool = False):
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=resource)
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Portal Test Org",
            slug="portal-test-org",
            created_at="2026-03-29T00:00:00+00:00",
            updated_at="2026-03-29T00:00:00+00:00",
            contact_email="ops@example.org",
        )
    )
    audits = DynamoAuditLogRepository(dynamodb_resource=resource)
    tickets = _InMemorySupportTicketRepository() if email_enabled else None
    email_delivery = _RecordingEmailDelivery(fail=fail_email) if email_enabled else None
    return (
        OrganizationSupportService(
            organizations=organizations,
            audits=audits,
            support_tickets=tickets,
            email_delivery=email_delivery,
        ),
        audits,
        tickets,
        email_delivery,
    )


def test_get_support_context_returns_org_scoped_contact_and_links():
    service, _audits, _tickets, _email_delivery = _service()

    context = service.get_support_context(
        organization_id="org_1",
        account_id="acct_1",
        workspace_id="ws_1",
        current_plan="growth",
        membership_role="admin",
    )

    payload = context.to_dict()
    assert payload["support_contact"]["support_email"] == "support@verifyforgood.com"
    assert payload["account_context"]["organization_name"] == "Portal Test Org"
    assert payload["account_context"]["account_id"] == "acct_1"
    assert payload["account_context"]["workspace_id"] == "ws_1"
    assert payload["account_context"]["current_plan"] == "growth"
    assert payload["product_links"]["api_access_hash"] == "#/api-access?nav=customer-admin-api"
    assert payload["issue_reporting"]["delivery_mode"] == SupportDeliveryMode.RECORDED_ONLY.value


def test_submit_support_request_records_sanitized_audit_event():
    service, audits, _tickets, _email_delivery = _service()

    receipt = service.submit_support_request(
        organization_id="org_1",
        account_id="acct_1",
        workspace_id="ws_1",
        actor_user_id="user_admin",
        current_plan="growth",
        membership_role="admin",
        payload={
            "category": "recommendation",
            "subject": "Token issue",
            "description": "The API token request is failing with a 401 response.",
            "watchers": ["ops@example.org", "reviewer@example.org"],
            "context": {
                "current_route_hash": "#/settings?nav=customer-admin-settings",
                "user_agent": "Portal Browser",
            },
        },
    )

    items = audits.list_for_organization("org_1")

    assert receipt.status == "received"
    assert receipt.delivery_mode is SupportDeliveryMode.RECORDED_ONLY
    assert len(items) == 1
    assert items[0].event_type is AuditEventType.SUPPORT_REQUEST_SUBMITTED
    assert items[0].metadata["category"] == "recommendation"
    assert items[0].metadata["subject"] == "Token issue"
    assert items[0].metadata["reply_email"] is None
    assert items[0].metadata["watchers"] == [
        "ops@example.org",
        "reviewer@example.org",
    ]
    assert items[0].metadata["route_hash"] == "#/settings?nav=customer-admin-settings"
    assert items[0].metadata["description_length"] >= 10
    assert "description" not in items[0].metadata


def test_submit_support_request_records_ticket_and_sends_email_when_enabled():
    service, audits, tickets, email_delivery = _service(email_enabled=True)

    receipt = service.submit_support_request(
        organization_id="org_1",
        account_id="acct_1",
        workspace_id="ws_1",
        actor_user_id="101",
        current_plan="growth",
        membership_role="admin",
        payload={
            "category": "recommendation",
            "subject": "Token issue",
            "description": "The API token request is failing with a 401 response.",
            "reply_email": "submitter@example.org",
            "watchers": ["ops@example.org", "reviewer@example.org"],
            "context": {
                "current_route_hash": "#/settings?nav=customer-admin-settings",
                "user_agent": "Portal Browser",
            },
        },
    )

    assert tickets is not None
    assert email_delivery is not None
    stored = tickets.get_by_support_request_id(receipt.support_request_id)
    audit_items = audits.list_for_organization("org_1")

    assert receipt.delivery_mode is SupportDeliveryMode.RECORDED_AND_EMAILED
    assert stored is not None
    assert stored.description == "The API token request is failing with a 401 response."
    assert stored.delivery_status is SupportTicketDeliveryStatus.SENT
    assert stored.provider_message_id == "message-123"
    assert len(email_delivery.requests) == 1
    assert email_delivery.requests[0].reply_email == "submitter@example.org"
    assert email_delivery.requests[0].watchers == (
        "ops@example.org",
        "reviewer@example.org",
    )
    assert len(audit_items) == 1
    assert "description" not in audit_items[0].metadata


def test_submit_support_request_marks_ticket_failed_when_email_delivery_fails():
    service, _audits, tickets, _email_delivery = _service(email_enabled=True, fail_email=True)

    try:
        service.submit_support_request(
            organization_id="org_1",
            account_id="acct_1",
            workspace_id="ws_1",
            actor_user_id="101",
            current_plan="growth",
            membership_role="admin",
            payload={
                "category": "api",
                "subject": "API issue",
                "description": "The API token request is failing with a 401 response.",
            },
        )
    except OrganizationSupportError as exc:
        assert exc.status_code == 502
        assert str(exc) == "Support request was recorded but email delivery failed"
    else:
        assert False, "Expected support delivery error"

    assert tickets is not None
    stored = next(iter(tickets._records.values()))
    assert stored.delivery_status is SupportTicketDeliveryStatus.FAILED
    assert stored.delivery_error == "smtp send failed"


def test_submit_support_request_rejects_invalid_payload():
    service, _audits, _tickets, _email_delivery = _service()

    try:
        service.submit_support_request(
            organization_id="org_1",
            account_id="acct_1",
            workspace_id="ws_1",
            actor_user_id="user_admin",
            current_plan="growth",
            membership_role="admin",
            payload={
                "category": "api",
                "subject": "Hi",
                "description": "short",
                "watchers": ["bad-email"],
            },
        )
    except OrganizationSupportError as exc:
        assert exc.status_code == 400
        assert str(exc) == "subject must be at least 3 characters"
    else:
        assert False, "Expected support validation error"
