from verification.backend.shared.enrichments import (
    InMemoryOrganizationIntegrationSettingsStore,
    OrganizationIntegrationSettingsService,
    OrganizationIntegrationSettingsValidationError,
    load_organization_integration_settings,
)


def _service(store=None, raw_json="[]"):
    return OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings(raw_json),
        store=store,
    )


def test_organization_integration_settings_default_document():
    service = _service()

    document = service.get_settings(workspace_id="ws_1", account_id="acct_1")

    assert document.workspace_id == "ws_1"
    assert document.account_id == "acct_1"
    assert document.source == "default"
    assert document.to_dict()["integrations"]["candid"] == {"enabled": False, "requiredForEvaluation": False, "required_for_evaluation": False, "required_for_eligibility": False}
    assert document.to_dict()["integrations"]["charityNavigator"]["enabled"] is False


def test_organization_integration_settings_update_and_retrieve():
    store = InMemoryOrganizationIntegrationSettingsStore()
    service = _service(store=store)

    updated = service.update_settings(
        workspace_id="ws_1",
        account_id="acct_1",
        payload={
            "integrations": {
                "candid": {"enabled": True, "requiredForEvaluation": False},
                "charityNavigator": {"enabled": True, "requiredForEvaluation": True},
            }
        },
    )
    fetched = service.get_settings(workspace_id="ws_1", account_id="acct_1")

    assert updated.source == "stored"
    assert fetched.source == "stored"
    assert fetched.integration_settings.setting_for("candid").enabled is True
    assert fetched.integration_settings.setting_for("charity_navigator").required_for_evaluation is True


def test_organization_integration_settings_validation_rejects_required_disabled():
    store = InMemoryOrganizationIntegrationSettingsStore()
    service = _service(store=store)

    try:
        service.update_settings(
            workspace_id="ws_1",
            account_id="acct_1",
            payload={
                "integrations": {
                    "candid": {"enabled": False, "requiredForEvaluation": True},
                }
            },
        )
    except OrganizationIntegrationSettingsValidationError as exc:
        assert "requiredForEvaluation" in str(exc)
    else:
        assert False, "Expected validation error"


def test_organization_integration_settings_reuses_existing_defaults_for_partial_update():
    store = InMemoryOrganizationIntegrationSettingsStore(
        [
            {
                "workspace_id": "ws_1",
                "account_id": "acct_1",
                "integrations": {
                    "candid": {"enabled": True, "requiredForEvaluation": False},
                    "charity_navigator": {"enabled": False, "requiredForEvaluation": False},
                },
            }
        ]
    )
    service = _service(store=store)

    updated = service.update_settings(
        workspace_id="ws_1",
        account_id="acct_1",
        payload={
            "integrations": {
                "charityNavigator": {"enabled": True, "requiredForEvaluation": True},
            }
        },
    )

    assert updated.integration_settings.setting_for("candid").enabled is True
    assert updated.integration_settings.setting_for("charity_navigator").required_for_evaluation is True

