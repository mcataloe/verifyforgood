from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


from charity_status_platform.customer_accounts import (  # noqa: E402
    AuditEventType,
    DynamoAuditLogRepository,
    DynamoOrganizationRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    OrganizationRecord,
    OrganizationSupportError,
    OrganizationSupportService,
)


def _service():
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
    return OrganizationSupportService(
        organizations=organizations,
        audits=audits,
    ), audits


def test_get_support_context_returns_org_scoped_contact_and_links():
    service, _audits = _service()

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


def test_submit_support_request_records_sanitized_audit_event():
    service, audits = _service()

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
    assert receipt.delivery_mode == "recorded_only"
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


def test_submit_support_request_rejects_invalid_payload():
    service, _audits = _service()

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
