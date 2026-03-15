from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from charity_status.enrichments.models import EvaluationContext, TenantIntegrationSetting


@dataclass(frozen=True)
class TenantIntegrationSettingsRecord:
    workspace_id: str | None
    account_id: str | None
    integration_settings: dict[str, TenantIntegrationSetting]


class TenantIntegrationSettingsResolver:
    def __init__(self, records: list[TenantIntegrationSettingsRecord] | None = None) -> None:
        self._records = records or []

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
                    integration_settings=match.integration_settings,
                )

        if account:
            match = next((item for item in self._records if item.account_id == account), None)
            if match is not None:
                return EvaluationContext(
                    workspace_id=workspace or match.workspace_id,
                    account_id=account,
                    integration_settings=match.integration_settings,
                )

        return EvaluationContext(workspace_id=workspace, account_id=account)


def load_tenant_integration_settings(raw_json: str) -> TenantIntegrationSettingsResolver:
    if not raw_json.strip():
        return TenantIntegrationSettingsResolver()

    payload = json.loads(raw_json)
    if not isinstance(payload, list):
        raise ValueError("TENANT_INTEGRATION_SETTINGS_JSON must be a JSON array")

    records: list[TenantIntegrationSettingsRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        settings_payload = item.get("integrations")
        if not isinstance(settings_payload, dict):
            settings_payload = {}
        integration_settings: dict[str, TenantIntegrationSetting] = {}
        for integration_id, raw_setting in settings_payload.items():
            if not isinstance(raw_setting, dict):
                continue
            integration_settings[str(integration_id).strip()] = TenantIntegrationSetting(
                enabled=bool(raw_setting.get("enabled", False)),
                required_for_eligibility=bool(raw_setting.get("required_for_eligibility", False)),
            )
        records.append(
            TenantIntegrationSettingsRecord(
                workspace_id=_clean_identifier(item.get("workspace_id")),
                account_id=_clean_identifier(item.get("account_id")),
                integration_settings=integration_settings,
            )
        )
    return TenantIntegrationSettingsResolver(records)


def _clean_identifier(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None
