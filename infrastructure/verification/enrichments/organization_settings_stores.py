from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import importlib
from sqlalchemy import BIGINT, JSON, Boolean, DateTime, Identity, Integer, MetaData, String, UniqueConstraint, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from verification.enrichments.organization_settings_service import (
    AccountBillingSettings,
    OrganizationIntegrationSettingsDocument,
    OrganizationIntegrationSettingsValidationError,
)


BIGINT_PRIMARY_KEY = BIGINT().with_variant(Integer(), "sqlite")
BIGINT_FOREIGN_KEY = BIGINT().with_variant(Integer(), "sqlite")
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class OrganizationSettingsBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class OrganizationSettingsModel(OrganizationSettingsBase):
    __tablename__ = "organization_settings"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_organization_settings_organization_id"),
        UniqueConstraint("workspace_id", name="uq_organization_settings_workspace_id"),
        UniqueConstraint("account_id", name="uq_organization_settings_account_id"),
    )

    settings_id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, Identity(start=1), primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(BIGINT_FOREIGN_KEY, nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    integrations_json: Mapped[dict[str, Any]] = mapped_column("integrations", JSON, nullable=False, default=dict)
    billing_allow_overage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    billing_monthly_request_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


@contextmanager
def organization_settings_session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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
        self._resource = dynamodb_resource or _load_boto3().resource("dynamodb")
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


class SqlAlchemyOrganizationIntegrationSettingsStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
        with organization_settings_session_scope(self._session_factory) as session:
            query = select(OrganizationSettingsModel)
            if workspace is not None and account is not None:
                query = query.where(
                    or_(
                        OrganizationSettingsModel.workspace_id == workspace,
                        OrganizationSettingsModel.account_id == account,
                    )
                )
            elif workspace is not None:
                query = query.where(OrganizationSettingsModel.workspace_id == workspace)
            else:
                query = query.where(OrganizationSettingsModel.account_id == account)
            model = session.scalar(query.limit(1))
            return None if model is None else _model_to_document(model)

    def put_settings_document(self, document: OrganizationIntegrationSettingsDocument) -> None:
        with organization_settings_session_scope(self._session_factory) as session:
            model = _lookup_settings_model(
                session,
                workspace_id=document.workspace_id,
                account_id=document.account_id,
            )
            if model is None:
                model = OrganizationSettingsModel(
                    organization_id=_require_org_id(document),
                    workspace_id=_clean_identifier(document.workspace_id),
                    account_id=_clean_identifier(document.account_id),
                    integrations_json=_document_integrations(document),
                    billing_allow_overage=bool(document.billing_settings.allow_overage),
                    billing_monthly_request_cap=document.billing_settings.monthly_request_cap,
                    updated_at=_parse_optional_timestamp(document.updated_at),
                )
                session.add(model)
            else:
                model.workspace_id = _clean_identifier(document.workspace_id)
                model.account_id = _clean_identifier(document.account_id)
                model.integrations_json = _document_integrations(document)
                model.updated_at = _parse_optional_timestamp(document.updated_at)
            session.flush()

    def load_billing_settings(self, *, account_id: str | None) -> tuple[AccountBillingSettings, str | None]:
        account = _clean_identifier(account_id)
        if account is None:
            return AccountBillingSettings(), None
        with organization_settings_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationSettingsModel)
                .where(OrganizationSettingsModel.account_id == account)
                .limit(1)
            )
            if model is None:
                return AccountBillingSettings(), None
            return _model_billing_settings(model), _format_optional_timestamp(model.updated_at)

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
        with organization_settings_session_scope(self._session_factory) as session:
            model = session.scalar(
                select(OrganizationSettingsModel)
                .where(OrganizationSettingsModel.account_id == account)
                .limit(1)
            )
            if model is None:
                if not account.isdigit():
                    raise OrganizationIntegrationSettingsValidationError("organization settings record was not found")
                model = OrganizationSettingsModel(
                    organization_id=int(account),
                    workspace_id=account,
                    account_id=account,
                    integrations_json={},
                    billing_allow_overage=bool(settings.allow_overage),
                    billing_monthly_request_cap=settings.monthly_request_cap,
                    updated_at=_parse_optional_timestamp(updated_at),
                )
                session.add(model)
            else:
                model.billing_allow_overage = bool(settings.allow_overage)
                model.billing_monthly_request_cap = settings.monthly_request_cap
                model.updated_at = _parse_optional_timestamp(updated_at)
            session.flush()


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


def _lookup_settings_model(
    session: Session,
    *,
    workspace_id: str | None,
    account_id: str | None,
) -> OrganizationSettingsModel | None:
    workspace = _clean_identifier(workspace_id)
    account = _clean_identifier(account_id)
    if workspace is None and account is None:
        return None
    query = select(OrganizationSettingsModel)
    if workspace is not None and account is not None:
        query = query.where(
            or_(
                OrganizationSettingsModel.workspace_id == workspace,
                OrganizationSettingsModel.account_id == account,
            )
        )
    elif workspace is not None:
        query = query.where(OrganizationSettingsModel.workspace_id == workspace)
    else:
        query = query.where(OrganizationSettingsModel.account_id == account)
    return session.scalar(query.limit(1))


def _document_integrations(document: OrganizationIntegrationSettingsDocument) -> dict[str, Any]:
    return {
        integration_id: setting.to_dict()
        for integration_id, setting in document.integration_settings.integrations.items()
    }


def _model_to_document(model: OrganizationSettingsModel) -> OrganizationIntegrationSettingsDocument:
    item = {
        "workspace_id": model.workspace_id,
        "account_id": model.account_id,
        "updated_at": _format_optional_timestamp(model.updated_at),
        "integrations": dict(model.integrations_json or {}),
    }
    document = OrganizationIntegrationSettingsDocument.from_item(item, source="stored")
    return OrganizationIntegrationSettingsDocument(
        workspace_id=document.workspace_id,
        account_id=document.account_id,
        integration_settings=document.integration_settings,
        billing_settings=_model_billing_settings(model),
        source="stored",
        updated_at=document.updated_at,
    )


def _model_billing_settings(model: OrganizationSettingsModel) -> AccountBillingSettings:
    return AccountBillingSettings(
        allow_overage=bool(model.billing_allow_overage),
        monthly_request_cap=model.billing_monthly_request_cap,
    )


def _require_org_id(document: OrganizationIntegrationSettingsDocument) -> int:
    candidate = _clean_identifier(document.workspace_id) or _clean_identifier(document.account_id)
    if candidate is None or not candidate.isdigit():
        raise OrganizationIntegrationSettingsValidationError("organization settings require a numeric workspace_id or account_id")
    return int(candidate)


def _parse_optional_timestamp(value: str | None):
    candidate = _clean_identifier(value)
    if candidate is None:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    return datetime.fromisoformat(candidate)


def _format_optional_timestamp(value) -> str | None:
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _load_boto3():
    try:
        return importlib.import_module("boto3")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "boto3 is required for DynamoDB-backed organization settings storage. "
            "The installed boto3/botocore environment could not be imported."
        ) from exc

