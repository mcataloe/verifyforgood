from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from verification.backend.shared.billing.models import Entitlement
from verification.backend.shared.enrichments import EvaluationContext, OrganizationIntegrationSetting, OrganizationIntegrationSettings

from .identity_models import FeatureFlagKey, FeatureFlagRecord
from .identity_repositories import FeatureFlagRepository, OrganizationRepository, SubscriptionRepository
from .subscription_service import SubscriptionScaffoldingError, SubscriptionService

PLAN_DEFAULT_FEATURE_FLAGS: dict[str, tuple[FeatureFlagKey, ...]] = {
    "starter": (),
    "growth": (
        FeatureFlagKey.ENABLE_BULK_LOOKUP,
        FeatureFlagKey.ENABLE_ADVANCED_REPORTING,
    ),
    "enterprise": (
        FeatureFlagKey.ENABLE_BULK_LOOKUP,
        FeatureFlagKey.ENABLE_ADVANCED_REPORTING,
        FeatureFlagKey.ENABLE_CANDID,
        FeatureFlagKey.ENABLE_CHARITY_NAVIGATOR,
    ),
}

ORG_FEATURE_TO_ENTITLEMENT_FLAGS: dict[FeatureFlagKey, tuple[str, ...]] = {
    FeatureFlagKey.ENABLE_ADVANCED_REPORTING: ("financial_trends", "risk_flags"),
}

ORG_FEATURE_TO_CAPABILITIES: dict[FeatureFlagKey, tuple[str, ...]] = {
    FeatureFlagKey.ENABLE_BULK_LOOKUP: ("batch_verification",),
    FeatureFlagKey.ENABLE_ADVANCED_REPORTING: ("financial_trends", "risk_flags"),
}

ORG_FEATURE_TO_INTEGRATIONS: dict[FeatureFlagKey, str] = {
    FeatureFlagKey.ENABLE_CANDID: "candid",
    FeatureFlagKey.ENABLE_CHARITY_NAVIGATOR: "charity_navigator",
}

FLAG_KEYS: tuple[FeatureFlagKey, ...] = (
    FeatureFlagKey.ENABLE_CHARITY_NAVIGATOR,
    FeatureFlagKey.ENABLE_CANDID,
    FeatureFlagKey.ENABLE_BULK_LOOKUP,
    FeatureFlagKey.ENABLE_ADVANCED_REPORTING,
)


class FeatureFlagError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class ResolvedFeatureFlag:
    organization_id: str
    flag_key: FeatureFlagKey
    plan_id: str
    plan_default: bool
    override_enabled: bool | None
    enabled: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "organization_id": self.organization_id,
            "flag_key": self.flag_key.value,
            "plan_id": self.plan_id,
            "plan_default": self.plan_default,
            "override_enabled": self.override_enabled,
            "enabled": self.enabled,
        }


class FeatureFlagService:
    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        subscriptions: SubscriptionRepository,
        flags: FeatureFlagRepository,
        subscription_service: SubscriptionService,
    ) -> None:
        self._organizations = organizations
        self._subscriptions = subscriptions
        self._flags = flags
        self._subscription_service = subscription_service

    def get_override(self, *, organization_id: str, flag_key: str) -> FeatureFlagRecord | None:
        self._require_organization(organization_id)
        normalized_flag = _normalize_flag_key(flag_key)
        return self._flags.get(organization_id, normalized_flag.value)

    def set_override(self, *, organization_id: str, flag_key: str, enabled: bool) -> FeatureFlagRecord:
        self._require_organization(organization_id)
        normalized_flag = _normalize_flag_key(flag_key)
        existing = self._flags.get(organization_id, normalized_flag.value)
        now = _utc_now()
        return self._flags.put(
            FeatureFlagRecord(
                organization_id=organization_id,
                flag_key=normalized_flag,
                enabled=bool(enabled),
                created_at=existing.created_at if existing is not None else now,
                updated_at=now,
            )
        )

    def list_resolved_flags(self, *, organization_id: str) -> list[ResolvedFeatureFlag]:
        return [self.resolve_flag(organization_id=organization_id, flag_key=flag.value) for flag in FLAG_KEYS]

    def resolve_flag(self, *, organization_id: str, flag_key: str) -> ResolvedFeatureFlag:
        self._require_organization(organization_id)
        normalized_flag = _normalize_flag_key(flag_key)
        plan_id = self._resolve_plan_id(organization_id)
        plan_default = normalized_flag in PLAN_DEFAULT_FEATURE_FLAGS.get(plan_id, ())
        override = self._flags.get(organization_id, normalized_flag.value)
        override_enabled = override.enabled if override is not None else None
        enabled = override_enabled if override_enabled is not None else plan_default
        return ResolvedFeatureFlag(
            organization_id=organization_id,
            flag_key=normalized_flag,
            plan_id=plan_id,
            plan_default=plan_default,
            override_enabled=override_enabled,
            enabled=enabled,
        )

    def is_enabled(self, *, organization_id: str, flag_key: str) -> bool:
        return self.resolve_flag(organization_id=organization_id, flag_key=flag_key).enabled

    def ensure_enabled(self, *, organization_id: str, flag_key: str) -> None:
        resolved = self.resolve_flag(organization_id=organization_id, flag_key=flag_key)
        if not resolved.enabled:
            raise FeatureFlagError(f"{resolved.flag_key.value} is not enabled for this organization")

    def apply_entitlement_overrides(self, *, organization_id: str, entitlements: Entitlement) -> Entitlement:
        resolved = {flag.flag_key: flag for flag in self.list_resolved_flags(organization_id=organization_id)}
        feature_flags = set(entitlements.feature_flags)
        allowed_capabilities = set(entitlements.allowed_capabilities)
        request_limits = dict(entitlements.request_limits)

        for flag_key, mapped_flags in ORG_FEATURE_TO_ENTITLEMENT_FLAGS.items():
            if resolved[flag_key].enabled:
                feature_flags.update(mapped_flags)
            else:
                feature_flags.difference_update(mapped_flags)

        for flag_key, capabilities in ORG_FEATURE_TO_CAPABILITIES.items():
            if resolved[flag_key].enabled:
                allowed_capabilities.update(capabilities)
            else:
                allowed_capabilities.difference_update(capabilities)

        if resolved[FeatureFlagKey.ENABLE_BULK_LOOKUP].enabled:
            request_limits["batch_items"] = max(1, int(request_limits.get("batch_items", 0) or 0), 100)
        else:
            request_limits["batch_items"] = 0

        return replace(
            entitlements,
            feature_flags=tuple(sorted(feature_flags)),
            allowed_capabilities=tuple(sorted(allowed_capabilities)),
            request_limits=request_limits,
        )

    def apply_evaluation_context_overrides(self, *, organization_id: str, context: EvaluationContext) -> EvaluationContext:
        resolved = {flag.flag_key: flag for flag in self.list_resolved_flags(organization_id=organization_id)}
        merged = dict(context.organization_integration_settings.integrations)
        for flag_key, integration_id in ORG_FEATURE_TO_INTEGRATIONS.items():
            if resolved[flag_key].enabled:
                merged[integration_id] = OrganizationIntegrationSetting(enabled=True, required_for_eligibility=False)
            else:
                merged[integration_id] = OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False)
        return EvaluationContext(
            workspace_id=context.workspace_id,
            account_id=context.account_id,
            organization_integration_settings=OrganizationIntegrationSettings.from_mapping(merged),
        )

    def guard(self, flag_key: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        normalized_flag = _normalize_flag_key(flag_key)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                organization_id = kwargs.get("organization_id")
                if not isinstance(organization_id, str) or not organization_id.strip():
                    raise FeatureFlagError("organization_id is required for feature-guarded operations")
                self.ensure_enabled(organization_id=organization_id, flag_key=normalized_flag.value)
                return func(*args, **kwargs)

            return wrapped

        return decorator

    def _require_organization(self, organization_id: str) -> None:
        if self._organizations.get(organization_id) is None:
            raise FeatureFlagError("organization_id must reference an existing organization")

    def _resolve_plan_id(self, organization_id: str) -> str:
        subscription = self._subscriptions.get_by_organization(organization_id)
        if subscription is None:
            raise FeatureFlagError("Subscription was not found for this organization")
        try:
            return self._subscription_service.get_plan(subscription.plan_id).plan_id
        except SubscriptionScaffoldingError as exc:
            raise FeatureFlagError(str(exc)) from exc


def organization_feature_guard(service: FeatureFlagService, flag_key: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return service.guard(flag_key)


def service_level_feature_enabled(service: FeatureFlagService, *, organization_id: str, flag_key: str) -> bool:
    return service.is_enabled(organization_id=organization_id, flag_key=flag_key)


def _normalize_flag_key(flag_key: str) -> FeatureFlagKey:
    try:
        return FeatureFlagKey(str(flag_key or "").strip().lower())
    except Exception as exc:  # noqa: BLE001
        allowed = ", ".join(flag.value for flag in FLAG_KEYS)
        raise FeatureFlagError(f"flag_key must be one of: {allowed}") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

