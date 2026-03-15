from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EnrichmentStatus(str, Enum):
    MATCHED = "matched"
    NO_MATCH = "no_match"
    DISABLED = "disabled"
    FAILED = "failed"


INTEGRATION_ID_ALIASES = {
    "charitynavigator": "charity_navigator",
    "charity_navigator": "charity_navigator",
    "charity-navigator": "charity_navigator",
    "charityNavigator": "charity_navigator",
    "candid": "candid",
}

INTEGRATION_ID_DISPLAY_NAMES = {
    "charity_navigator": "charityNavigator",
}


def normalize_integration_id(value: str | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    return INTEGRATION_ID_ALIASES.get(candidate, candidate.lower())


def integration_id_display_name(integration_id: str) -> str:
    normalized = normalize_integration_id(integration_id)
    return INTEGRATION_ID_DISPLAY_NAMES.get(normalized, normalized)


@dataclass(frozen=True)
class EnrichmentProviderResult:
    name: str
    status: EnrichmentStatus
    provider_record_id: str | None
    fetched_at: str
    fields: dict[str, Any]
    source_payload: dict[str, Any] | None
    source: dict[str, Any]
    source_records: list[dict[str, Any]] | None = None
    capabilities: list[dict[str, Any]] | None = None
    integration_id: str | None = None
    driver: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "status": self.status.value,
            "fields": self.fields,
            "source": self.source,
        }
        if self.integration_id is not None:
            payload["integration_id"] = self.integration_id
        if self.driver is not None:
            payload["driver"] = self.driver
        if self.source_records is not None:
            payload["source_records"] = self.source_records
        if self.capabilities is not None:
            payload["capabilities"] = self.capabilities
        if self.error:
            payload["error"] = self.error
        if self.source_payload is not None:
            payload["source_payload"] = self.source_payload
        return payload


@dataclass(frozen=True)
class OrganizationIntegrationSetting:
    enabled: bool = False
    required_for_eligibility: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "requiredForEvaluation": self.required_for_eligibility,
            "required_for_evaluation": self.required_for_eligibility,
            "required_for_eligibility": self.required_for_eligibility,
        }

    @property
    def required_for_evaluation(self) -> bool:
        return self.required_for_eligibility


TenantIntegrationSetting = OrganizationIntegrationSetting


@dataclass(frozen=True)
class OrganizationIntegrationSettings:
    integrations: dict[str, OrganizationIntegrationSetting] = field(default_factory=dict)

    def setting_for(self, integration_id: str) -> OrganizationIntegrationSetting:
        return self.integrations.get(normalize_integration_id(integration_id), OrganizationIntegrationSetting())

    def integration_ids(self) -> list[str]:
        return sorted(self.integrations.keys())

    def has_non_default_integrations(self) -> bool:
        return any(
            setting.enabled or setting.required_for_eligibility
            for setting in self.integrations.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            integration_id_display_name(integration_id): setting.to_dict()
            for integration_id, setting in sorted(self.integrations.items())
        }

    @classmethod
    def from_mapping(cls, mapping: dict[str, OrganizationIntegrationSetting] | None) -> "OrganizationIntegrationSettings":
        if not mapping:
            return cls()
        normalized = {
            normalize_integration_id(integration_id): setting
            for integration_id, setting in mapping.items()
            if normalize_integration_id(integration_id)
        }
        return cls(integrations=normalized)


@dataclass(frozen=True)
class EvaluationContext:
    workspace_id: str | None = None
    account_id: str | None = None
    integration_settings: dict[str, OrganizationIntegrationSetting] = field(default_factory=dict)
    organization_integration_settings: OrganizationIntegrationSettings = field(default_factory=OrganizationIntegrationSettings)

    def __post_init__(self) -> None:
        legacy_settings = OrganizationIntegrationSettings.from_mapping(self.integration_settings)
        if isinstance(self.organization_integration_settings, dict):
            current_settings = OrganizationIntegrationSettings.from_mapping(self.organization_integration_settings)
        else:
            current_settings = self.organization_integration_settings
        merged_settings = OrganizationIntegrationSettings.from_mapping(
            {
                **legacy_settings.integrations,
                **current_settings.integrations,
            }
        )
        object.__setattr__(self, "organization_integration_settings", merged_settings)
        object.__setattr__(self, "integration_settings", merged_settings.integrations)

    def setting_for(self, integration_id: str) -> OrganizationIntegrationSetting:
        return self.organization_integration_settings.setting_for(integration_id)

    def has_non_default_integrations(self) -> bool:
        return self.organization_integration_settings.has_non_default_integrations()

    def integration_ids(self) -> list[str]:
        return self.organization_integration_settings.integration_ids()


@dataclass(frozen=True)
class IntegrationBinding:
    integration_id: str
    provider_name: str | None
    offered: bool
    driver: str
    credentials_present: bool
    endpoint: str | None = None


@dataclass(frozen=True)
class IntegrationState:
    integration_id: str
    offered: bool
    credentials_present: bool
    tenant_enabled: bool
    required_for_eligibility: bool
    attempted: bool
    availability_status: str
    requirement_status: str
    driver: str = "none"
    provider_name: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "integration_id": self.integration_id,
            "offered": self.offered,
            "credentials_present": self.credentials_present,
            "tenant_enabled": self.tenant_enabled,
            "required_for_eligibility": self.required_for_eligibility,
            "attempted": self.attempted,
            "availability_status": self.availability_status,
            "requirement_status": self.requirement_status,
            "driver": self.driver,
        }
        if self.provider_name is not None:
            payload["provider_name"] = self.provider_name
        if self.error is not None:
            payload["error"] = self.error
        return payload


@dataclass(frozen=True)
class IntegrationEvaluation:
    integrations: list[IntegrationState]

    def attempted_integrations(self) -> list[str]:
        return [state.integration_id for state in self.integrations if state.attempted]

    def used_integrations(self) -> list[str]:
        return [
            state.integration_id
            for state in self.integrations
            if state.attempted and state.availability_status == "matched"
        ]

    def required_unmet_integrations(self) -> list[str]:
        return [
            state.integration_id
            for state in self.integrations
            if state.required_for_eligibility and state.requirement_status == "unmet"
        ]

    def failure_integrations(self) -> list[str]:
        return [
            state.integration_id
            for state in self.integrations
            if state.attempted and state.availability_status == "failed"
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "integrations": [state.to_dict() for state in self.integrations],
            "attempted_integrations": self.attempted_integrations(),
            "used_integrations": self.used_integrations(),
            "required_unmet_integrations": self.required_unmet_integrations(),
            "failure_integrations": self.failure_integrations(),
        }


@dataclass(frozen=True)
class EnrichmentAggregateResult:
    providers: list[EnrichmentProviderResult]
    failures: list[dict[str, Any]]
    source_catalog: dict[str, Any] | None = None
    integration_evaluation: IntegrationEvaluation | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "providers": [provider.to_dict() for provider in self.providers],
            "failures": self.failures,
        }
        if self.source_catalog is not None:
            payload["source_catalog"] = self.source_catalog
        if self.integration_evaluation is not None:
            payload["integration_evaluation"] = self.integration_evaluation.to_dict()
        return payload



def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
