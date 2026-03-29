from charity_status.enrichments import (
    InMemoryOrganizationIntegrationSettingsStore,
    OrganizationIntegrationSettingsService,
    OrganizationIntegrationSettingsValidationError,
    load_organization_integration_settings,
)
from charity_status_platform.customer_accounts import (
    AuditEventType,
    AuditLogService,
    DynamoAuditLogRepository,
    DynamoOrganizationRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    OrganizationRecord,
    OrganizationSettingsService,
)


def _service(*, settings_store=None):
    identity_table = FakeIdentityDynamoTable()
    identity_resource = FakeIdentityDynamoResource(identity_table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=identity_resource)
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Org One",
            slug="org-one",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
            contact_email="ops@orgone.example",
        )
    )
    integration_settings = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=settings_store,
    )
    audit_repository = DynamoAuditLogRepository(dynamodb_resource=identity_resource)
    audit_log_service = AuditLogService(
        repository=audit_repository,
    )
    return (
        OrganizationSettingsService(
            integration_settings=integration_settings,
            organizations=organizations,
            audit_log_service=audit_log_service,
        ),
        organizations,
        audit_repository,
    )


def test_get_organization_settings_returns_composite_document():
    settings_store = InMemoryOrganizationIntegrationSettingsStore(
        [
            {
                "workspace_id": "org_1",
                "account_id": "org_1",
                "integrations": {
                    "candid": {"enabled": True, "requiredForEvaluation": False},
                },
            }
        ]
    )
    service, _organizations, _audit_log_service = _service(settings_store=settings_store)

    document = service.get_settings(
        organization_id="org_1",
        workspace_id="org_1",
        account_id="org_1",
    )

    payload = document.to_dict()
    assert payload["organization"]["displayName"] == "Org One"
    assert payload["organization"]["contactEmail"] == "ops@orgone.example"
    assert payload["organization"]["slug"] == "org-one"
    assert payload["integrations"]["candid"]["enabled"] is True
    assert payload["billing"]["allowOverage"] is True


def test_update_organization_settings_persists_profile_changes():
    service, organizations, _audit_log_service = _service(
        settings_store=InMemoryOrganizationIntegrationSettingsStore()
    )

    document = service.update_settings(
        organization_id="org_1",
        workspace_id="org_1",
        account_id="org_1",
        payload={
            "organization": {
                "displayName": "Org One Updated",
                "contactEmail": "",
            }
        },
    )

    assert document.organization.display_name == "Org One Updated"
    assert document.organization.contact_email is None
    persisted = organizations.get("org_1")
    assert persisted is not None
    assert persisted.name == "Org One Updated"
    assert persisted.contact_email is None


def test_update_organization_settings_rejects_slug_mutation():
    service, _organizations, _audit_log_service = _service(
        settings_store=InMemoryOrganizationIntegrationSettingsStore()
    )

    try:
        service.update_settings(
            organization_id="org_1",
            workspace_id="org_1",
            account_id="org_1",
            payload={"organization": {"slug": "new-slug"}},
        )
    except OrganizationIntegrationSettingsValidationError as exc:
        assert str(exc) == "organization.slug is read-only"
    else:
        assert False, "Expected validation error"


def test_update_organization_settings_records_sanitized_audit_event():
    service, _organizations, audit_repository = _service(
        settings_store=InMemoryOrganizationIntegrationSettingsStore()
    )

    service.update_settings(
        organization_id="org_1",
        workspace_id="org_1",
        account_id="org_1",
        actor_user_id="user_admin",
        payload={
            "organization": {
                "displayName": "Org One Updated",
                "contactEmail": "support@orgone.example",
            },
            "billing": {
                "allowOverage": False,
                "monthlyRequestCap": 750,
            },
        },
    )

    audit_items = audit_repository.list_for_organization("org_1")

    assert len(audit_items) == 1
    assert audit_items[0].event_type is AuditEventType.ORGANIZATION_SETTINGS_UPDATE
    assert audit_items[0].actor_user_id == "user_admin"
    assert audit_items[0].metadata["changed_fields"] == ["display_name", "contact_email"]
    assert audit_items[0].metadata["changed_sections"] == ["billing"]
    assert "support@orgone.example" not in str(audit_items[0].metadata)
