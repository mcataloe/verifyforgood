from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import boto3

from charity_status.enrichments.models import (
    EvaluationContext,
    OrganizationIntegrationSetting,
    OrganizationIntegrationSettings,
    integration_id_display_name,
    normalize_integration_id,
)
from charity_status.enrichments.settings import OrganizationIntegrationSettingsResolver


SUPPORTED_MANAGED_INTEGRATIONS = ("candid", "charity_navigator")


class OrganizationIntegrationSettingsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class OrganizationIntegrationSettingsDocument:
    workspace_id: str | None
    account_id: str | None
    integration_settings: OrganizationIntegrationSettings
    source: str = "default"
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "account_id": self.account_id,
            "source": self.source,
            "updated_at": self.updated_at,
            "integrations": self.integration_settings.to_dict(),
        }

    @classmethod
    def from_item(cls, item: dict[str, Any], source: str = "stored") -> "OrganizationIntegrationSettingsDocument":
        payload = item.get("integrations") if isinstance(item.get("integrations"), dict) else {}
        settings = {
            normalize_integration_id(key): _normalize_setting_dict(value)
            for key, value in payload.items()
            if normalize_integration_id(key)
        }
        return cls(
            workspace_id=_clean_identifier(item.get("workspace_id")),
            account_id=_clean_identifier(item.get("account_id")),
            integration_settings=OrganizationIntegrationSettings.from_mapping(settings),
            source=source,
            updated_at=_clean_identifier(item.get("updated_at")),
        )


class InMemoryOrganizationIntegrationSettingsStore:
    def __init__(self, items: list[dict[str, Any]] | None = None) -> None:
        self._items: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for item in items or []:
            key = (_clean_identifier(item.get("workspace_id")), _clean_identifier(item.get("account_id")))
            self._items[key] = dict(item)

    def get_settings(self, *, workspace_id: str | None, account_id: str | None) -> dict[str, Any] | None:
        workspace = _clean_identifier(workspace_id)
        account = _clean_identifier(account_id)
        if workspace is not None:
            item = self._items.get((workspace, account)) or next(
                (value for (ws, _acct), value in self._items.items() if ws == workspace),
                None,
            )
            if item is not None:
                return dict(item)
        if account is not None:
            item = next((value for (_ws, acct), value in self._items.items() if acct == account), None)
            if item is not None:
                return dict(item)
        return None

    def put_settings(self, item: dict[str, Any]) -> None:
        key = (_clean_identifier(item.get("workspace_id")), _clean_identifier(item.get("account_id")))
        self._items[key] = dict(item)


class DynamoOrganizationIntegrationSettingsStore:
    def __init__(self, table_name: str, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name
        self._resource = dynamodb_resource or boto3.resource("dynamodb")
        self._table = self._resource.Table(table_name)

    def get_settings(self, *, workspace_id: str | None, account_id: str | None) -> dict[str, Any] | None:
        workspace = _clean_identifier(workspace_id)
        account = _clean_identifier(account_id)
        if workspace is None and account is None:
            return None
        if workspace is not None:
            response = self._table.get_item(Key={"pk": _organization_settings_pk(workspace), "sk": _organization_settings_sk(account)})
            item = response.get("Item")
            if item is not None:
                return item
        if account is not None:
            response = self._table.query(
                IndexName="account_lookup",
                KeyConditionExpression="account_id = :account_id",
                ExpressionAttributeValues={":account_id": account},
                Limit=1,
            )
            items = response.get("Items") or []
            if items:
                return items[0]
        return None

    def put_settings(self, item: dict[str, Any]) -> None:
        self._table.put_item(Item=item)


class OrganizationIntegrationSettingsService:
    def __init__(
        self,
        *,
        fallback_resolver: OrganizationIntegrationSettingsResolver,
        store: InMemoryOrganizationIntegrationSettingsStore | DynamoOrganizationIntegrationSettingsStore | None = None,
        supported_integrations: tuple[str, ...] = SUPPORTED_MANAGED_INTEGRATIONS,
    ) -> None:
        self._fallback_resolver = fallback_resolver
        self._store = store
        self._supported_integrations = tuple(normalize_integration_id(item) for item in supported_integrations)

    def resolve_context(self, *, workspace_id: str | None, account_id: str | None) -> EvaluationContext:
        base_context = self._fallback_resolver.resolve(workspace_id=workspace_id, account_id=account_id)
        stored = self._get_stored_document(workspace_id=workspace_id, account_id=account_id)
        if stored is None:
            return base_context
        merged = OrganizationIntegrationSettings.from_mapping(
            {
                **base_context.organization_integration_settings.integrations,
                **stored.integration_settings.integrations,
            }
        )
        return EvaluationContext(
            workspace_id=workspace_id or stored.workspace_id,
            account_id=account_id or stored.account_id,
            organization_integration_settings=merged,
        )

    def get_settings(self, *, workspace_id: str | None, account_id: str | None) -> OrganizationIntegrationSettingsDocument:
        context = self.resolve_context(workspace_id=workspace_id, account_id=account_id)
        stored = self._get_stored_document(workspace_id=workspace_id, account_id=account_id)
        source = stored.source if stored is not None else "default"
        updated_at = stored.updated_at if stored is not None else None
        return OrganizationIntegrationSettingsDocument(
            workspace_id=context.workspace_id,
            account_id=context.account_id,
            integration_settings=self._with_supported_defaults(context.organization_integration_settings),
            source=source,
            updated_at=updated_at,
        )

    def update_settings(
        self,
        *,
        workspace_id: str | None,
        account_id: str | None,
        payload: dict[str, Any],
    ) -> OrganizationIntegrationSettingsDocument:
        if self._store is None:
            raise OrganizationIntegrationSettingsValidationError("Organization integration settings store is not configured")
        workspace = _clean_identifier(workspace_id)
        account = _clean_identifier(account_id)
        if workspace is None and account is None:
            raise OrganizationIntegrationSettingsValidationError("workspace_id or account_id is required")

        current = self.get_settings(workspace_id=workspace, account_id=account)
        updates = self._parse_update_payload(payload)
        merged = OrganizationIntegrationSettings.from_mapping(
            {
                **current.integration_settings.integrations,
                **updates.integrations,
            }
        )
        validate_organization_integration_settings(merged, supported_integrations=self._supported_integrations)
        document = OrganizationIntegrationSettingsDocument(
            workspace_id=workspace or current.workspace_id,
            account_id=account or current.account_id,
            integration_settings=self._with_supported_defaults(merged),
            source="stored",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._store.put_settings(_document_to_item(document))
        return document

    def _parse_update_payload(self, payload: dict[str, Any]) -> OrganizationIntegrationSettings:
        integrations = payload.get("integrations")
        if not isinstance(integrations, dict):
            raise OrganizationIntegrationSettingsValidationError("Request body must include integrations object")
        parsed: dict[str, OrganizationIntegrationSetting] = {}
        for raw_id, raw_setting in integrations.items():
            integration_id = normalize_integration_id(raw_id)
            if integration_id not in self._supported_integrations:
                raise OrganizationIntegrationSettingsValidationError(f"Unsupported integration: {raw_id}")
            if not isinstance(raw_setting, dict):
                raise OrganizationIntegrationSettingsValidationError(f"Integration settings for {raw_id} must be an object")
            parsed[integration_id] = _normalize_setting_dict(raw_setting)
        return OrganizationIntegrationSettings.from_mapping(parsed)

    def _get_stored_document(self, *, workspace_id: str | None, account_id: str | None) -> OrganizationIntegrationSettingsDocument | None:
        if self._store is None:
            return None
        item = self._store.get_settings(workspace_id=workspace_id, account_id=account_id)
        if item is None:
            return None
        return OrganizationIntegrationSettingsDocument.from_item(item, source="stored")

    def _with_supported_defaults(self, settings: OrganizationIntegrationSettings) -> OrganizationIntegrationSettings:
        return OrganizationIntegrationSettings.from_mapping(
            {
                integration_id: settings.setting_for(integration_id)
                for integration_id in self._supported_integrations
            }
        )


def validate_organization_integration_settings(
    settings: OrganizationIntegrationSettings,
    *,
    supported_integrations: tuple[str, ...] = SUPPORTED_MANAGED_INTEGRATIONS,
) -> None:
    supported = {normalize_integration_id(item) for item in supported_integrations}
    for integration_id in settings.integration_ids():
        if integration_id not in supported:
            raise OrganizationIntegrationSettingsValidationError(f"Unsupported integration: {integration_id_display_name(integration_id)}")
        setting = settings.setting_for(integration_id)
        if setting.required_for_evaluation and not setting.enabled:
            raise OrganizationIntegrationSettingsValidationError(
                f"{integration_id_display_name(integration_id)}.requiredForEvaluation cannot be true when enabled is false"
            )


def _document_to_item(document: OrganizationIntegrationSettingsDocument) -> dict[str, Any]:
    return {
        "pk": _organization_settings_pk(document.workspace_id),
        "sk": _organization_settings_sk(document.account_id),
        "workspace_id": document.workspace_id,
        "account_id": document.account_id,
        "updated_at": document.updated_at,
        "integrations": {
            integration_id: setting.to_dict()
            for integration_id, setting in document.integration_settings.integrations.items()
        },
    }


def _organization_settings_pk(workspace_id: str | None) -> str:
    return f"WORKSPACE#{_clean_identifier(workspace_id) or 'unknown'}"


def _organization_settings_sk(account_id: str | None) -> str:
    return f"ACCOUNT#{_clean_identifier(account_id) or 'unknown'}"


def _normalize_setting_dict(raw_setting: dict[str, Any]) -> OrganizationIntegrationSetting:
    return OrganizationIntegrationSetting(
        enabled=bool(raw_setting.get("enabled", False)),
        required_for_eligibility=bool(
            raw_setting.get("requiredForEvaluation", raw_setting.get("required_for_evaluation", raw_setting.get("required_for_eligibility", False)))
        ),
    )


def _clean_identifier(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None
