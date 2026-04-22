from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from verification.backend.shared.enrichments.models import (
    EvaluationContext,
    OrganizationIntegrationSetting,
    OrganizationIntegrationSettings,
    integration_id_display_name,
    normalize_integration_id,
)
from verification.backend.shared.enrichments.settings import OrganizationIntegrationSettingsResolver


SUPPORTED_MANAGED_INTEGRATIONS = ("candid", "charity_navigator")


class OrganizationIntegrationSettingsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AccountBillingSettings:
    allow_overage: bool = False
    monthly_request_cap: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowOverage": self.allow_overage,
            "monthlyRequestCap": self.monthly_request_cap,
        }

    @classmethod
    def from_item(cls, item: dict[str, Any] | None) -> "AccountBillingSettings":
        if not isinstance(item, dict):
            return cls()
        billing = item.get("billing") if isinstance(item.get("billing"), dict) else item
        return cls(
            allow_overage=_coerce_bool(
                billing.get("allowOverage", billing.get("allow_overage")),
                default=False,
            ),
            monthly_request_cap=_coerce_positive_int_or_none(
                billing.get("monthlyRequestCap", billing.get("monthly_request_cap")),
            ),
        )


@dataclass(frozen=True)
class OrganizationIntegrationSettingsDocument:
    workspace_id: str | None
    account_id: str | None
    integration_settings: OrganizationIntegrationSettings
    billing_settings: AccountBillingSettings = field(default_factory=AccountBillingSettings)
    source: str = "default"
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "account_id": self.account_id,
            "source": self.source,
            "updated_at": self.updated_at,
            "integrations": self.integration_settings.to_dict(),
            "billing": self.billing_settings.to_dict(),
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
            billing_settings=AccountBillingSettings(),
            source=source,
            updated_at=_clean_identifier(item.get("updated_at")),
        )


class OrganizationIntegrationSettingsStore(Protocol):
    def get_settings_document(
        self,
        *,
        workspace_id: str | None,
        account_id: str | None,
    ) -> OrganizationIntegrationSettingsDocument | None:
        ...

    def put_settings_document(self, document: OrganizationIntegrationSettingsDocument) -> None:
        ...

    def load_billing_settings(self, *, account_id: str | None) -> tuple[AccountBillingSettings, str | None]:
        ...

    def store_billing_settings(
        self,
        *,
        account_id: str | None,
        settings: AccountBillingSettings,
        updated_at: str | None,
    ) -> None:
        ...


class OrganizationIntegrationSettingsService:
    def __init__(
        self,
        *,
        fallback_resolver: OrganizationIntegrationSettingsResolver,
        store: OrganizationIntegrationSettingsStore | None = None,
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
        billing_settings, billing_updated_at = self._get_billing_settings(account_id=context.account_id or account_id)
        source = "stored" if stored is not None or billing_updated_at is not None else "default"
        updated_at = _latest_updated_at(stored.updated_at if stored is not None else None, billing_updated_at)
        return OrganizationIntegrationSettingsDocument(
            workspace_id=context.workspace_id,
            account_id=context.account_id,
            integration_settings=self._with_supported_defaults(context.organization_integration_settings),
            billing_settings=billing_settings,
            source=source,
            updated_at=updated_at,
        )

    def allow_overage(self, account_id: str | None) -> bool:
        settings, _updated_at = self._get_billing_settings(account_id=account_id)
        return settings.allow_overage

    def monthly_request_limit(
        self,
        account_id: str | None,
        default_limit: int,
    ) -> int:
        settings, _updated_at = self._get_billing_settings(account_id=account_id)
        if settings.monthly_request_cap is None:
            return max(1, int(default_limit))
        return max(1, int(settings.monthly_request_cap))

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
        if "integrations" not in payload and "billing" not in payload:
            raise OrganizationIntegrationSettingsValidationError("Request body must include integrations or billing object")

        current = self.get_settings(workspace_id=workspace, account_id=account)
        updated_at = datetime.now(timezone.utc).isoformat()
        integration_settings = current.integration_settings
        billing_settings = current.billing_settings

        if "integrations" in payload:
            updates = self._parse_update_payload(payload)
            merged = OrganizationIntegrationSettings.from_mapping(
                {
                    **current.integration_settings.integrations,
                    **updates.integrations,
                }
            )
            validate_organization_integration_settings(merged, supported_integrations=self._supported_integrations)
            integration_settings = self._with_supported_defaults(merged)
            self._store.put_settings_document(
                OrganizationIntegrationSettingsDocument(
                    workspace_id=workspace or current.workspace_id,
                    account_id=account or current.account_id,
                    integration_settings=integration_settings,
                    billing_settings=current.billing_settings,
                    source="stored",
                    updated_at=updated_at,
                )
            )

        if "billing" in payload:
            if account is None and current.account_id is None:
                raise OrganizationIntegrationSettingsValidationError("account_id is required for billing settings")
            billing_settings = self._parse_billing_payload(
                payload,
                current=current.billing_settings,
            )
            self._store.store_billing_settings(
                account_id=account or current.account_id,
                settings=billing_settings,
                updated_at=updated_at,
            )

        return OrganizationIntegrationSettingsDocument(
            workspace_id=workspace or current.workspace_id,
            account_id=account or current.account_id,
            integration_settings=integration_settings,
            billing_settings=billing_settings,
            source="stored",
            updated_at=updated_at,
        )

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
        return self._store.get_settings_document(workspace_id=workspace_id, account_id=account_id)

    def _get_billing_settings(self, *, account_id: str | None) -> tuple[AccountBillingSettings, str | None]:
        if self._store is None:
            return AccountBillingSettings(), None
        return self._store.load_billing_settings(account_id=account_id)

    def _with_supported_defaults(self, settings: OrganizationIntegrationSettings) -> OrganizationIntegrationSettings:
        return OrganizationIntegrationSettings.from_mapping(
            {
                integration_id: settings.setting_for(integration_id)
                for integration_id in self._supported_integrations
            }
        )

    def _parse_billing_payload(
        self,
        payload: dict[str, Any],
        *,
        current: AccountBillingSettings,
    ) -> AccountBillingSettings:
        billing = payload.get("billing")
        if not isinstance(billing, dict):
            raise OrganizationIntegrationSettingsValidationError("Request body billing must be an object")
        if "allowOverage" not in billing and "allow_overage" not in billing:
            raise OrganizationIntegrationSettingsValidationError("billing.allowOverage is required")
        allow_overage = billing.get("allowOverage", billing.get("allow_overage"))
        if not isinstance(allow_overage, bool):
            raise OrganizationIntegrationSettingsValidationError("billing.allowOverage must be a boolean")
        monthly_request_cap = current.monthly_request_cap
        if "monthlyRequestCap" in billing or "monthly_request_cap" in billing:
            monthly_request_cap = billing.get(
                "monthlyRequestCap",
                billing.get("monthly_request_cap"),
            )
            if monthly_request_cap is not None and not isinstance(
                monthly_request_cap,
                int,
            ):
                raise OrganizationIntegrationSettingsValidationError(
                    "billing.monthlyRequestCap must be an integer or null",
                )
            if isinstance(monthly_request_cap, int) and monthly_request_cap < 1:
                raise OrganizationIntegrationSettingsValidationError(
                    "billing.monthlyRequestCap must be greater than 0",
                )
        return AccountBillingSettings(
            allow_overage=allow_overage,
            monthly_request_cap=monthly_request_cap,
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


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in {"true", "1", "yes"}:
            return True
        if candidate in {"false", "0", "no"}:
            return False
    return default


def _coerce_positive_int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        candidate = int(value.strip())
        return candidate if candidate > 0 else None
    return None


def _latest_updated_at(*values: str | None) -> str | None:
    candidates = [str(value).strip() for value in values if str(value or "").strip()]
    if not candidates:
        return None
    return max(candidates)

