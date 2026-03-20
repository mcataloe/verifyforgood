from __future__ import annotations

from typing import Any

import boto3

from charity_status.enrichments.organization_settings_service import (
    AccountBillingSettings,
    OrganizationIntegrationSettingsDocument,
    OrganizationIntegrationSettingsValidationError,
)


class InMemoryOrganizationIntegrationSettingsStore:
    def __init__(self, items: list[dict[str, Any]] | None = None) -> None:
        self._items: dict[tuple[str | None, str | None], OrganizationIntegrationSettingsDocument] = {}
        self._billing_items: dict[str, tuple[AccountBillingSettings, str | None]] = {}
        for item in items or []:
            document = OrganizationIntegrationSettingsDocument.from_item(dict(item), source="stored")
            key = (_clean_identifier(document.workspace_id), _clean_identifier(document.account_id))
            self._items[key] = document

    def get_settings_document(
        self,
        *,
        workspace_id: str | None,
        account_id: str | None,
    ) -> OrganizationIntegrationSettingsDocument | None:
        workspace = _clean_identifier(workspace_id)
        account = _clean_identifier(account_id)
        if workspace is not None:
            document = self._items.get((workspace, account)) or next(
                (value for (ws, _acct), value in self._items.items() if ws == workspace),
                None,
            )
            if document is not None:
                return document
        if account is not None:
            document = next((value for (_ws, acct), value in self._items.items() if acct == account), None)
            if document is not None:
                return document
        return None

    def put_settings_document(self, document: OrganizationIntegrationSettingsDocument) -> None:
        key = (_clean_identifier(document.workspace_id), _clean_identifier(document.account_id))
        self._items[key] = document

    def load_billing_settings(self, *, account_id: str | None) -> tuple[AccountBillingSettings, str | None]:
        account = _clean_identifier(account_id)
        if account is None:
            return AccountBillingSettings(), None
        return self._billing_items.get(account, (AccountBillingSettings(), None))

    def store_billing_settings(
        self,
        *,
        account_id: str | None,
        settings: AccountBillingSettings,
        updated_at: str | None,
    ) -> None:
        account = _clean_identifier(account_id)
        if account is None:
            raise OrganizationIntegrationSettingsValidationError("account_id is required")
        self._billing_items[account] = (settings, updated_at)

    def get_settings(self, *, workspace_id: str | None, account_id: str | None) -> dict[str, Any] | None:
        document = self.get_settings_document(workspace_id=workspace_id, account_id=account_id)
        if document is None:
            return None
        return {
            "workspace_id": document.workspace_id,
            "account_id": document.account_id,
            "updated_at": document.updated_at,
            "integrations": {
                integration_id: setting.to_dict()
                for integration_id, setting in document.integration_settings.integrations.items()
            },
        }

    def put_settings(self, item: dict[str, Any]) -> None:
        self.put_settings_document(OrganizationIntegrationSettingsDocument.from_item(item, source="stored"))

    def get_billing_settings(self, *, account_id: str | None) -> dict[str, Any] | None:
        settings, updated_at = self.load_billing_settings(account_id=account_id)
        account = _clean_identifier(account_id)
        if account is None:
            return None
        return {
            "account_id": account,
            "updated_at": updated_at,
            "billing": settings.to_dict(),
        }

    def put_billing_settings(self, item: dict[str, Any]) -> None:
        self.store_billing_settings(
            account_id=item.get("account_id"),
            settings=AccountBillingSettings.from_item(item),
            updated_at=item.get("updated_at"),
        )


class DynamoOrganizationIntegrationSettingsStore:
    def __init__(self, table_name: str, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name
        self._resource = dynamodb_resource or boto3.resource("dynamodb")
        self._table = self._resource.Table(table_name)

    def get_settings_document(
        self,
        *,
        workspace_id: str | None,
        account_id: str | None,
    ) -> OrganizationIntegrationSettingsDocument | None:
        workspace = _clean_identifier(workspace_id)
        account = _clean_identifier(account_id)
        if workspace is None and account is None:
            return None
        if workspace is not None:
            response = self._table.get_item(Key={"pk": _organization_settings_pk(workspace), "sk": _organization_settings_sk(account)})
            item = response.get("Item")
            if item is not None:
                return OrganizationIntegrationSettingsDocument.from_item(item, source="stored")
        if account is not None:
            response = self._table.query(
                IndexName="account_lookup",
                KeyConditionExpression="account_id = :account_id",
                ExpressionAttributeValues={":account_id": account},
                Limit=1,
            )
            items = response.get("Items") or []
            if items:
                return OrganizationIntegrationSettingsDocument.from_item(items[0], source="stored")
        return None

    def put_settings_document(self, document: OrganizationIntegrationSettingsDocument) -> None:
        self._table.put_item(Item=_document_to_item(document))

    def load_billing_settings(self, *, account_id: str | None) -> tuple[AccountBillingSettings, str | None]:
        account = _clean_identifier(account_id)
        if account is None:
            return AccountBillingSettings(), None
        response = self._table.get_item(Key={"pk": _organization_billing_pk(account), "sk": "BILLING"})
        item = response.get("Item")
        if item is None:
            return AccountBillingSettings(), None
        return AccountBillingSettings.from_item(item), _clean_identifier(item.get("updated_at"))

    def store_billing_settings(
        self,
        *,
        account_id: str | None,
        settings: AccountBillingSettings,
        updated_at: str | None,
    ) -> None:
        self._table.put_item(Item=_billing_settings_item(account_id, settings, updated_at))

    def get_settings(self, *, workspace_id: str | None, account_id: str | None) -> dict[str, Any] | None:
        document = self.get_settings_document(workspace_id=workspace_id, account_id=account_id)
        if document is None:
            return None
        return _document_to_item(document)

    def put_settings(self, item: dict[str, Any]) -> None:
        self.put_settings_document(OrganizationIntegrationSettingsDocument.from_item(item, source="stored"))

    def get_billing_settings(self, *, account_id: str | None) -> dict[str, Any] | None:
        account = _clean_identifier(account_id)
        if account is None:
            return None
        settings, updated_at = self.load_billing_settings(account_id=account)
        return _billing_settings_item(account, settings, updated_at)

    def put_billing_settings(self, item: dict[str, Any]) -> None:
        self.store_billing_settings(
            account_id=item.get("account_id"),
            settings=AccountBillingSettings.from_item(item),
            updated_at=item.get("updated_at"),
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


def _billing_settings_item(account_id: str | None, settings: AccountBillingSettings, updated_at: str | None) -> dict[str, Any]:
    account = _clean_identifier(account_id)
    if account is None:
        raise OrganizationIntegrationSettingsValidationError("account_id is required")
    return {
        "pk": _organization_billing_pk(account),
        "sk": "BILLING",
        "type": "ACCOUNT_BILLING_SETTINGS",
        "account_id": account,
        "updated_at": updated_at,
        "billing": settings.to_dict(),
    }


def _organization_settings_pk(workspace_id: str | None) -> str:
    return f"WORKSPACE#{_clean_identifier(workspace_id) or 'unknown'}"


def _organization_settings_sk(account_id: str | None) -> str:
    return f"ACCOUNT#{_clean_identifier(account_id) or 'unknown'}"


def _organization_billing_pk(account_id: str | None) -> str:
    return f"ACCOUNT#{_clean_identifier(account_id) or 'unknown'}"


def _clean_identifier(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None
