from verification.enrichments import load_organization_integration_settings
from verification.platform import load_platform_integrations_config


def test_platform_integrations_default_to_disabled():
    config = load_platform_integrations_config({})

    assert config.globally_enabled is False
    assert config.integration("candid").available is False
    assert config.integration("candid").credentials_present is False
    assert config.integration("candid").default_required_for_evaluation is False
    assert config.integration("charity_navigator").available is False
    assert config.integration("charity_navigator").credentials_present is False


def test_platform_integrations_parse_requested_env_shape():
    config = load_platform_integrations_config(
        {
            "THIRD_PARTY_INTEGRATIONS_ENABLED": "true",
            "INTEGRATION_CANDID_ENABLED": "true",
            "INTEGRATION_CANDID_CLIENT_ID": "client-id",
            "INTEGRATION_CANDID_CLIENT_SECRET": "client-secret",
            "DEFAULT_REQUIRE_CANDID_FOR_EVALUATION": "true",
            "INTEGRATION_CHARITY_NAVIGATOR_ENABLED": "true",
            "INTEGRATION_CHARITY_NAVIGATOR_API_KEY": "nav-key",
            "DEFAULT_REQUIRE_CHARITY_NAVIGATOR_FOR_EVALUATION": "false",
        }
    )

    candid = config.integration("candid")
    charity_navigator = config.integration("charityNavigator")

    assert config.globally_enabled is True
    assert candid.available is True
    assert candid.credentials_present is True
    assert candid.default_required_for_evaluation is True
    assert charity_navigator.available is True
    assert charity_navigator.credentials_present is True
    assert charity_navigator.default_required_for_evaluation is False


def test_organization_integration_settings_default_to_disabled():
    resolver = load_organization_integration_settings("[]")
    context = resolver.resolve(workspace_id="ws_1", account_id="acct_1")

    assert context.setting_for("candid").enabled is False
    assert context.setting_for("candid").required_for_evaluation is False
    assert context.organization_integration_settings.to_dict() == {}


def test_organization_integration_settings_parse_enablement_and_requirement():
    resolver = load_organization_integration_settings(
        """
        [
          {
            "workspace_id": "ws_1",
            "account_id": "acct_1",
            "integrations": {
              "candid": {"enabled": true, "requiredForEvaluation": true},
              "charityNavigator": {"enabled": false, "requiredForEvaluation": false}
            }
          }
        ]
        """
    )

    context = resolver.resolve(workspace_id="ws_1", account_id="acct_1")

    assert context.setting_for("candid").enabled is True
    assert context.setting_for("candid").required_for_evaluation is True
    assert context.setting_for("charity_navigator").enabled is False
    assert context.setting_for("charity_navigator").required_for_evaluation is False
    assert context.organization_integration_settings.to_dict()["charityNavigator"]["enabled"] is False


def test_default_required_for_evaluation_applies_without_enabling_integration():
    platform_config = load_platform_integrations_config(
        {
            "THIRD_PARTY_INTEGRATIONS_ENABLED": "true",
            "INTEGRATION_CANDID_ENABLED": "true",
            "DEFAULT_REQUIRE_CANDID_FOR_EVALUATION": "true",
        }
    )
    resolver = load_organization_integration_settings(
        "[]",
        default_settings=platform_config.organization_default_settings(),
    )

    context = resolver.resolve(workspace_id="ws_2", account_id="acct_2")
    setting = context.setting_for("candid")

    assert setting.enabled is False
    assert setting.required_for_evaluation is True

