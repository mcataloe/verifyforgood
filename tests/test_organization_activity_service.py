from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

if str(PRIVATE_PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIVATE_PLATFORM_SRC))


from charity_status_platform.customer_accounts import (  # noqa: E402
    AuditEventType,
    AuditRecord,
    DynamoAuditLogRepository,
    DynamoUserRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    OrganizationActivityService,
    UserRecord,
)


def test_activity_service_returns_sanitized_org_scoped_page_with_cursor():
    table = FakeIdentityDynamoTable()
    resource = FakeIdentityDynamoResource(table)
    audits = DynamoAuditLogRepository(dynamodb_resource=resource)
    users = DynamoUserRepository(dynamodb_resource=resource)
    users.create(
        UserRecord(
            user_id="user_admin",
            email="jamie.admin@example.org",
            normalized_email="jamie.admin@example.org",
            full_name="Jamie Admin",
            created_at="2026-03-29T00:00:00+00:00",
            updated_at="2026-03-29T00:00:00+00:00",
        )
    )
    service = OrganizationActivityService(audits=audits, users=users)

    audits.create(
        AuditRecord(
            audit_id="audit_other_org",
            event_type=AuditEventType.API_KEY_CREATION,
            actor_user_id="user_admin",
            organization_id="org_2",
            target_user_id=None,
            timestamp="2026-03-29T09:55:00+00:00",
            metadata={
                "display_name": "Other Org Key",
                "key_id": "key_other",
                "secret": "should_not_leak",
                "status": "active",
            },
        )
    )
    audits.create(
        AuditRecord(
            audit_id="audit_api_key",
            event_type=AuditEventType.API_KEY_CREATION,
            actor_user_id="user_admin",
            organization_id="org_1",
            target_user_id=None,
            timestamp="2026-03-29T10:00:00+00:00",
            metadata={
                "display_name": "Primary Key",
                "hashed_key_value": "hash_should_not_surface",
                "key_id": "key_123",
                "secret": "csk_secret_should_not_surface",
                "status": "active",
            },
        )
    )
    audits.create(
        AuditRecord(
            audit_id="audit_search",
            event_type=AuditEventType.NONPROFIT_SEARCH,
            actor_user_id="user_admin",
            organization_id="org_1",
            target_user_id=None,
            timestamp="2026-03-29T11:00:00+00:00",
            metadata={
                "query_state": "IL",
                "query_subsection": "03",
                "query_text": "helping hands",
                "result_count": 4,
            },
        )
    )
    audits.create(
        AuditRecord(
            audit_id="audit_invitation",
            event_type=AuditEventType.INVITATION_CREATION,
            actor_user_id="user_admin",
            organization_id="org_1",
            target_user_id=None,
            timestamp="2026-03-29T12:00:00+00:00",
            metadata={
                "email": "invitee@example.org",
                "role": "user",
                "token": "invtok_secret",
            },
        )
    )

    first_page = service.list_activity(organization_id="org_1", limit=2)
    second_page = service.list_activity(
        organization_id="org_1",
        limit=2,
        cursor=first_page.next_cursor,
    )

    assert [item.activity_id for item in first_page.items] == [
        "audit_invitation",
        "audit_search",
    ]
    assert first_page.has_more is True
    assert first_page.next_cursor is not None
    assert [item.activity_id for item in second_page.items] == [
        "audit_api_key",
    ]
    assert second_page.has_more is False
    assert second_page.next_cursor is None

    invitation = first_page.items[0]
    assert invitation.category == "invitations"
    assert invitation.actor["display_name"] == "Jamie Admin"
    assert invitation.metadata["email"] == "i***e@example.org"
    assert "token" not in invitation.metadata

    nonprofit_search = first_page.items[1]
    assert nonprofit_search.category == "nonprofit_access"
    assert nonprofit_search.metadata["result_count"] == 4
    assert "query_text" not in nonprofit_search.metadata

    api_key = second_page.items[0]
    assert api_key.category == "api_keys"
    assert api_key.metadata == {
        "display_name": "Primary Key",
        "key_id": "key_123",
        "status": "active",
    }
