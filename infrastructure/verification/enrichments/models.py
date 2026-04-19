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

INTEGRATION_ID_LABELS = {
    "candid": "Candid",
    "charity_navigator": "Charity Navigator",
}


def normalize_integration_id(value: str | None) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    return INTEGRATION_ID_ALIASES.get(candidate, candidate.lower())


def integration_id_display_name(integration_id: str) -> str:
    normalized = normalize_integration_id(integration_id)
    return INTEGRATION_ID_DISPLAY_NAMES.get(normalized, normalized)


def integration_id_label(integration_id: str) -> str:
    normalized = normalize_integration_id(integration_id)
    if not normalized:
        return "Integration"
    if normalized in INTEGRATION_ID_LABELS:
        return INTEGRATION_ID_LABELS[normalized]
    return normalized.replace("_", " ").title()


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
        explanation = explain_integration_state(
            {
                "integration_id": self.integration_id,
                "tenant_enabled": self.tenant_enabled,
                "required_for_eligibility": self.required_for_eligibility,
                "attempted": self.attempted,
                "availability_status": self.availability_status,
                "requirement_status": self.requirement_status,
                "credentials_present": self.credentials_present,
            }
        )
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
            "evaluation_effect": explanation["effect"],
            "explanation_code": explanation["code"],
            "explanation": explanation["message"],
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
        payload = {
            "integrations": [state.to_dict() for state in self.integrations],
            "attempted_integrations": self.attempted_integrations(),
            "used_integrations": self.used_integrations(),
            "required_unmet_integrations": self.required_unmet_integrations(),
            "failure_integrations": self.failure_integrations(),
        }
        return annotate_integration_evaluation_payload(payload)


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


def annotate_integration_evaluation_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(payload or {})
    annotated_integrations: list[dict[str, Any]] = []
    for raw_state in base.get("integrations", []) or []:
        if not isinstance(raw_state, dict):
            continue
        explanation = explain_integration_state(raw_state)
        annotated_state = {
            **raw_state,
            "evaluation_effect": raw_state.get("evaluation_effect") or explanation["effect"],
            "explanation_code": raw_state.get("explanation_code") or explanation["code"],
            "explanation": raw_state.get("explanation") or explanation["message"],
        }
        annotated_integrations.append(annotated_state)

    annotated = {
        **base,
        "integrations": annotated_integrations,
    }
    explanations = [
        {
            "integration_id": str(item.get("integration_id") or ""),
            "effect": str(item.get("evaluation_effect") or "neutral"),
            "code": str(item.get("explanation_code") or ""),
            "message": str(item.get("explanation") or ""),
            "availability_status": str(item.get("availability_status") or ""),
        }
        for item in annotated_integrations
        if str(item.get("integration_id") or "").strip()
    ]
    annotated["explanations"] = explanations
    annotated["summary"] = build_integration_policy_summary(annotated)
    return annotated


def build_integration_policy_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    evaluation = payload or {}
    explanations = evaluation.get("explanations") or []
    integrations = evaluation.get("integrations") or []
    attempted_integrations = evaluation.get("attempted_integrations") or []
    used_integrations = evaluation.get("used_integrations") or []
    required_unmet_integrations = evaluation.get("required_unmet_integrations") or []

    status = "neutral"
    if required_unmet_integrations:
        status = "required_unavailable"
    elif used_integrations:
        status = "evaluated"

    return {
        "status": status,
        "configured_count": len(integrations),
        "attempted_count": len(attempted_integrations),
        "successful_count": len(used_integrations),
        "required_unmet_count": len(required_unmet_integrations),
        "neutral_count": len([item for item in explanations if item.get("effect") == "neutral"]),
        "warning_count": len([item for item in explanations if item.get("effect") == "warning"]),
    }


def explain_integration_state(state: dict[str, Any]) -> dict[str, str]:
    integration_id = normalize_integration_id(str(state.get("integration_id") or ""))
    label = integration_id_label(integration_id)
    availability_status = str(state.get("availability_status") or "")
    required = bool(state.get("required_for_eligibility"))
    attempted = bool(state.get("attempted"))

    if availability_status == "not_offered":
        return {
            "code": "integration_not_offered",
            "effect": "neutral",
            "message": f"{label} is not offered by this platform deployment and was excluded from evaluation.",
        }
    if availability_status == "tenant_disabled":
        return {
            "code": "integration_disabled_for_organization",
            "effect": "neutral",
            "message": f"{label} is disabled for this organization and was ignored during evaluation.",
        }
    if required and str(state.get("requirement_status") or "") == "unmet":
        if availability_status == "no_match":
            detail = "no vendor record was available"
        elif availability_status == "failed":
            detail = "the integration could not be evaluated successfully"
        elif availability_status == "missing_credentials":
            detail = "platform credentials or configuration are unavailable"
        else:
            detail = "the integration was unavailable"
        return {
            "code": "integration_required_but_unavailable",
            "effect": "warning",
            "message": f"{label} is required for evaluation, but {detail}.",
        }
    if attempted and availability_status == "matched":
        return {
            "code": "integration_successfully_evaluated",
            "effect": "positive",
            "message": f"{label} was successfully evaluated and contributed available third-party data.",
        }
    if availability_status == "no_match":
        return {
            "code": "integration_optional_and_skipped",
            "effect": "neutral",
            "message": f"{label} is optional for this organization; no vendor data was found and evaluation continued without penalty.",
        }
    if availability_status == "missing_credentials":
        return {
            "code": "integration_optional_and_skipped",
            "effect": "neutral",
            "message": f"{label} is optional for this organization; platform credentials or configuration are unavailable and evaluation continued without penalty.",
        }
    if availability_status == "failed":
        return {
            "code": "integration_optional_and_skipped",
            "effect": "neutral",
            "message": f"{label} is optional for this organization; vendor data could not be retrieved and evaluation continued without penalty.",
        }
    return {
        "code": "integration_optional_and_skipped",
        "effect": "neutral",
        "message": f"{label} remained optional and had no effect on evaluation.",
    }
