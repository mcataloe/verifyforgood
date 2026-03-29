from __future__ import annotations

import json
import logging
import os
import secrets
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs

import boto3
from charity_status.api import ResponseContext, build_response_context, error_response, json_response, normalize_route_key, strip_version_prefix
from charity_status.auth import (
    AuthenticationError,
    AuthorizationError,
    FeatureUnavailableError,
    QuotaExceededError,
    StaticApiKeyStore,
    StaticOAuthClientStore,
    StaticOAuthTokenStore,
    authenticate_admin_key,
    load_admin_key_store,
)
from charity_status.billing import (
    EntitlementService,
    ResponseShapingService,
    TrialLifecycleService,
    build_plan_catalog_payload,
    load_trial_config,
)
from charity_status.billing.checkout import BillingCheckoutError, BillingCheckoutService, load_stripe_checkout_config
from charity_status.billing.plan_changes import BillingPlanChangeError, BillingPlanChangeService
from charity_status.billing.portal import BillingPortalError, BillingPortalService
from charity_status.billing.visibility import BillingVisibilityService
from charity_status.billing.webhooks import BillingWebhookError, StripeWebhookService, load_stripe_webhook_config
from charity_status.billing.service import DEFAULT_PLANS
from charity_status.control_plane import ControlPlaneError, ControlPlaneService, DynamoControlPlaneStore, InMemoryControlPlaneStore
from charity_status.core.hooks import NoopAuthContextProvider, NoopQuotaMeteringHook
from charity_status.core.interfaces import AuthContextProvider, EnrichmentProviderGateway, OrganizationIntegrationSettingsStoreAdapter, ProfileStoreAdapter, QueryRepository, QuotaMeteringHook
from charity_status.core.models import AuthContext
from charity_status.enrichments import (
    DynamoOrganizationIntegrationSettingsStore,
    EvaluationContext,
    OrganizationIntegrationSettingsResolver,
    OrganizationIntegrationSettingsService,
    OrganizationIntegrationSettingsValidationError,
    load_organization_integration_settings,
)
from charity_status.enrichments.compliance import extract_state_compliance
from charity_status.enrichments.external_signals import extract_external_signals
from charity_status.platform import (
    ApiKeyAuthContextProvider,
    ApiKeyOrOAuthAuthContextProvider,
    ApiKeyQuotaMeteringHook,
    OAuthClientCredentialsService,
    QueryRuntimeConfig,
    RefreshRuntimeConfig,
    build_athena_client,
    build_enrichment_service,
    load_api_key_store,
    load_oauth_client_store,
    load_platform_integrations_config,
    load_oauth_token_store,
)
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.policy import evaluate_policy
from charity_status.query import VerificationInput, apply_evaluation_overlay, get_nonprofit_filings, search_nonprofit_summaries, verify_nonprofit
from charity_status.query.ops_views import (
    get_ingest_run,
    get_ingest_run_filings,
    get_nonprofit_pipeline_status,
    get_refresh_run,
    get_refresh_run_eins,
    list_ingest_runs,
    list_refresh_runs,
)
from charity_status.query.source_views import (
    get_nonprofit_compliance_view,
    get_nonprofit_federal_awards_view,
    get_nonprofit_single_source_view,
    get_nonprofit_sources_view,
)
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout
from charity_status.scoring import SCORING_MODEL_VERSION
from charity_status.serving import DynamoProfileStore, materialize_profile_item
from charity_status.serving.writer import MaterializedProfileWriter
from verification_platform.organization_verification.nonprofit_service import NonprofitService, TenantNonprofitContext
from charity_status_platform.customer_accounts import (
    ApiKeyCreateRequest,
    ApiKeyManagementError,
    ApiKeyService,
    AuditLogService,
    DynamoApiKeyRepository,
    DynamoAuditLogRepository,
    DynamoFeatureFlagRepository,
    DynamoUsageRepository,
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoPlanRepository,
    DynamoSubscriptionRepository,
    DynamoUserRepository,
    DynamoInvitationRepository,
    FeatureFlagService,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    MemberUpdateRequest,
    MembershipManagementError,
    MembershipManagementService,
    MembershipStatus,
    OrganizationBootstrapValidationError,
    OrganizationCreateRequest,
    OrganizationService,
    SubscriptionService,
    UsageService,
    usage_metrics_for_route,
)
from charity_status_platform.identity_access import (
    AuthService,
    BcryptPasswordHasher,
    HmacBearerTokenCodec,
    PortalAuthValidationError,
    UserCreateRequest,
    UserLoginRequest,
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() == "true"


def _env_optional_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.lower() == "true"


DATABASE = os.environ.get("DATABASE", "irs_nonprofits")
TABLE = os.environ.get("TABLE", "eo_bmf")
WORKGROUP = os.environ.get("WORKGROUP")
FORM990_FILINGS_TABLE = os.environ.get("FORM990_FILINGS_TABLE", "form990_metadata")
FORM990_METRICS_TABLE = os.environ.get("FORM990_METRICS_TABLE", "form990_metrics")
FORM990_GOVERNANCE_TABLE = os.environ.get("FORM990_GOVERNANCE_TABLE", "form990_governance")
FORM990_QUALITY_TABLE = os.environ.get("FORM990_QUALITY_TABLE", "form990_quality")

ENRICHMENT_TIMEOUT_SECONDS = int(os.environ.get("ENRICHMENT_TIMEOUT_SECONDS", "5"))
PLATFORM_INTEGRATIONS = load_platform_integrations_config(os.environ)
PROFILE_TABLE_NAME = os.environ.get("PROFILE_TABLE_NAME")
CONTROL_PLANE_TABLE_NAME = os.environ.get("CONTROL_PLANE_TABLE_NAME", "").strip()
ORGANIZATION_SETTINGS_TABLE_NAME = os.environ.get("ORGANIZATION_SETTINGS_TABLE_NAME", "").strip()
APP_ENV = os.environ.get("APP_ENV", "dev")
SERVING_DDB_ENABLED = _env_bool("SERVING_DDB_ENABLED")
BATCH_VERIFY_MAX_SIZE = int(os.environ.get("BATCH_VERIFY_MAX_SIZE", "25"))
SEARCH_MAX_LIMIT = int(os.environ.get("SEARCH_MAX_LIMIT", "50"))
SEARCH_DEFAULT_LIMIT = int(os.environ.get("SEARCH_DEFAULT_LIMIT", "20"))
API_AUTH_ENABLED = _env_bool("API_AUTH_ENABLED")
API_KEY_RECORDS_JSON = os.environ.get("API_KEY_RECORDS_JSON", "")
OAUTH_M2M_ENABLED = _env_bool("OAUTH_M2M_ENABLED")
OAUTH_TOKEN_RECORDS_JSON = os.environ.get("OAUTH_TOKEN_RECORDS_JSON", "")
OAUTH_CLIENT_RECORDS_JSON = os.environ.get("OAUTH_CLIENT_RECORDS_JSON", "")
OAUTH_TOKEN_TTL_SECONDS = int(os.environ.get("OAUTH_TOKEN_TTL_SECONDS", "3600"))
ADMIN_KEY_RECORDS_JSON = os.environ.get("ADMIN_KEY_RECORDS_JSON", "")
OPS_METADATA_BUCKET = os.environ.get("OPS_METADATA_BUCKET", "").strip()
OPS_METADATA_PREFIX = os.environ.get("OPS_METADATA_PREFIX", "ops").strip()
FORM990_ORCHESTRATOR_FUNCTION_NAME = os.environ.get("FORM990_ORCHESTRATOR_FUNCTION_NAME", "").strip()
IDENTITY_TABLE_NAME = os.environ.get("IDENTITY_TABLE_NAME", "identity").strip() or "identity"
PORTAL_AUTH_TOKEN_SECRET = os.environ.get("PORTAL_AUTH_TOKEN_SECRET", "dev-portal-auth-secret")
PORTAL_AUTH_TOKEN_TTL_SECONDS = int(os.environ.get("PORTAL_AUTH_TOKEN_TTL_SECONDS", "86400"))
ORGANIZATION_INTEGRATION_SETTINGS_JSON = os.environ.get(
    "ORGANIZATION_INTEGRATION_SETTINGS_JSON",
    os.environ.get("TENANT_INTEGRATION_SETTINGS_JSON", ""),
)
STRIPE_CHECKOUT_CONFIG = load_stripe_checkout_config(os.environ)
STRIPE_WEBHOOK_CONFIG = load_stripe_webhook_config(os.environ)
TRIAL_CONFIG = load_trial_config(os.environ)

athena_client: QueryRepository | None = None
enrichment_service: EnrichmentProviderGateway | None = None
profile_store: ProfileStoreAdapter | None = None
auth_context_provider: AuthContextProvider | None = None
quota_metering_hook: QuotaMeteringHook | None = None
usage_store: Any | None = None
ops_run_store: Any | None = None
lambda_invoke_client: Any | None = None
tenant_integration_settings_resolver: OrganizationIntegrationSettingsResolver | None = None
organization_integration_settings_store: OrganizationIntegrationSettingsStoreAdapter | None = None
organization_integration_settings_service: OrganizationIntegrationSettingsService | None = None
oauth_client_credentials_service: OAuthClientCredentialsService | None = None
control_plane_service: ControlPlaneService | None = None
entitlement_service: EntitlementService | None = None
response_shaping_service: ResponseShapingService | None = None
billing_checkout_service: BillingCheckoutService | None = None
billing_plan_change_service: BillingPlanChangeService | None = None
billing_portal_service: BillingPortalService | None = None
billing_visibility_service: BillingVisibilityService | None = None
stripe_webhook_service: StripeWebhookService | None = None
trial_lifecycle_service: TrialLifecycleService | None = None
portal_auth_service: AuthService | None = None
portal_organization_service: OrganizationService | None = None
portal_membership_service: MembershipManagementService | None = None
portal_api_key_service: ApiKeyService | None = None
portal_usage_service: UsageService | None = None
portal_subscription_service: SubscriptionService | None = None
portal_feature_flag_service: FeatureFlagService | None = None
portal_audit_log_service: AuditLogService | None = None
nonprofit_service: NonprofitService | None = None
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _get_athena_client() -> QueryRepository:
    global athena_client
    if athena_client is None:
        athena_client = build_athena_client(
            QueryRuntimeConfig(
                database=DATABASE,
                table=TABLE,
                workgroup=WORKGROUP,
                form990_filings_table=FORM990_FILINGS_TABLE,
                form990_metrics_table=FORM990_METRICS_TABLE,
                form990_governance_table=FORM990_GOVERNANCE_TABLE,
                form990_quality_table=FORM990_QUALITY_TABLE,
            )
        )
    return athena_client


def _get_enrichment_service() -> EnrichmentProviderGateway:
    global enrichment_service
    if enrichment_service is None:
        enrichment_service = build_enrichment_service(
            RefreshRuntimeConfig(
                database=DATABASE,
                table=TABLE,
                workgroup=WORKGROUP,
                form990_filings_table=FORM990_FILINGS_TABLE,
                form990_metrics_table=FORM990_METRICS_TABLE,
                form990_governance_table=FORM990_GOVERNANCE_TABLE,
                form990_quality_table=FORM990_QUALITY_TABLE,
                platform_integrations=PLATFORM_INTEGRATIONS,
                enrichment_timeout_seconds=ENRICHMENT_TIMEOUT_SECONDS,
                enrichment_mock_offered=_env_optional_bool("ENRICHMENT_MOCK_OFFERED"),
                enrichment_mock_enabled=_env_bool("ENRICHMENT_MOCK_ENABLED"),
                enrichment_candid_offered=_env_optional_bool("ENRICHMENT_CANDID_OFFERED"),
                enrichment_candid_enabled=_env_bool("ENRICHMENT_CANDID_ENABLED"),
                enrichment_candid_api_key=os.environ.get("ENRICHMENT_CANDID_API_KEY"),
                enrichment_candid_endpoint=os.environ.get("ENRICHMENT_CANDID_ENDPOINT"),
                enrichment_state_registry_offered=_env_optional_bool("ENRICHMENT_STATE_REGISTRY_OFFERED"),
                enrichment_state_registry_enabled=_env_bool("ENRICHMENT_STATE_REGISTRY_ENABLED"),
                enrichment_state_registry_mock_enabled=_env_bool("ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED"),
                enrichment_state_registry_endpoint=os.environ.get("ENRICHMENT_STATE_REGISTRY_ENDPOINT"),
                enrichment_state_registry_colorado_enabled=_env_bool("ENRICHMENT_STATE_REGISTRY_COLORADO_ENABLED"),
                enrichment_state_registry_colorado_app_token=os.environ.get("ENRICHMENT_STATE_REGISTRY_COLORADO_APP_TOKEN"),
                enrichment_state_registry_kentucky_enabled=_env_bool("ENRICHMENT_STATE_REGISTRY_KENTUCKY_ENABLED"),
                enrichment_state_registry_kentucky_companies_url=os.environ.get("ENRICHMENT_STATE_REGISTRY_KENTUCKY_COMPANIES_URL"),
                enrichment_state_business_offered=_env_optional_bool("ENRICHMENT_STATE_BUSINESS_OFFERED"),
                enrichment_state_business_enabled=_env_bool("ENRICHMENT_STATE_BUSINESS_ENABLED"),
                enrichment_state_business_mock_enabled=_env_bool("ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED"),
                enrichment_state_business_endpoint=os.environ.get("ENRICHMENT_STATE_BUSINESS_ENDPOINT"),
                enrichment_usaspending_offered=_env_optional_bool("ENRICHMENT_USASPENDING_OFFERED"),
                enrichment_usaspending_enabled=_env_bool("ENRICHMENT_USASPENDING_ENABLED"),
                enrichment_usaspending_mock_enabled=_env_bool("ENRICHMENT_USASPENDING_MOCK_ENABLED"),
                enrichment_usaspending_endpoint=os.environ.get("ENRICHMENT_USASPENDING_ENDPOINT"),
                enrichment_ofac_offered=_env_optional_bool("ENRICHMENT_OFAC_OFFERED"),
                enrichment_ofac_enabled=_env_bool("ENRICHMENT_OFAC_ENABLED"),
                enrichment_ofac_mock_enabled=_env_bool("ENRICHMENT_OFAC_MOCK_ENABLED"),
                enrichment_ofac_endpoint=os.environ.get("ENRICHMENT_OFAC_ENDPOINT"),
            )
        )
    return enrichment_service


def _get_nonprofit_service() -> NonprofitService:
    global nonprofit_service
    if nonprofit_service is None:
        nonprofit_service = NonprofitService(
            client=_get_athena_client(),
            enrichment_service=_get_enrichment_service(),
        )
    return nonprofit_service


def _get_profile_store() -> ProfileStoreAdapter | None:
    global profile_store
    if not SERVING_DDB_ENABLED or not PROFILE_TABLE_NAME:
        return None
    if profile_store is None:
        profile_store = DynamoProfileStore(table_name=PROFILE_TABLE_NAME)
    return profile_store


def _get_auth_context_provider() -> AuthContextProvider:
    global auth_context_provider
    if not API_AUTH_ENABLED:
        if auth_context_provider is None:
            auth_context_provider = NoopAuthContextProvider()
        return auth_context_provider

    api_key_store = _load_runtime_api_key_store()
    if OAUTH_M2M_ENABLED:
        return ApiKeyOrOAuthAuthContextProvider(
            api_key_store=api_key_store,
            oauth_token_store=_load_runtime_oauth_token_store(),
            oauth_client_store=_load_runtime_oauth_client_store(),
            entitlement_service=_get_entitlement_service(),
        )
    return ApiKeyAuthContextProvider(api_key_store, entitlement_service=_get_entitlement_service())


def _get_quota_metering_hook() -> QuotaMeteringHook:
    global quota_metering_hook, usage_store
    if quota_metering_hook is None:
        if API_AUTH_ENABLED:
            usage_store = usage_store or _get_control_plane_service().store
            usage_service = _get_portal_usage_service()
            quota_metering_hook = ApiKeyQuotaMeteringHook(
                usage_store=usage_store,
                entitlement_service=_get_entitlement_service(),
                billing_settings_resolver=_get_organization_integration_settings_service(),
                trial_lifecycle_service=_get_trial_lifecycle_service(),
                organization_usage_tracker=_PortalOrganizationUsageTracker(usage_service) if usage_service is not None else None,
                organization_feature_service=_get_portal_feature_flag_service(),
            )
        else:
            quota_metering_hook = NoopQuotaMeteringHook()
    return quota_metering_hook


def _get_oauth_client_credentials_service() -> OAuthClientCredentialsService:
    global oauth_client_credentials_service
    oauth_client_credentials_service = OAuthClientCredentialsService(
        _load_runtime_oauth_client_store(),
        token_ttl_seconds=OAUTH_TOKEN_TTL_SECONDS,
        entitlement_service=_get_entitlement_service(),
    )
    return oauth_client_credentials_service


def _get_admin_key_store():
    return load_admin_key_store(ADMIN_KEY_RECORDS_JSON)


def _get_control_plane_service() -> ControlPlaneService:
    global control_plane_service
    if control_plane_service is None:
        if CONTROL_PLANE_TABLE_NAME:
            control_plane_service = ControlPlaneService(store=DynamoControlPlaneStore(table_name=CONTROL_PLANE_TABLE_NAME))
        else:
            control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    return control_plane_service


def _get_entitlement_service() -> EntitlementService:
    global entitlement_service
    if entitlement_service is None:
        entitlement_service = EntitlementService(
            subscription_loader=_load_runtime_subscription,
            trial_config=TRIAL_CONFIG,
        )
    return entitlement_service


def _get_response_shaping_service() -> ResponseShapingService:
    global response_shaping_service
    if response_shaping_service is None:
        response_shaping_service = ResponseShapingService()
    return response_shaping_service


def _get_billing_checkout_service() -> BillingCheckoutService:
    global billing_checkout_service
    if billing_checkout_service is None:
        billing_checkout_service = BillingCheckoutService(
            store=_get_control_plane_service().store,
            config=STRIPE_CHECKOUT_CONFIG,
        )
    return billing_checkout_service


def _get_billing_plan_change_service() -> BillingPlanChangeService:
    global billing_plan_change_service
    if billing_plan_change_service is None:
        billing_plan_change_service = BillingPlanChangeService(
            store=_get_control_plane_service().store,
            config=STRIPE_CHECKOUT_CONFIG,
        )
    return billing_plan_change_service


def _get_billing_portal_service() -> BillingPortalService:
    global billing_portal_service
    if billing_portal_service is None:
        billing_portal_service = BillingPortalService(
            store=_get_control_plane_service().store,
            config=STRIPE_CHECKOUT_CONFIG,
        )
    return billing_portal_service


def _get_billing_visibility_service() -> BillingVisibilityService:
    global billing_visibility_service
    if billing_visibility_service is None:
        billing_visibility_service = BillingVisibilityService(
            store=_get_control_plane_service().store,
            entitlement_service=_get_entitlement_service(),
            trial_lifecycle_service=_get_trial_lifecycle_service(),
        )
    return billing_visibility_service


def _get_stripe_webhook_service() -> StripeWebhookService:
    global stripe_webhook_service
    if stripe_webhook_service is None:
        stripe_webhook_service = StripeWebhookService(
            store=_get_control_plane_service().store,
            config=STRIPE_WEBHOOK_CONFIG,
            trial_lifecycle_service=_get_trial_lifecycle_service(),
        )
    return stripe_webhook_service


def _get_trial_lifecycle_service() -> TrialLifecycleService:
    global trial_lifecycle_service
    if trial_lifecycle_service is None:
        trial_lifecycle_service = TrialLifecycleService(
            store=_get_control_plane_service().store,
            config=TRIAL_CONFIG,
        )
    return trial_lifecycle_service


def _get_portal_audit_log_service() -> AuditLogService:
    global portal_audit_log_service
    if portal_audit_log_service is None:
        portal_audit_log_service = AuditLogService(
            repository=DynamoAuditLogRepository(table_name=IDENTITY_TABLE_NAME),
            logger=logger,
        )
    return portal_audit_log_service


def _get_portal_auth_service() -> AuthService:
    global portal_auth_service
    if portal_auth_service is None:
        portal_auth_service = AuthService(
            users=DynamoUserRepository(table_name=IDENTITY_TABLE_NAME),
            password_hasher=BcryptPasswordHasher(),
            token_codec=HmacBearerTokenCodec(
                secret=PORTAL_AUTH_TOKEN_SECRET,
                token_ttl_seconds=PORTAL_AUTH_TOKEN_TTL_SECONDS,
            ),
            audit_log_service=_get_portal_audit_log_service(),
        )
    return portal_auth_service


def _get_portal_usage_service() -> UsageService | None:
    global portal_usage_service
    if portal_usage_service is None:
        try:
            portal_usage_service = UsageService(
                organizations=DynamoOrganizationRepository(table_name=IDENTITY_TABLE_NAME),
                usage=DynamoUsageRepository(table_name=IDENTITY_TABLE_NAME),
            )
        except Exception:  # noqa: BLE001
            return None
    return portal_usage_service


def _get_portal_subscription_service() -> SubscriptionService | None:
    global portal_subscription_service
    if portal_subscription_service is None:
        try:
            portal_subscription_service = SubscriptionService(
                organizations=DynamoOrganizationRepository(table_name=IDENTITY_TABLE_NAME),
                plans=DynamoPlanRepository(table_name=IDENTITY_TABLE_NAME),
                subscriptions=DynamoSubscriptionRepository(table_name=IDENTITY_TABLE_NAME),
            )
        except Exception:  # noqa: BLE001
            return None
    return portal_subscription_service


def _get_portal_feature_flag_service() -> FeatureFlagService | None:
    global portal_feature_flag_service
    if portal_feature_flag_service is None:
        subscription_service = _get_portal_subscription_service()
        if subscription_service is None:
            return None
        try:
            portal_feature_flag_service = FeatureFlagService(
                organizations=DynamoOrganizationRepository(table_name=IDENTITY_TABLE_NAME),
                subscriptions=DynamoSubscriptionRepository(table_name=IDENTITY_TABLE_NAME),
                flags=DynamoFeatureFlagRepository(table_name=IDENTITY_TABLE_NAME),
                subscription_service=subscription_service,
            )
        except Exception:  # noqa: BLE001
            return None
    return portal_feature_flag_service


def _get_portal_organization_service() -> OrganizationService:
    global portal_organization_service
    if portal_organization_service is None:
        portal_organization_service = OrganizationService(
            users=DynamoUserRepository(table_name=IDENTITY_TABLE_NAME),
            organizations=DynamoOrganizationRepository(table_name=IDENTITY_TABLE_NAME),
            memberships=DynamoMembershipRepository(table_name=IDENTITY_TABLE_NAME),
            audit_log_service=_get_portal_audit_log_service(),
        )
    return portal_organization_service


def _get_portal_membership_service() -> MembershipManagementService:
    global portal_membership_service
    if portal_membership_service is None:
        portal_membership_service = MembershipManagementService(
            users=DynamoUserRepository(table_name=IDENTITY_TABLE_NAME),
            organizations=DynamoOrganizationRepository(table_name=IDENTITY_TABLE_NAME),
            memberships=DynamoMembershipRepository(table_name=IDENTITY_TABLE_NAME),
            invitations=DynamoInvitationRepository(table_name=IDENTITY_TABLE_NAME),
            audit_log_service=_get_portal_audit_log_service(),
        )
    return portal_membership_service


def _get_portal_api_key_service() -> ApiKeyService:
    global portal_api_key_service
    if portal_api_key_service is None:
        portal_api_key_service = ApiKeyService(
            organizations=DynamoOrganizationRepository(table_name=IDENTITY_TABLE_NAME),
            memberships=DynamoMembershipRepository(table_name=IDENTITY_TABLE_NAME),
            api_keys=DynamoApiKeyRepository(table_name=IDENTITY_TABLE_NAME),
            audit_log_service=_get_portal_audit_log_service(),
        )
    return portal_api_key_service


def _load_runtime_api_key_store() -> StaticApiKeyStore:
    return _MergedApiKeyStore(
        _ManagedOrganizationApiKeyStore(),
        _ManagedApiKeyStore(_get_control_plane_service().store),
        load_api_key_store(API_KEY_RECORDS_JSON),
    )


def _load_runtime_oauth_token_store() -> StaticOAuthTokenStore:
    return load_oauth_token_store(OAUTH_TOKEN_RECORDS_JSON)


def _load_runtime_oauth_client_store() -> StaticOAuthClientStore:
    return _MergedOAuthClientStore(
        _ManagedOAuthClientStore(_get_control_plane_service().store),
        load_oauth_client_store(OAUTH_CLIENT_RECORDS_JSON),
    )


def _load_runtime_subscription(account_id: str):
    store = _get_control_plane_service().store
    subscription = store.get_subscription(account_id)
    if subscription is None:
        return None
    return subscription.to_subscription()


class _ManagedApiKeyStore:
    def __init__(self, store: Any) -> None:
        self._store = store

    def get(self, key_id: str):
        return self._store.get_api_key_record(key_id)


class _ManagedOrganizationApiKeyStore:
    def __init__(self, repository: DynamoApiKeyRepository | None = None) -> None:
        self._repository = repository

    def _get_repository(self) -> DynamoApiKeyRepository | None:
        if self._repository is not None:
            return self._repository
        try:
            self._repository = DynamoApiKeyRepository(table_name=IDENTITY_TABLE_NAME)
        except Exception:  # noqa: BLE001
            return None
        return self._repository

    def get(self, key_id: str):
        repository = self._get_repository()
        if repository is None:
            return None
        try:
            record = repository.get_by_key_id(key_id)
        except Exception:  # noqa: BLE001
            return None
        if record is None:
            return None
        return _to_stored_api_key_record(record)

    def touch_last_used(self, key_id: str):
        repository = self._get_repository()
        if repository is None:
            return None
        try:
            repository.touch_last_used(key_id, used_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat())
        except Exception:  # noqa: BLE001
            return None

    def get_organization_id(self, key_id: str):
        repository = self._get_repository()
        if repository is None:
            return None
        try:
            record = repository.get_by_key_id(key_id)
        except Exception:  # noqa: BLE001
            return None
        if record is None:
            return None
        return record.organization_id


class _MergedApiKeyStore:
    def __init__(self, primary: Any, secondary: Any, fallback: StaticApiKeyStore) -> None:
        self._primary = primary
        self._secondary = secondary
        self._fallback = fallback

    def get(self, key_id: str):
        return self._primary.get(key_id) or self._secondary.get(key_id) or self._fallback.get(key_id)

    def touch_last_used(self, key_id: str):
        touch_last_used = getattr(self._primary, "touch_last_used", None)
        if callable(touch_last_used):
            touch_last_used(key_id)

    def get_organization_id(self, key_id: str):
        get_organization_id = getattr(self._primary, "get_organization_id", None)
        if callable(get_organization_id):
            return get_organization_id(key_id)
        return None


class _PortalOrganizationUsageTracker:
    def __init__(self, usage_service: UsageService) -> None:
        self._usage_service = usage_service

    def record_usage(self, *, organization_id: str, route_key: str, billable_units: int, period_month: str) -> None:
        for metric in usage_metrics_for_route(route_key):
            self._usage_service.increment_metric(
                organization_id=organization_id,
                metric_type=metric.value,
                period_month=period_month,
                units=billable_units,
            )


class _ManagedOAuthClientStore:
    def __init__(self, store: Any) -> None:
        self._store = store

    def get(self, client_id: str):
        return self._store.get_oauth_client_record(client_id)


class _MergedOAuthClientStore:
    def __init__(self, primary: Any, fallback: StaticOAuthClientStore) -> None:
        self._primary = primary
        self._fallback = fallback

    def get(self, client_id: str):
        return self._primary.get(client_id) or self._fallback.get(client_id)


def _to_stored_api_key_record(record):
    from charity_status.auth.service import StoredApiKeyRecord

    return StoredApiKeyRecord(
        key_id=record.key_id,
        secret_hash=record.hashed_key_value,
        account_id=record.organization_id,
        workspace_id=record.organization_id,
        scopes=(
            "verify:read",
            "verify:write",
            "nonprofits:read",
            "sources:read",
            "compliance:read",
            "federal_awards:read",
        ),
        revoked=record.status.value != "active",
        plan_id="free",
        rate_limit_profile="free",
    )


def _get_ops_run_store() -> Any | None:
    global ops_run_store
    if not OPS_METADATA_BUCKET:
        return None
    if ops_run_store is None:
        ops_run_store = S3RunStore(bucket=OPS_METADATA_BUCKET, prefix=OPS_METADATA_PREFIX, s3_client=boto3.client("s3"))
    return ops_run_store


def _get_lambda_invoke_client() -> Any:
    global lambda_invoke_client
    if lambda_invoke_client is None:
        lambda_invoke_client = boto3.client("lambda")
    return lambda_invoke_client


def _get_organization_integration_settings_store() -> OrganizationIntegrationSettingsStoreAdapter | None:
    global organization_integration_settings_store
    if not ORGANIZATION_SETTINGS_TABLE_NAME:
        return None
    if organization_integration_settings_store is None:
        organization_integration_settings_store = DynamoOrganizationIntegrationSettingsStore(table_name=ORGANIZATION_SETTINGS_TABLE_NAME)
    return organization_integration_settings_store


def _get_tenant_integration_settings_resolver() -> OrganizationIntegrationSettingsResolver:
    global tenant_integration_settings_resolver
    if tenant_integration_settings_resolver is None:
        tenant_integration_settings_resolver = load_organization_integration_settings(
            ORGANIZATION_INTEGRATION_SETTINGS_JSON,
            default_settings=PLATFORM_INTEGRATIONS.organization_default_settings(),
        )
    return tenant_integration_settings_resolver


def _get_organization_integration_settings_service() -> OrganizationIntegrationSettingsService:
    global organization_integration_settings_service
    if organization_integration_settings_service is None:
        organization_integration_settings_service = OrganizationIntegrationSettingsService(
            fallback_resolver=_get_tenant_integration_settings_resolver(),
            store=_get_organization_integration_settings_store(),
        )
    return organization_integration_settings_service


def _resolve_evaluation_context(auth_context: Any) -> EvaluationContext:
    context = _get_organization_integration_settings_service().resolve_context(
        workspace_id=getattr(auth_context, "workspace_id", None),
        account_id=getattr(auth_context, "account_id", None),
    )
    metadata = getattr(auth_context, "metadata", {}) or {}
    organization_id = metadata.get("organization_id")
    if metadata.get("tenant_scoped_request") != "true" or not organization_id:
        return context
    feature_service = _get_portal_feature_flag_service()
    if feature_service is None:
        return context
    try:
        return feature_service.apply_evaluation_context_overrides(
            organization_id=str(organization_id),
            context=context,
        )
    except Exception:  # noqa: BLE001
        return context


def _is_tenant_nonprofit_request(event: dict[str, Any], method: str) -> bool:
    return any(
        checker(event, method)
        for checker in (
            _is_search_request,
            _is_sources_list_request,
            _is_sources_detail_request,
            _is_compliance_request,
            _is_federal_awards_request,
            _is_filings_request,
            _is_lookup_request,
        )
    )


def _is_lookup_request(event: dict[str, Any], method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    candidate = resource or path
    if candidate.endswith("/nonprofit/{ein}") or candidate.endswith("/nonprofit/{ein}/"):
        return True
    path_params = event.get("pathParameters") or {}
    return bool(path_params.get("ein"))


def _build_portal_session_auth_context(*, organization_id: str, user_id: str) -> AuthContext:
    plan_code = "free"
    subscription_service = _get_portal_subscription_service()
    if subscription_service is not None:
        try:
            resolved = subscription_service.get_subscription_for_organization(organization_id)
            plan_code = str(resolved.subscription.plan.plan_id)
        except Exception:  # noqa: BLE001
            plan_code = "free"
    entitlements = DEFAULT_PLANS.get(plan_code, DEFAULT_PLANS["free"]).entitlements
    return AuthContext(
        account_id=organization_id,
        credential_id=user_id,
        auth_method="portal_session",
        plan=plan_code,
        scopes=("verify:read", "nonprofits:read", "sources:read"),
        rate_limit_profile=plan_code,
        workspace_id=organization_id,
        subject=f"portal_session:{user_id}",
        entitlements=entitlements,
        metadata={
            "organization_id": organization_id,
            "portal_session": "true",
            "tenant_scoped_request": "true",
        },
    )


def _build_tenant_nonprofit_context(auth_context: Any) -> TenantNonprofitContext:
    metadata = getattr(auth_context, "metadata", {}) or {}
    organization_id = str(metadata.get("organization_id") or "").strip()
    if not organization_id:
        raise AuthorizationError("Tenant nonprofit routes require organization-scoped authentication")
    return TenantNonprofitContext(
        organization_id=organization_id,
        authenticated_subject=str(getattr(auth_context, "subject", "") or ""),
        authenticated_user_id=(str(getattr(auth_context, "credential_id", "") or "") if getattr(auth_context, "auth_method", "") == "portal_session" else None),
        auth_method=str(getattr(auth_context, "auth_method", "") or ""),
        credential_id=(str(getattr(auth_context, "credential_id", "") or "") or None),
        metadata=dict(metadata),
    )


def _resolve_tenant_nonprofit_auth_context(event: dict[str, Any]) -> AuthContext:
    headers = event.get("headers") or {}
    authorization = str(_get_header(headers, "authorization") or "").strip()
    has_current_org_headers = bool(_get_header(headers, "x-portal-account-id") or _get_header(headers, "x-portal-workspace-id"))
    if authorization.lower().startswith("bearer ") and has_current_org_headers:
        try:
            current_user = _get_portal_auth_service().get_current_user(authorization)
            try:
                organization_id, workspace_id = _resolve_current_portal_context(event)
            except MembershipManagementError as exc:
                raise AuthorizationError(str(exc)) from exc
            if organization_id != workspace_id:
                raise AuthorizationError("Current organization headers must identify the same scope")
            membership = DynamoMembershipRepository(table_name=IDENTITY_TABLE_NAME).get(organization_id, current_user.user_id)
            if membership is None or membership.status != MembershipStatus.ACTIVE:
                raise AuthorizationError("Active membership is required for nonprofit queries")
            return _build_portal_session_auth_context(organization_id=organization_id, user_id=current_user.user_id)
        except AuthenticationError:
            pass

    auth_context = _get_auth_context_provider().extract_context(event or {})
    if str(getattr(auth_context, "auth_method", "") or "") == "anonymous":
        if authorization.lower().startswith("bearer "):
            raise AuthorizationError("Current organization headers are required")
        raise AuthenticationError("Authentication required")
    metadata = getattr(auth_context, "metadata", None)
    if not isinstance(metadata, dict) or not str(metadata.get("organization_id") or "").strip():
        raise AuthorizationError("Tenant nonprofit routes require organization-scoped authentication")
    metadata["tenant_scoped_request"] = "true"
    return auth_context


def _handle_oauth_token_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    if not OAUTH_M2M_ENABLED:
        return error_response(404, "OAuth token endpoint is not enabled", response_context=response_context, code="not_found")
    try:
        client_id, client_secret = _parse_oauth_token_request(event)
        auth_context, token_payload = _get_oauth_client_credentials_service().issue_token(client_id, client_secret)
        event["_auth_context"] = auth_context
        token_context = ResponseContext(
            request_id=response_context.request_id,
            plan=str(auth_context.plan or "public"),
            deprecation=response_context.deprecation,
            cors_origin=response_context.cors_origin,
        )
        return json_response(200, token_payload, response_context=token_context)
    except AuthenticationError as exc:
        return error_response(exc.status_code, str(exc), response_context=response_context, code="invalid_client")
    except ValueError as exc:
        return error_response(400, str(exc), response_context=response_context, code="invalid_request")


def _parse_oauth_token_request(event: dict[str, Any]) -> tuple[str, str]:
    headers = event.get("headers") or {}
    content_type = str(_get_header(headers, "content-type") or "").lower()
    body = str(event.get("body") or "")
    if not body:
        raise ValueError("Request body is required")

    if "application/x-www-form-urlencoded" in content_type:
        params = parse_qs(body, keep_blank_values=True)
        client_id = str((params.get("client_id") or [""])[0]).strip()
        client_secret = str((params.get("client_secret") or [""])[0]).strip()
    else:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")
        client_id = str(payload.get("client_id") or "").strip()
        client_secret = str(payload.get("client_secret") or "").strip()

    if not client_id or not client_secret:
        raise ValueError("client_id and client_secret are required")
    return client_id, client_secret


def _parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if not body:
        raise ValueError("Request body is required")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    return payload


def _parse_optional_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, str) and not body.strip():
        return {}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    return payload


def _is_admin_request(event: dict[str, Any], method: str) -> bool:
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return False
    resource, path = _route_paths(event)
    return resource.startswith("/admin/") or path.startswith("/admin/")


def _is_portal_auth_request(event: dict[str, Any], method: str) -> bool:
    if method not in {"GET", "POST"}:
        return False
    resource, path = _route_paths(event)
    candidate = resource or path
    return candidate in {"/auth/register", "/auth/login", "/auth/me"}


def _is_portal_organization_request(event: dict[str, Any], method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    candidate = resource or path
    return candidate == "/organizations"


def _is_portal_membership_request(event: dict[str, Any], method: str) -> bool:
    if method not in {"GET", "POST", "PATCH", "DELETE"}:
        return False
    resource, path = _route_paths(event)
    candidate = resource or path
    return candidate in {
        "/organizations/current/members",
        "/organizations/current/invitations",
        "/organizations/current/members/{memberId}",
    }


def _is_portal_api_key_request(event: dict[str, Any], method: str) -> bool:
    if method not in {"GET", "POST", "DELETE"}:
        return False
    resource, path = _route_paths(event)
    candidate = resource or path
    return candidate in {
        "/organizations/current/api-keys",
        "/organizations/current/api-keys/{keyId}",
    }


def _is_invitation_accept_request(event: dict[str, Any], method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    candidate = resource or path
    return candidate == "/invitations/accept"


def _handle_portal_auth_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = _route_template(event)
    service = _get_portal_auth_service()

    if resource == "/auth/register" and method == "POST":
        payload = _parse_json_body(event)
        session = service.register_user(
            UserCreateRequest(
                email=str(payload.get("email") or ""),
                password=str(payload.get("password") or ""),
                full_name=(str(payload.get("full_name")) if payload.get("full_name") is not None else None),
            )
        )
        return json_response(201, session.to_dict(), response_context=response_context)

    if resource == "/auth/login" and method == "POST":
        payload = _parse_json_body(event)
        session = service.login_user(
            UserLoginRequest(
                email=str(payload.get("email") or ""),
                password=str(payload.get("password") or ""),
            )
        )
        return json_response(200, session.to_dict(), response_context=response_context)

    if resource == "/auth/me" and method == "GET":
        headers = event.get("headers") or {}
        authorization = str(_get_header(headers, "authorization") or "")
        user = service.get_current_user(authorization)
        return json_response(200, {"user": user.to_dict()}, response_context=response_context)

    return error_response(404, "Auth route not found", response_context=response_context, code="not_found")


def _handle_portal_organization_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    headers = event.get("headers") or {}
    authorization = str(_get_header(headers, "authorization") or "")
    current_user = _get_portal_auth_service().get_current_user(authorization)
    payload = _parse_json_body(event)
    organization = _get_portal_organization_service().create_organization(
        creator_user_id=current_user.user_id,
        request=OrganizationCreateRequest(
            name=str(payload.get("name") or ""),
            slug=(str(payload.get("slug")) if payload.get("slug") is not None else None),
        ),
    )
    return json_response(201, organization.to_dict(), response_context=response_context)


def _resolve_current_portal_context(event: dict[str, Any]) -> tuple[str, str]:
    headers = event.get("headers") or {}
    account_id = str(_get_header(headers, "x-portal-account-id") or "").strip()
    workspace_id = str(_get_header(headers, "x-portal-workspace-id") or "").strip()
    if not account_id or not workspace_id:
        raise MembershipManagementError("Current organization headers are required")
    if account_id != workspace_id:
        raise MembershipManagementError("Current organization headers must identify the same scope")
    return account_id, workspace_id


def _handle_portal_membership_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = _route_template(event)
    headers = event.get("headers") or {}
    authorization = str(_get_header(headers, "authorization") or "")
    current_user = _get_portal_auth_service().get_current_user(authorization)
    account_id, workspace_id = _resolve_current_portal_context(event)
    del workspace_id
    service = _get_portal_membership_service()

    if resource == "/organizations/current/members" and method == "GET":
        items = [item.to_dict() for item in service.list_members(organization_id=account_id)]
        return json_response(200, {"items": items}, response_context=response_context)

    if resource == "/organizations/current/invitations" and method == "POST":
        payload = _parse_json_body(event)
        invitation = service.invite_member(
            organization_id=account_id,
            actor_user_id=current_user.user_id,
            request=InvitationCreateRequest(
                email=str(payload.get("email") or ""),
                role=str(payload.get("role") or ""),
            ),
        )
        return json_response(201, invitation.to_dict(), response_context=response_context)

    if resource == "/organizations/current/members/{memberId}" and method == "PATCH":
        path_params = event.get("pathParameters") or {}
        member_id = str(path_params.get("memberId") or "")
        payload = _parse_json_body(event)
        member = service.update_member(
            organization_id=account_id,
            actor_user_id=current_user.user_id,
            member_user_id=member_id,
            request=MemberUpdateRequest(
                role=(str(payload.get("role")) if payload.get("role") is not None else None),
                status=(str(payload.get("status")) if payload.get("status") is not None else None),
            ),
        )
        return json_response(200, member.to_dict(), response_context=response_context)

    if resource == "/organizations/current/members/{memberId}" and method == "DELETE":
        path_params = event.get("pathParameters") or {}
        member_id = str(path_params.get("memberId") or "")
        payload = service.remove_member(
            organization_id=account_id,
            actor_user_id=current_user.user_id,
            member_user_id=member_id,
        )
        return json_response(200, payload, response_context=response_context)

    return error_response(404, "Membership route not found", response_context=response_context, code="not_found")


def _handle_invitation_accept_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    headers = event.get("headers") or {}
    authorization = str(_get_header(headers, "authorization") or "")
    current_user = _get_portal_auth_service().get_current_user(authorization)
    payload = _parse_json_body(event)
    accepted = _get_portal_membership_service().accept_invitation(
        user_id=current_user.user_id,
        request=InvitationAcceptRequest(token=str(payload.get("token") or "")),
    )
    return json_response(200, accepted, response_context=response_context)


def _handle_portal_api_key_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = _route_template(event)
    headers = event.get("headers") or {}
    authorization = str(_get_header(headers, "authorization") or "")
    current_user = _get_portal_auth_service().get_current_user(authorization)
    account_id, workspace_id = _resolve_current_portal_context(event)
    del workspace_id
    service = _get_portal_api_key_service()

    if resource == "/organizations/current/api-keys" and method == "GET":
        items = [item.to_dict() for item in service.list_keys(organization_id=account_id, actor_user_id=current_user.user_id)]
        return json_response(200, {"items": items}, response_context=response_context)

    if resource == "/organizations/current/api-keys" and method == "POST":
        payload = _parse_json_body(event)
        created = service.create_key(
            organization_id=account_id,
            actor_user_id=current_user.user_id,
            request=ApiKeyCreateRequest(display_name=str(payload.get("display_name") or "")),
        )
        return json_response(201, created.to_dict(), response_context=response_context)

    if resource == "/organizations/current/api-keys/{keyId}" and method == "DELETE":
        path_params = event.get("pathParameters") or {}
        key_id = str(path_params.get("keyId") or "")
        revoked = service.revoke_key(
            organization_id=account_id,
            actor_user_id=current_user.user_id,
            key_id=key_id,
        )
        return json_response(200, revoked.to_dict(), response_context=response_context)

    return error_response(404, "API key route not found", response_context=response_context, code="not_found")


def _handle_admin_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = _route_template(event)
    path_params = event.get("pathParameters") or {}
    account_id = str(path_params.get("accountId") or "")
    key_id = str(path_params.get("keyId") or "")
    client_id = str(path_params.get("clientId") or "")
    service = _get_control_plane_service()

    if resource == "/admin/accounts":
        if method == "POST":
            return json_response(201, service.create_account(_parse_json_body(event)), response_context=response_context)
        if method == "GET":
            return json_response(200, {"items": service.list_accounts()}, response_context=response_context)

    if resource == "/admin/accounts/{accountId}":
        if method == "GET":
            return json_response(200, service.get_account(account_id), response_context=response_context)
        if method == "PATCH":
            return json_response(200, service.update_account(account_id, _parse_json_body(event)), response_context=response_context)

    if resource == "/admin/accounts/{accountId}/subscription":
        if method == "GET":
            return json_response(200, service.get_subscription(account_id), response_context=response_context)
        if method == "PUT":
            return json_response(200, service.update_subscription(account_id, _parse_json_body(event)), response_context=response_context)

    if resource == "/admin/accounts/{accountId}/suspend" and method == "POST":
        return json_response(200, service.suspend_account(account_id), response_context=response_context)

    if resource == "/admin/accounts/{accountId}/activate" and method == "POST":
        return json_response(200, service.activate_account(account_id), response_context=response_context)

    if resource == "/admin/accounts/{accountId}/api-keys":
        if method == "POST":
            return json_response(201, service.create_api_key(account_id, _parse_json_body(event)), response_context=response_context)
        if method == "GET":
            return json_response(200, {"items": service.list_api_keys(account_id)}, response_context=response_context)

    if resource == "/admin/accounts/{accountId}/api-keys/{keyId}":
        if method == "DELETE":
            return json_response(200, service.delete_api_key(account_id, key_id), response_context=response_context)

    if resource == "/admin/accounts/{accountId}/api-keys/{keyId}/rotate" and method == "POST":
        return json_response(200, service.rotate_api_key(account_id, key_id), response_context=response_context)

    if resource == "/admin/accounts/{accountId}/oauth-clients":
        if method == "POST":
            return json_response(201, service.create_oauth_client(account_id, _parse_json_body(event)), response_context=response_context)
        if method == "GET":
            return json_response(200, {"items": service.list_oauth_clients(account_id)}, response_context=response_context)

    if resource == "/admin/accounts/{accountId}/oauth-clients/{clientId}" and method == "DELETE":
        return json_response(200, service.delete_oauth_client(account_id, client_id), response_context=response_context)

    return error_response(404, "Admin route not found", response_context=response_context, code="not_found")


def handler(event, context):
    api_context = build_response_context(event, context)
    route_key = _route_key(event or {})
    
    def respond(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
        return json_response(status_code, payload, response_context=api_context)

    def fail(status_code: int, message: str, code: str | None = None) -> dict[str, Any]:
        return error_response(status_code, message, response_context=api_context, code=code)

    method = (event.get("httpMethod") or "GET").upper()
    if _is_admin_request(event, method) or _is_ops_request(event, method):
        try:
            admin_id = authenticate_admin_key((event or {}).get("headers") or {}, _get_admin_key_store())
            event["_admin_id"] = admin_id
            admin_context = ResponseContext(
                request_id=api_context.request_id,
                plan="admin",
                deprecation=api_context.deprecation,
                cors_origin=api_context.cors_origin,
            )
            if _is_ops_request(event, method):
                status_code, payload = _handle_ops_request(event)
                return json_response(status_code, payload, response_context=admin_context)
            return _handle_admin_request(event, admin_context)
        except AuthenticationError as exc:
            return error_response(exc.status_code, str(exc), response_context=api_context)
        except ControlPlaneError as exc:
            return error_response(
                exc.status_code,
                str(exc),
                response_context=ResponseContext(
                    api_context.request_id,
                    "admin",
                    api_context.deprecation,
                    api_context.cors_origin,
                ),
            )
        except ValueError as exc:
            return error_response(
                400,
                str(exc),
                response_context=ResponseContext(
                    api_context.request_id,
                    "admin",
                    api_context.deprecation,
                    api_context.cors_origin,
                ),
            )

    if method == "OPTIONS":
        return json_response(200, {}, response_context=api_context)

    if _is_stripe_webhook_request(event, method):
        try:
            return _handle_stripe_webhook_request(event, api_context)
        except BillingWebhookError as exc:
            return error_response(exc.status_code, str(exc), response_context=api_context, code=getattr(exc, "code", None))

    if _is_oauth_token_request(event, method):
        return _handle_oauth_token_request(event, api_context)

    if _is_public_plan_catalog_request(event, method):
        return _handle_public_plan_catalog_request(response_context=api_context)

    if _is_portal_auth_request(event, method):
        portal_context = ResponseContext(
            request_id=api_context.request_id,
            plan="portal",
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
        try:
            return _handle_portal_auth_request(event, portal_context)
        except PortalAuthValidationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="bad_request")
        except AuthenticationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="unauthorized")
        except ValueError as exc:
            return error_response(400, str(exc), response_context=portal_context, code="bad_request")

    if _is_portal_organization_request(event, method):
        portal_context = ResponseContext(
            request_id=api_context.request_id,
            plan="portal",
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
        try:
            return _handle_portal_organization_request(event, portal_context)
        except OrganizationBootstrapValidationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="bad_request")
        except PortalAuthValidationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="bad_request")
        except AuthenticationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="unauthorized")
        except ValueError as exc:
            return error_response(400, str(exc), response_context=portal_context, code="bad_request")

    if _is_portal_membership_request(event, method):
        portal_context = ResponseContext(
            request_id=api_context.request_id,
            plan="portal",
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
        try:
            return _handle_portal_membership_request(event, portal_context)
        except MembershipManagementError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="bad_request")
        except AuthenticationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="unauthorized")
        except ValueError as exc:
            return error_response(400, str(exc), response_context=portal_context, code="bad_request")

    if _is_portal_api_key_request(event, method):
        portal_context = ResponseContext(
            request_id=api_context.request_id,
            plan="portal",
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
        try:
            return _handle_portal_api_key_request(event, portal_context)
        except ApiKeyManagementError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="bad_request")
        except AuthenticationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="unauthorized")
        except ValueError as exc:
            return error_response(400, str(exc), response_context=portal_context, code="bad_request")

    if _is_invitation_accept_request(event, method):
        portal_context = ResponseContext(
            request_id=api_context.request_id,
            plan="portal",
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
        try:
            return _handle_invitation_accept_request(event, portal_context)
        except MembershipManagementError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="bad_request")
        except AuthenticationError as exc:
            return error_response(exc.status_code, str(exc), response_context=portal_context, code="unauthorized")
        except ValueError as exc:
            return error_response(400, str(exc), response_context=portal_context, code="bad_request")

    tenant_nonprofit_request = _is_tenant_nonprofit_request(event or {}, method)
    try:
        if tenant_nonprofit_request:
            auth_context = _resolve_tenant_nonprofit_auth_context(event or {})
        else:
            auth_context = _get_auth_context_provider().extract_context(event or {})
        _prepare_quota_request_metadata(event or {}, auth_context)
        api_context = ResponseContext(
            request_id=api_context.request_id,
            plan=str(getattr(auth_context, "plan", None) or getattr(auth_context, "plan_id", None) or "public"),
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
        _get_quota_metering_hook().on_request(auth_context, route_key)
        api_context = ResponseContext(
            request_id=api_context.request_id,
            plan=str(getattr(auth_context, "plan", None) or getattr(auth_context, "plan_id", None) or "public"),
            deprecation=api_context.deprecation,
            cors_origin=api_context.cors_origin,
        )
    except AuthenticationError as exc:
        return fail(exc.status_code, str(exc))
    except FeatureUnavailableError as exc:
        return error_response(
            exc.status_code,
            str(exc),
            response_context=api_context,
            code="feature_unavailable",
            meta={
                "feature_flag": exc.feature_flag,
                "capability": exc.capability,
                "upgrade_plan": exc.upgrade_plan,
            },
        )
    except AuthorizationError as exc:
        return fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
    except QuotaExceededError as exc:
        return fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
    evaluation_context = _resolve_evaluation_context(auth_context)
    tenant_context = _build_tenant_nonprofit_context(auth_context) if tenant_nonprofit_request else None
    if method == "POST" and _is_batch_verify_request(event):
        response = _handle_batch_verify(
            event,
            auth_context=auth_context,
            evaluation_context=evaluation_context,
            response_context=api_context,
        )
        try:
            body = json.loads(response.get("body") or "{}")
            total = (((body.get("data") or {}).get("batch_summary") or {}).get("total"))
            if isinstance(total, int):
                auth_context.metadata["batch_items_count"] = str(total)
        except Exception:
            pass
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response
    if _is_organization_checkout_request(event, method):
        try:
            response = _handle_organization_checkout_request(event, auth_context, response_context=api_context)
        except BillingCheckoutError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        except AuthorizationError as exc:
            response = fail(exc.status_code, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response
    if _is_organization_plan_change_request(event, method):
        try:
            response = _handle_organization_plan_change_request(event, auth_context, response_context=api_context)
        except BillingPlanChangeError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        except AuthorizationError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response
    if _is_organization_portal_request(event, method):
        try:
            response = _handle_organization_portal_request(event, auth_context, response_context=api_context)
        except BillingPortalError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        except AuthorizationError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response
    if _is_organization_subscription_visibility_request(event, method):
        try:
            response = _handle_organization_subscription_visibility_request(auth_context, response_context=api_context)
        except BillingCheckoutError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        except AuthorizationError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response
    if _is_organization_settings_request(event, method):
        try:
            response = _handle_organization_settings_request(event, auth_context, response_context=api_context)
        except OrganizationIntegrationSettingsValidationError as exc:
            response = fail(400, str(exc))
        except AuthorizationError as exc:
            response = fail(exc.status_code, str(exc), code=getattr(exc, "code", None))
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response

    try:
        if method == "POST":
            verification_input = _parse_post_request(event)
        else:
            verification_input = _parse_get_request(event)
    except EINValidationError as exc:
        return fail(400, str(exc))
    except ValueError as exc:
        return fail(400, str(exc))

    try:
        if _is_search_request(event, method):
            status_code, payload = _handle_search_request(event, tenant_context=tenant_context)
            response = respond(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response

        normalized_ein = normalize_ein(verification_input.ein)
        if _is_sources_list_request(event, method):
            status_code, payload = _get_nonprofit_service().get_sources(
                tenant_context=tenant_context,
                ein=normalized_ein,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = respond(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response
        if _is_sources_detail_request(event, method):
            source_name = _extract_source_name(event)
            status_code, payload = _get_nonprofit_service().get_source_detail(
                tenant_context=tenant_context,
                ein=normalized_ein,
                source_name=source_name,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = respond(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response
        if _is_compliance_request(event, method):
            status_code, payload = _get_nonprofit_service().get_compliance(
                tenant_context=tenant_context,
                ein=normalized_ein,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = respond(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response
        if _is_federal_awards_request(event, method):
            status_code, payload = _get_nonprofit_service().get_federal_awards(
                tenant_context=tenant_context,
                ein=normalized_ein,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = respond(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response

        if _is_filings_request(event, method):
            status_code, payload = _get_nonprofit_service().get_filings(
                tenant_context=tenant_context,
                ein=normalized_ein,
            )
            response = respond(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response

        if method == "GET":
            cached = _load_cached_profile(normalized_ein)
            if cached is not None and _cached_profile_is_current(cached):
                if policy_id_required(verification_input) or evaluation_context.has_non_default_integrations() or not cached.get("integration_evaluation"):
                    cached = apply_evaluation_overlay(
                        payload=cached,
                        policy_id=verification_input.policy_id,
                        enrichment_service=_get_enrichment_service(),
                        evaluation_context=evaluation_context,
                        ein=normalized_ein,
                    )
                shaped = _shape_payload_for_response(cached, auth_context)
                response = respond(200, shaped)
                _get_quota_metering_hook().on_response(auth_context, route_key, 200)
                return response

        verification_input = VerificationInput(
            ein=normalized_ein,
            provided_name=verification_input.provided_name,
            subsection=verification_input.subsection,
            policy_id=verification_input.policy_id,
            weighting_profile=verification_input.weighting_profile,
        )
        if tenant_nonprofit_request:
            status_code, payload = _get_nonprofit_service().lookup_nonprofit(
                tenant_context=tenant_context,
                verification_input=verification_input,
                evaluation_context=evaluation_context,
            )
        else:
            status_code, payload = verify_nonprofit(
                _get_athena_client(),
                verification_input,
                enrichment_service=_get_enrichment_service(),
                evaluation_context=evaluation_context,
            )
        if status_code == 200 and method == "GET" and not evaluation_context.has_non_default_integrations():
            _materialize_profile(normalized_ein, payload)
        shaped_payload = _shape_payload_for_response(payload, auth_context) if status_code == 200 else payload
        response = respond(status_code, shaped_payload)
        _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
        return response
    except EINValidationError as exc:
        response = fail(400, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, 400)
        return response
    except ValueError as exc:
        response = fail(400, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, 400)
        return response
    except FeatureUnavailableError as exc:
        response = error_response(
            exc.status_code,
            str(exc),
            response_context=api_context,
            code="feature_unavailable",
            meta={
                "feature_flag": exc.feature_flag,
                "capability": exc.capability,
                "upgrade_plan": exc.upgrade_plan,
            },
        )
        _get_quota_metering_hook().on_response(auth_context, route_key, exc.status_code)
        return response
    except AuthorizationError as exc:
        response = fail(exc.status_code, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, exc.status_code)
        return response
    except OrganizationIntegrationSettingsValidationError as exc:
        response = fail(400, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, 400)
        return response
    except AthenaQueryTimeout as exc:
        response = fail(504, str(exc), code="timeout")
        _get_quota_metering_hook().on_response(auth_context, route_key, 504)
        return response
    except AthenaQueryError:
        logger.exception("Athena query error")
        response = fail(500, "Internal server error")
        _get_quota_metering_hook().on_response(auth_context, route_key, 500)
        return response
    except Exception:
        logger.exception("Unhandled exception in lambda_query handler")
        response = fail(500, "Internal server error")
        _get_quota_metering_hook().on_response(auth_context, route_key, 500)
        return response


def _parse_get_request(event: dict) -> VerificationInput:
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    return VerificationInput(
        ein=path_params.get("ein") or "",
        subsection=query_params.get("subsection"),
        policy_id=None,
        weighting_profile=(query_params.get("weighting_profile") if query_params else None),
    )


def _route_key(event: dict[str, Any]) -> str:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return normalize_route_key(f"{method} {resource or path or '/'}")


def _prepare_quota_request_metadata(event: dict[str, Any], auth_context: Any) -> None:
    metadata = getattr(auth_context, "metadata", None)
    if not isinstance(metadata, dict):
        return
    if not _is_batch_verify_request(event):
        metadata.pop("batch_items_count", None)
        return
    body = event.get("body")
    if not body:
        metadata.pop("batch_items_count", None)
        return
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        metadata.pop("batch_items_count", None)
        return
    if isinstance(payload, list):
        metadata["batch_items_count"] = str(len(payload))
        return
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        metadata["batch_items_count"] = str(len(payload["items"]))
        return
    metadata.pop("batch_items_count", None)


def _parse_post_request(event: dict) -> VerificationInput:
    body = event.get("body")
    if not body:
        raise ValueError("Request body is required")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON")

    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")

    ein = payload.get("ein")
    if not ein:
        raise ValueError("Request body must include ein")

    provided_name = payload.get("name")
    if provided_name is not None and not isinstance(provided_name, str):
        raise ValueError("name must be a string")
    policy_id = payload.get("policy_id")
    if policy_id is not None and not isinstance(policy_id, str):
        raise ValueError("policy_id must be a string")
    weighting_profile = payload.get("weighting_profile")
    if weighting_profile is not None and not isinstance(weighting_profile, str):
        raise ValueError("weighting_profile must be a string")

    return VerificationInput(
        ein=ein,
        provided_name=provided_name,
        policy_id=policy_id,
        weighting_profile=weighting_profile,
    )


def _is_filings_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/filings") or path.endswith("/filings")


def _is_search_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/nonprofits/search") or path.endswith("/nonprofits/search")


def _is_batch_verify_request(event: dict) -> bool:
    resource, path = _route_paths(event)
    return resource.endswith("/verify/batch") or path.endswith("/verify/batch")


def _is_oauth_token_request(event: dict, method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/oauth/token") or path.endswith("/oauth/token")


def _is_stripe_webhook_request(event: dict, method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/webhooks/stripe") or path.endswith("/webhooks/stripe")


def _is_public_plan_catalog_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/plans") or path.endswith("/plans")


def _is_ops_request(event: dict, method: str) -> bool:
    if method not in {"GET", "POST"}:
        return False
    resource, path = _route_paths(event)
    return resource.startswith("/ops/") or path.startswith("/ops/")


def _is_organization_settings_request(event: dict, method: str) -> bool:
    if method not in {"GET", "PUT"}:
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/organization/settings") or path.endswith("/organization/settings")


def _is_organization_checkout_request(event: dict, method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/organization/billing/checkout-session") or path.endswith("/organization/billing/checkout-session")


def _is_organization_plan_change_request(event: dict, method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/organization/billing/plan-change") or path.endswith("/organization/billing/plan-change")


def _is_organization_portal_request(event: dict, method: str) -> bool:
    if method != "POST":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/organization/billing/portal-session") or path.endswith("/organization/billing/portal-session")


def _is_organization_subscription_visibility_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/organization/billing/subscription") or path.endswith("/organization/billing/subscription")


def _handle_organization_settings_request(
    event: dict,
    auth_context: Any,
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    workspace_id, account_id = _require_organization_context(auth_context)
    service = _get_organization_integration_settings_service()
    method = str(event.get("httpMethod") or "GET").upper()
    if method == "GET":
        document = service.get_settings(workspace_id=workspace_id, account_id=account_id)
        return json_response(200, document.to_dict(), response_context=response_context)

    body = event.get("body")
    if not body:
        return error_response(400, "Request body is required", response_context=response_context)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return error_response(400, "Request body must be valid JSON", response_context=response_context)
    if not isinstance(payload, dict):
        return error_response(400, "Request body must be a JSON object", response_context=response_context)
    if "integrations" in payload and not _allows_organization_settings_management(auth_context):
        return error_response(
            403,
            "Plan entitlement does not allow integration settings changes",
            response_context=response_context,
            code="forbidden",
        )
    document = service.update_settings(
        workspace_id=workspace_id,
        account_id=account_id,
        payload=payload,
    )
    return json_response(200, document.to_dict(), response_context=response_context)


def _handle_stripe_webhook_request(event: dict[str, Any], response_context: ResponseContext) -> dict[str, Any]:
    headers = event.get("headers") or {}
    signature = _get_header(headers, "Stripe-Signature")
    result = _get_stripe_webhook_service().handle(
        raw_body=_raw_request_body(event),
        signature_header=signature,
    )
    return json_response(200, result, response_context=response_context)


def _handle_public_plan_catalog_request(
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    return json_response(200, build_plan_catalog_payload(), response_context=response_context)


def _handle_organization_checkout_request(
    event: dict,
    auth_context: Any,
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    _workspace_id, account_id = _require_organization_context(auth_context)
    if not account_id:
        raise AuthorizationError("Billing checkout requires authenticated account context")
    payload = _parse_json_body(event)
    checkout = _get_billing_checkout_service().create_checkout_session(
        account_id=account_id,
        payload=payload,
    )
    return json_response(200, checkout, response_context=response_context)


def _handle_organization_plan_change_request(
    event: dict,
    auth_context: Any,
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    _workspace_id, account_id = _require_organization_context(auth_context)
    if not account_id:
        raise AuthorizationError("Billing plan changes require authenticated account context")
    payload = _parse_json_body(event)
    plan_change = _get_billing_plan_change_service().change_plan(
        account_id=account_id,
        payload=payload,
    )
    return json_response(200, plan_change, response_context=response_context)


def _handle_organization_portal_request(
    event: dict,
    auth_context: Any,
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    _workspace_id, account_id = _require_organization_context(auth_context)
    if not account_id:
        raise AuthorizationError("Billing portal requires authenticated account context")
    payload = _parse_json_body(event)
    portal = _get_billing_portal_service().create_portal_session(
        account_id=account_id,
        payload=payload,
    )
    return json_response(200, portal, response_context=response_context)


def _handle_organization_subscription_visibility_request(
    auth_context: Any,
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    _workspace_id, account_id = _require_organization_context(auth_context)
    if not account_id:
        raise AuthorizationError("Billing visibility requires authenticated account context")
    summary = _get_billing_visibility_service().get_subscription_summary(account_id=account_id)
    return json_response(200, summary, response_context=response_context)


def _allows_organization_settings_management(auth_context: Any) -> bool:
    entitlements = getattr(auth_context, "entitlements", None)
    if entitlements is None:
        plan_code = str(getattr(auth_context, "plan", getattr(auth_context, "plan_id", "free")) or "free")
        entitlements = DEFAULT_PLANS.get(plan_code, DEFAULT_PLANS["free"]).entitlements
    return entitlements.allows_capability("organization_settings")


def _generate_manual_form990_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-manual-{secrets.token_hex(4)}"


def _parse_manual_form990_request(event: dict[str, Any]) -> tuple[dict[str, Any], list[str], bool]:
    payload = _parse_optional_json_body(event)
    allowed_fields = {"mode", "target_years"}
    unknown_fields = sorted(str(key) for key in payload.keys() if key not in allowed_fields)
    if unknown_fields:
        field_list = ", ".join(unknown_fields)
        raise ValueError(f"Unsupported request field(s): {field_list}")

    mode = str(payload.get("mode") or "incremental").strip().lower()
    if mode not in {"incremental", "bootstrap"}:
        raise ValueError("mode must be one of: incremental, bootstrap")

    target_years_present = "target_years" in payload
    target_years: list[str] = []
    if target_years_present:
        raw_target_years = payload.get("target_years")
        if not isinstance(raw_target_years, list):
            raise ValueError("target_years must be an array of year strings")
        for item in raw_target_years:
            if not isinstance(item, str):
                raise ValueError("target_years must be an array of year strings")
            year = item.strip()
            if not year:
                raise ValueError("target_years entries must be non-empty strings")
            target_years.append(year)

    return {"mode": mode}, target_years, target_years_present


def _handle_ops_form990_runs_request(event: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if not FORM990_ORCHESTRATOR_FUNCTION_NAME:
        return 503, {"message": "Form 990 orchestrator is not configured"}

    request_payload, target_years, target_years_present = _parse_manual_form990_request(event)
    run_id = _generate_manual_form990_run_id()
    triggered_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    invoke_payload: dict[str, Any] = {
        "run_id": run_id,
        "execution_mode": "orchestrated",
        "mode": request_payload["mode"],
    }
    if target_years_present:
        invoke_payload["target_years"] = target_years

    try:
        invoke_result = _get_lambda_invoke_client().invoke(
            FunctionName=FORM990_ORCHESTRATOR_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(invoke_payload).encode("utf-8"),
        )
    except Exception:
        logger.exception("form990.manual_trigger_invoke_failed", extra={"run_id": run_id})
        return 500, {"message": "Failed to queue Form 990 run"}

    status_code = int(invoke_result.get("StatusCode") or 0)
    if status_code != 202:
        logger.error(
            "form990.manual_trigger_unexpected_status",
            extra={"run_id": run_id, "status_code": status_code},
        )
        return 500, {"message": "Failed to queue Form 990 run"}

    logger.info(
        "form990.manual_trigger_queued run_id=%s mode=%s target_years=%s",
        run_id,
        request_payload["mode"],
        json.dumps(target_years),
    )

    return 202, {
        "status": "queued",
        "run_id": run_id,
        "execution_mode": "orchestrated",
        "mode": request_payload["mode"],
        "target_years": target_years,
        "triggered_at": triggered_at,
        "inspection_paths": {
            "ingest_runs": "/v1/ops/ingest/runs",
            "ingest_run": f"/v1/ops/ingest/runs/{run_id}",
            "ingest_run_filings": f"/v1/ops/ingest/runs/{run_id}/filings",
        },
    }


def _handle_ops_request(event: dict) -> tuple[int, dict[str, Any]]:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = _route_template(event)
    if resource.endswith("/ops/form990/runs"):
        if method != "POST":
            return 404, {"message": "Ops route not found"}
        return _handle_ops_form990_runs_request(event)

    run_store = _get_ops_run_store()
    if run_store is None:
        return 503, {"message": "Operational run store not configured"}
    path_params = event.get("pathParameters") or {}
    query = event.get("queryStringParameters") or {}
    try:
        limit = int(str(query.get("limit"))) if query.get("limit") else 50
    except ValueError:
        return 400, {"message": "limit must be an integer"}

    if resource.endswith("/ops/ingest/runs"):
        return list_ingest_runs(run_store, limit=limit)
    if resource.endswith("/ops/ingest/runs/{ingest_run_id}"):
        return get_ingest_run(run_store, str(path_params.get("ingest_run_id") or ""))
    if resource.endswith("/ops/ingest/runs/{ingest_run_id}/filings"):
        return get_ingest_run_filings(run_store, str(path_params.get("ingest_run_id") or ""))
    if resource.endswith("/ops/refresh/runs"):
        return list_refresh_runs(run_store, limit=limit)
    if resource.endswith("/ops/refresh/runs/{refresh_run_id}"):
        return get_refresh_run(run_store, str(path_params.get("refresh_run_id") or ""))
    if resource.endswith("/ops/refresh/runs/{refresh_run_id}/eins"):
        return get_refresh_run_eins(run_store, str(path_params.get("refresh_run_id") or ""))
    if resource.endswith("/ops/nonprofits/{ein}/pipeline-status"):
        ein = str(path_params.get("ein") or "")
        return get_nonprofit_pipeline_status(run_store, _get_profile_store(), ein)
    return 404, {"message": "Ops route not found"}


def _is_sources_list_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/nonprofits/{ein}/sources") or path.endswith("/sources")


def _is_sources_detail_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/nonprofits/{ein}/sources/{source_name}") or "/sources/" in path


def _is_compliance_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/nonprofits/{ein}/compliance") or path.endswith("/compliance")


def _is_federal_awards_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource, path = _route_paths(event)
    return resource.endswith("/nonprofits/{ein}/federal-awards") or path.endswith("/federal-awards")


def _extract_source_name(event: dict) -> str:
    path_params = event.get("pathParameters") or {}
    direct = path_params.get("source_name")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    path = strip_version_prefix(str(event.get("path") or ""))
    marker = "/sources/"
    if marker in path:
        return path.split(marker, 1)[1].strip("/")
    raise ValueError("source_name is required")


def _require_organization_context(auth_context: Any) -> tuple[str | None, str | None]:
    workspace_id = getattr(auth_context, "workspace_id", None)
    account_id = getattr(auth_context, "account_id", None)
    if not workspace_id and not account_id:
        raise AuthorizationError("Organization settings endpoints require authenticated workspace or account context")
    return workspace_id, account_id


def _handle_search_request(
    event: dict,
    *,
    tenant_context: TenantNonprofitContext | None,
) -> tuple[int, dict[str, Any]]:
    query = event.get("queryStringParameters") or {}
    name_query = str(query.get("q") or query.get("name") or "").strip()
    if not name_query:
        raise ValueError("Search query parameter q is required")
    if len(name_query) < 2:
        raise ValueError("Search query must be at least 2 characters")

    limit = SEARCH_DEFAULT_LIMIT
    if query.get("limit") is not None:
        try:
            limit = int(str(query.get("limit")))
        except ValueError as exc:
            raise ValueError("limit must be an integer") from exc
    if limit < 1 or limit > SEARCH_MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {SEARCH_MAX_LIMIT}")

    active_only = _parse_bool(query.get("active_only"), default=False)
    state = str(query.get("state")).strip().upper() if query.get("state") else None
    subsection = str(query.get("subsection")).strip() if query.get("subsection") else None
    cursor = str(query.get("cursor")).strip() if query.get("cursor") else None

    if tenant_context is None:
        raise AuthorizationError("Tenant nonprofit routes require organization-scoped authentication")

    return _get_nonprofit_service().search_nonprofits(
        tenant_context=tenant_context,
        name_query=name_query,
        limit=limit,
        state=state,
        subsection=subsection,
        active_only=active_only,
        cursor=cursor,
    )


def _handle_batch_verify(
    event: dict,
    auth_context: Any,
    evaluation_context: EvaluationContext,
    *,
    response_context: ResponseContext,
) -> dict[str, Any]:
    try:
        body = event.get("body")
        if not body:
            return error_response(400, "Request body is required", response_context=response_context)
        payload = json.loads(body)
    except json.JSONDecodeError:
        return error_response(400, "Request body must be valid JSON", response_context=response_context)

    items_input: list[Any]
    if isinstance(payload, list):
        items_input = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items_input = payload["items"]
    else:
        return error_response(400, "Request body must be an array or an object with items[]", response_context=response_context)

    plan_entitlements = getattr(auth_context, "entitlements", None)
    plan_batch_limit = getattr(plan_entitlements, "batch_request_limit", 0)
    if plan_entitlements is not None and plan_batch_limit <= 0:
        return error_response(403, "Plan entitlement does not allow this endpoint", response_context=response_context, code="forbidden")
    if plan_entitlements is not None and len(items_input) > plan_batch_limit:
        return error_response(403, f"Batch size exceeds plan limit of {plan_batch_limit}", response_context=response_context, code="forbidden")
    if len(items_input) > BATCH_VERIFY_MAX_SIZE:
        return error_response(400, f"Batch size exceeds maximum of {BATCH_VERIFY_MAX_SIZE}", response_context=response_context)

    results: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()

    for index, row in enumerate(items_input):
        item_result = _process_batch_item(index, row, evaluation_context=evaluation_context)
        results.append(item_result)
        status_counts[item_result["status"]] += 1
        if item_result["status"] == "ok":
            decision_counts[item_result.get("decision_status") or "unknown"] += 1
        else:
            error_counts[item_result.get("error_code") or "unknown_error"] += 1

    summary = {
        "total": len(items_input),
        "success": status_counts.get("ok", 0),
        "error": status_counts.get("error", 0),
        "counts_by_status": dict(status_counts),
        "counts_by_decision": dict(decision_counts),
        "counts_by_error": dict(error_counts),
        "max_batch_size": BATCH_VERIFY_MAX_SIZE,
    }
    return json_response(200, {"batch_summary": summary, "items": results}, response_context=response_context)


def _route_paths(event: dict[str, Any]) -> tuple[str, str]:
    return _route_template(event), strip_version_prefix(str(event.get("path") or ""))


def _route_template(event: dict[str, Any]) -> str:
    resource = str(event.get("resource") or "")
    if resource.strip():
        return strip_version_prefix(resource)
    return strip_version_prefix(str(event.get("path") or ""))


def _get_header(headers: dict[str, Any], name: str) -> str | None:
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None


def _raw_request_body(event: dict[str, Any]) -> str:
    if "rawBody" in event and isinstance(event.get("rawBody"), str):
        return str(event.get("rawBody") or "")
    body = event.get("body")
    if body is None:
        return ""
    if bool(event.get("isBase64Encoded")):
        import base64

        return base64.b64decode(str(body)).decode("utf-8")
    return str(body)


def _process_batch_item(index: int, row: Any, evaluation_context: EvaluationContext) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"index": index, "status": "error", "error_code": "invalid_item", "message": "Item must be an object"}

    ein = row.get("ein")
    if not ein:
        return {"index": index, "status": "error", "error_code": "missing_ein", "message": "Item must include ein"}

    provided_name = row.get("name")
    if provided_name is not None and not isinstance(provided_name, str):
        return {"index": index, "status": "error", "error_code": "invalid_name", "message": "name must be a string"}

    policy_id = row.get("policy_id")
    if policy_id is not None and not isinstance(policy_id, str):
        return {"index": index, "status": "error", "error_code": "invalid_policy_id", "message": "policy_id must be a string"}
    weighting_profile = row.get("weighting_profile")
    if weighting_profile is not None and not isinstance(weighting_profile, str):
        return {"index": index, "status": "error", "error_code": "invalid_weighting_profile", "message": "weighting_profile must be a string"}

    try:
        normalized_ein = normalize_ein(str(ein))
        payload = _verify_single_item(normalized_ein, provided_name, policy_id, weighting_profile, evaluation_context)
        return {
            "index": index,
            "ein": normalized_ein,
            "status": "ok",
            "decision_status": (payload.get("decision") or {}).get("status"),
            "final_recommendation": payload.get("final_recommendation"),
            "item": payload,
        }
    except EINValidationError as exc:
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "invalid_ein", "message": str(exc)}
    except ValueError as exc:
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "invalid_policy", "message": str(exc)}
    except AthenaQueryTimeout as exc:
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "athena_timeout", "message": str(exc)}
    except AthenaQueryError:
        logger.exception("Athena query error while processing batch item")
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "athena_error", "message": "Athena query failed"}
    except Exception:
        logger.exception("Unhandled exception while processing batch item")
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "internal_error", "message": "Internal server error"}


def _verify_single_item(
    normalized_ein: str,
    provided_name: str | None,
    policy_id: str | None,
    weighting_profile: str | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> dict[str, Any]:
    context = evaluation_context or EvaluationContext()
    if provided_name is None:
        cached = _load_cached_profile(normalized_ein)
        if cached is not None and _cached_profile_is_current(cached):
            if policy_id or context.has_non_default_integrations() or not cached.get("integration_evaluation"):
                cached = apply_evaluation_overlay(
                    payload=cached,
                    policy_id=policy_id,
                    enrichment_service=_get_enrichment_service(),
                    evaluation_context=context,
                    ein=normalized_ein,
                )
            return cached

    verification_input = VerificationInput(
        ein=normalized_ein,
        provided_name=provided_name,
        policy_id=policy_id,
        weighting_profile=weighting_profile,
    )
    status_code, payload = verify_nonprofit(
        _get_athena_client(),
        verification_input,
        enrichment_service=_get_enrichment_service(),
        evaluation_context=context,
    )
    if status_code != 200:
        raise ValueError(payload.get("message") or "Verification failed")
    payload["state_compliance"] = extract_state_compliance(payload.get("enrichment"))
    payload["external_signals"] = extract_external_signals(payload.get("enrichment"))
    return payload


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    candidate = str(value).strip().lower()
    if candidate in {"true", "1", "yes"}:
        return True
    if candidate in {"false", "0", "no"}:
        return False
    raise ValueError("active_only must be a boolean")


def _shape_payload_for_response(payload: dict[str, Any], auth_context: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    entitlements = getattr(auth_context, "entitlements", None)
    return _get_response_shaping_service().shape_verification_response(payload, entitlements)


def _cached_profile_is_current(payload: dict[str, Any]) -> bool:
    cached_version = str(((payload.get("score_explanation") or {}).get("model_version") or (payload.get("model") or {}).get("version") or "")).strip()
    return cached_version == SCORING_MODEL_VERSION


def _load_cached_profile(ein: str) -> dict | None:
    store = _get_profile_store()
    if store is None:
        return None
    item = store.get_profile(ein)
    if not item:
        return None
    return {
        "organization": item.get("organization"),
        "verification": item.get("verification"),
        "scores": item.get("scores"),
        "score_explanation": item.get("score_explanation"),
        "model": {"version": item.get("model_version"), "source": "materialized_dynamodb"},
        "filing_summary": item.get("latest_filing"),
        "enrichment": item.get("enrichment") or {"providers": [], "failures": []},
        "decision": item.get("decision"),
        "audit": item.get("audit"),
        "summary": item.get("summary"),
        "evidence": item.get("evidence"),
        "policy_evaluation": item.get("policy_evaluation"),
        "final_recommendation": item.get("final_recommendation") or item.get("decision", {}).get("status"),
        "state_compliance": item.get("state_compliance"),
        "external_signals": item.get("external_signals"),
        "integration_evaluation": item.get("integration_evaluation"),
    }


def _materialize_profile(ein: str, payload: dict) -> None:
    store = _get_profile_store()
    if store is None:
        return
    source_versions = {
        "model_version": payload.get("score_explanation", {}).get("model_version"),
        "score_data_sources": payload.get("score_explanation", {}).get("score_data_sources"),
    }
    item = materialize_profile_item(
        ein=ein,
        response_payload=payload,
        environment=APP_ENV,
        source_data_versions=source_versions,
    )
    MaterializedProfileWriter(store).write_if_needed(ein=ein, item=item)
from charity_status.ops import S3RunStore


def policy_id_required(verification_input: VerificationInput) -> bool:
    return bool(verification_input.policy_id)
