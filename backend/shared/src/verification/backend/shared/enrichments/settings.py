from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from verification.backend.shared.enrichments.models import (
    EvaluationContext,
    OrganizationIntegrationSetting,
    OrganizationIntegrationSettings,
    TenantIntegrationSetting,
    normalize_integration_id,
)


@dataclass(frozen=True)
class OrganizationIntegrationSettingsRecord:
    workspace_id: str | None
    account_id: str | None
    integration_settings: OrganizationIntegrationSettings


class OrganizationIntegrationSettingsResolver:
    def __init__(
        self,
        records: list[OrganizationIntegrationSettingsRecord] | None = None,
        default_settings: OrganizationIntegrationSettings | dict[str, OrganizationIntegrationSetting] | None = None,
    ) -> None:
        self._records = records or []
        self._default_settings = (
            default_settings
            if isinstance(default_settings, OrganizationIntegrationSettings)
            else OrganizationIntegrationSettings.from_mapping(default_settings)
        )

    def resolve(
        self,
        *,
        workspace_id: str | None = None,
        account_id: str | None = None,
    ) -> EvaluationContext:
        workspace = (workspace_id or "").strip() or None
        account = (account_id or "").strip() or None

        if workspace:
            match = next((item for item in self._records if item.workspace_id == workspace), None)
            if match is not None:
                return EvaluationContext(
                    workspace_id=workspace,
                    account_id=account or match.account_id,
                    organization_integration_settings=_merge_settings(self._default_settings, match.integration_settings),
                )

        if account:
            match = next((item for item in self._records if item.account_id == account), None)
            if match is not None:
                return EvaluationContext(
                    workspace_id=workspace or match.workspace_id,
                    account_id=account,
                    organization_integration_settings=_merge_settings(self._default_settings, match.integration_settings),
                )

        return EvaluationContext(
            workspace_id=workspace,
            account_id=account,
            organization_integration_settings=self._default_settings,
        )


TenantIntegrationSettingsRecord = OrganizationIntegrationSettingsRecord
TenantIntegrationSettingsResolver = OrganizationIntegrationSettingsResolver


def load_organization_integration_settings(
    raw_json: str,
    default_settings: OrganizationIntegrationSettings | dict[str, OrganizationIntegrationSetting] | None = None,
) -> OrganizationIntegrationSettingsResolver:
    if not raw_json.strip():
        return OrganizationIntegrationSettingsResolver(default_settings=default_settings)

    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("ORGANIZATION_INTEGRATION_SETTINGS_JSON must be a JSON array")

    records: list[OrganizationIntegrationSettingsRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        settings_payload = item.get("integrations")
        if not isinstance(settings_payload, dict):
            settings_payload = {}
        integration_settings: dict[str, OrganizationIntegrationSetting] = {}
        for integration_id, raw_setting in settings_payload.items():
            if not isinstance(raw_setting, dict):
                continue
            normalized_integration_id = normalize_integration_id(str(integration_id).strip())
            if not normalized_integration_id:
                continue
            integration_settings[normalized_integration_id] = OrganizationIntegrationSetting(
                enabled=bool(raw_setting.get("enabled", False)),
                required_for_eligibility=bool(
                    raw_setting.get("requiredForEvaluation", raw_setting.get("required_for_evaluation", raw_setting.get("required_for_eligibility", False)))
                ),
            )
        records.append(
            OrganizationIntegrationSettingsRecord(
                workspace_id=_clean_identifier(item.get("workspace_id")),
                account_id=_clean_identifier(item.get("account_id")),
                integration_settings=OrganizationIntegrationSettings.from_mapping(integration_settings),
            )
        )
    return OrganizationIntegrationSettingsResolver(records, default_settings=default_settings)


def load_tenant_integration_settings(
    raw_json: str,
    default_settings: OrganizationIntegrationSettings | dict[str, OrganizationIntegrationSetting] | None = None,
) -> TenantIntegrationSettingsResolver:
    return load_organization_integration_settings(raw_json, default_settings=default_settings)


def _clean_identifier(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _merge_settings(
    defaults: OrganizationIntegrationSettings,
    overrides: OrganizationIntegrationSettings,
) -> OrganizationIntegrationSettings:
    return OrganizationIntegrationSettings.from_mapping(
        {
            **defaults.integrations,
            **overrides.integrations,
        }
    )

