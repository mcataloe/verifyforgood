import importlib
import hashlib
import hmac
import json
import re
import sys
from decimal import Decimal
from time import time
from types import SimpleNamespace

from charity_status.auth import InMemoryUsageStore, build_admin_key_record, build_api_key_record
from charity_status.billing import DEFAULT_ENTITLEMENTS, monthly_period_for
from charity_status.billing.checkout import BillingCheckoutService, BillingProviderError, CheckoutSessionResult, StripeCheckoutConfig
from charity_status.billing.models import Subscription
from charity_status.billing.plan_changes import BillingPlanChangeService
from charity_status.billing.portal import BillingPortalService, PortalSessionResult
from charity_status.control_plane import ControlPlaneService, InMemoryControlPlaneStore
from charity_status.control_plane.models import ManagedSubscription
from charity_status.enrichments import InMemoryOrganizationIntegrationSettingsStore, OrganizationIntegrationSettingsService, load_organization_integration_settings
from charity_status.platform.auth import ApiKeyQuotaMeteringHook
from charity_status.scoring import SCORING_MODEL_VERSION
from charity_status.core.models import AuthContext
from charity_status_platform.customer_accounts import (
    AuditEventType,
    AuditLogService,
    DynamoAuditLogRepository,
    DynamoFeatureFlagRepository,
    DynamoOrganizationRepository,
    DynamoPlanRepository,
    DynamoSubscriptionRepository,
    FakeIdentityDynamoResource,
    FakeIdentityDynamoTable,
    FeatureFlagKey,
    FeatureFlagService,
    OrganizationRecord,
    SubscriptionService,
)


def _response_envelope(response):
    return json.loads(response["body"])


def _response_data(response):
    return _response_envelope(response)["data"]


def _response_error_message(response):
    return _response_envelope(response)["errors"][0]["message"]


def _stripe_signature(payload: str, *, secret: str, timestamp: int | None = None) -> str:
    timestamp = int(time()) if timestamp is None else timestamp
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def _load_module():
    sys.modules.pop("infrastructure.lambda_query", None)
    return importlib.import_module("infrastructure.lambda_query")


def _load_admin_module(monkeypatch):
    admin_key, admin_record = build_admin_key_record("root", secret="admin-secret")
    monkeypatch.setenv("ADMIN_KEY_RECORDS_JSON", json.dumps([admin_record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    return importlib.import_module("infrastructure.lambda_query"), admin_key


def _sample_record(name="Test Org", status="1"):
    return {
        "name": name,
        "state": "IL",
        "status": status,
        "deductibility": "1",
        "subsection": "03",
        "ntee_cd": "P20",
        "tax_period": "202501",
        "filing_req_cd": "1",
        "asset_amt": "",
        "income_amt": "",
        "revenue_amt": "",
    }


def _mock_client(
    record=None,
    filings=None,
    metrics=None,
    governance=None,
    quality=None,
    filing_rows=None,
    peer_stats=None,
    search_rows=None,
):
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", record),
        lookup_form990_enrichment=lambda ein: (filings, metrics, governance, quality),
        list_form990_filings=lambda ein, limit=10: ("qid-f", filing_rows or []),
        lookup_peer_benchmark=lambda group: peer_stats or {"count": 0, "metrics": {}},
        search_nonprofits=lambda **kwargs: ("qid-s", search_rows or []),
    )


def _mock_enrichment(providers=None, failures=None):
    return SimpleNamespace(to_dict=lambda: {"providers": providers or [], "failures": failures or []})


def _install_tenant_auth(
    module,
    *,
    organization_id: str = "org_1",
    credential_id: str = "key_1",
    auth_method: str = "api_key",
    plan: str = "pro",
    scopes: tuple[str, ...] = ("verify:read",),
):
    class _AuthProvider:
        def extract_context(self, event):
            return AuthContext(
                account_id=organization_id,
                credential_id=credential_id,
                auth_method=auth_method,
                plan=plan,
                scopes=scopes,
                rate_limit_profile=plan,
                workspace_id=organization_id,
                subject=f"{auth_method}:{credential_id}",
                entitlements=DEFAULT_ENTITLEMENTS.get(plan, DEFAULT_ENTITLEMENTS["free"]),
                metadata={
                    "organization_id": organization_id,
                    "tenant_scoped_request": "true",
                    "organization_api_key": "true" if auth_method == "api_key" else "false",
                },
            )

    module.auth_context_provider = _AuthProvider()


def _install_audit_store(module):
    identity_table = FakeIdentityDynamoTable()
    identity_resource = FakeIdentityDynamoResource(identity_table)
    module.portal_audit_log_service = AuditLogService(
        repository=DynamoAuditLogRepository(dynamodb_resource=identity_resource),
    )
    return identity_resource


def _audit_by_event_type(audits, event_type):
    return [item for item in audits if item.event_type is event_type]


class _BillingSettingsResolver:
    def __init__(self, allow_overage: bool) -> None:
        self._allow_overage = allow_overage

    def allow_overage(self, account_id: str) -> bool:
        return self._allow_overage


class _StripeCheckoutClient:
    def __init__(self) -> None:
        self.session_calls = 0

    def create_customer(self, *, account_id: str, account_name: str, ein: str | None) -> str:
        return "cus_test_123"

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        plan_code: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
    ) -> CheckoutSessionResult:
        self.session_calls += 1
        return CheckoutSessionResult(
            session_id="cs_test_123",
            url="https://checkout.stripe.com/c/pay/cs_test_123",
            expires_at="2099-03-20T00:00:00+00:00",
        )


class _FailingStripeCheckoutClient:
    def create_customer(self, *, account_id: str, account_name: str, ein: str | None) -> str:
        return "cus_test_123"

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        plan_code: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        idempotency_key: str,
    ) -> CheckoutSessionResult:
        raise BillingProviderError("Stripe rejected the request during checkout session creation")


class _StripePortalClient:
    def __init__(self) -> None:
        self.session_calls = 0

    def create_portal_session(
        self,
        *,
        customer_id: str,
        account_id: str,
        return_url: str,
        idempotency_key: str,
    ) -> PortalSessionResult:
        self.session_calls += 1
        return PortalSessionResult(
            session_id="bps_test_123",
            url="https://billing.stripe.com/p/session/test_123",
        )


def test_invalid_ein_still_returns_400():
    module = _load_module()
    _install_tenant_auth(module)

    event = {"httpMethod": "GET", "pathParameters": {"ein": "12-34A6789"}, "queryStringParameters": None}
    result = module.handler(event, None)

    assert result["statusCode"] == 400
    assert "invalid characters" in _response_error_message(result)


def test_options_preflight_returns_cors_headers_for_allowed_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    module = _load_module()

    result = module.handler(
        {
            "httpMethod": "OPTIONS",
            "resource": "/v1/auth/register",
            "path": "/v1/auth/register",
            "headers": {"Origin": "http://localhost:5173"},
        },
        None,
    )

    assert result["statusCode"] == 200
    assert result["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert result["headers"]["Access-Control-Allow-Headers"] == "Content-Type,Authorization,X-Portal-Account-Id,X-Portal-Workspace-Id"
    assert result["headers"]["Access-Control-Allow-Methods"] == "GET,POST,PUT,PATCH,DELETE,OPTIONS"


def test_lookup_hit_path_returns_materialized_profile():
    module = _load_module()
    _install_tenant_auth(module)
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active"},
            "scores": {"overall": 88},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION, "peer_benchmarking_used": False},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve"},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        }
    )

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    envelope = _response_envelope(result)
    body = envelope["data"]

    assert result["statusCode"] == 200
    assert envelope["api_version"] == "v1"
    assert envelope["api_release"] == "1.0.0"
    assert envelope["request_id"]
    assert envelope["plan"] == "pro"
    assert envelope["deprecation"]["status"] == "active"
    assert body["organization"]["name"] == "Cached Org"
    assert body["scores"]["overall"] == 88
    assert body["evidence"]["model_version"] == SCORING_MODEL_VERSION
    assert body["state_compliance"]["registration_status"] == "active"


def test_lookup_hit_path_refreshes_stale_materialized_profile():
    module = _load_module()
    _install_tenant_auth(module)
    put_calls = []
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "unknown"},
            "scores": {"overall": 45},
            "score_explanation": {"model_version": "2.0.0", "peer_benchmarking_used": False, "eligibility": "INELIGIBLE", "factors": {"active_status": False}},
            "model_version": "2.0.0",
            "decision": {"status": "deny"},
            "audit": {"model_version": "2.0.0"},
            "summary": {"decision_status": "deny"},
            "evidence": {"model_version": "2.0.0", "factors": []},
        },
        put_profile=lambda item: put_calls.append(item),
    )
    module.athena_client = _mock_client(record=_sample_record("Fresh Org", status="01"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Fresh Org"
    assert body["verification"]["irs_status"] == "active"
    assert len(put_calls) == 1
    assert put_calls[0]["model_version"] == SCORING_MODEL_VERSION


def test_lookup_miss_then_fallback_materialize_nonprod_lazy():
    module = _load_module()
    _install_tenant_auth(module)
    put_calls = []
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.APP_ENV = "dev"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: None,
        put_profile=lambda item: put_calls.append(item),
    )
    module.athena_client = _mock_client(record=_sample_record("Fresh Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Fresh Org"
    assert len(put_calls) == 1
    assert put_calls[0]["pk"] == "EIN#123456789"


def test_post_verify_bypasses_cache_readthrough():
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {"organization": {"name": "Cached Org"}},
        put_profile=lambda item: None,
    )
    module.athena_client = _mock_client(record=_sample_record("Post Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Post Org"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["organization"]["name"] == "Post Org"


def test_post_verify_accepts_policy_id_and_returns_policy_evaluation():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Policy Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Policy Org", "policy_id": "strict_deny"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["policy_evaluation"]["policy_id"] == "strict_deny"
    assert "final_recommendation" in body


def test_post_verify_accepts_weighting_profile():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Weighted Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "body": json.dumps({"ein": "123456789", "name": "Weighted Org", "weighting_profile": "compliance_heavy_v1"}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["score_explanation"]["weighting_profile"]["applied"] == "compliance_heavy_v1"
    assert body["audit"]["weighting_profile"]["applied"] == "compliance_heavy_v1"


def test_response_shape_still_contains_core_fields():
    module = _load_module()
    _install_tenant_auth(module)
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Test Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    body = _response_data(module.handler(event, None))

    for key in [
        "organization",
        "verification",
        "scores",
        "score_explanation",
        "decision",
        "audit",
        "summary",
        "evidence",
        "policy_evaluation",
        "final_recommendation",
        "state_compliance",
    ]:
        assert key in body


def test_lookup_hit_path_with_dynamodb_decimal_values_is_serializable():
    module = _load_module()
    _install_tenant_auth(module)
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active"},
            "scores": {"overall": Decimal("88.5")},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION, "peer_benchmarking_used": False},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve"},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        }
    )

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["scores"]["overall"] == 88.5


def test_lookup_hit_path_recomputes_tenant_required_integrations(monkeypatch):
    monkeypatch.setenv(
        "ORGANIZATION_INTEGRATION_SETTINGS_JSON",
        json.dumps(
            [
                {
                    "workspace_id": "ws_1",
                    "integrations": {
                        "candid": {"enabled": True, "requiredForEvaluation": True}
                    },
                }
            ]
        ),
    )
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active", "recent_990_on_file": True},
            "scores": {"overall": 88},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION, "peer_benchmarking_used": False, "eligibility": "ELIGIBLE", "factors": {}},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve", "risk_flags": [], "manual_review": {"reason_codes": []}},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        }
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=(),
                metadata={
                    "organization_id": "org_1",
                    "tenant_scoped_request": "true",
                },
                workspace_id="ws_1",
                account_id="acct_1",
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["integration_evaluation"]["required_unmet_integrations"] == ["candid"]
    assert body["decision"]["status"] == "manual_review"


def test_get_organization_integrations_returns_current_settings():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore(
        [
            {
                "workspace_id": "ws_1",
                "account_id": "acct_1",
                "integrations": {
                    "candid": {"enabled": True, "requiredForEvaluation": False},
                },
            }
        ]
    )
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:read",),
                metadata={},
                workspace_id="ws_1",
                account_id="acct_1",
                plan="growth",
                entitlements=DEFAULT_ENTITLEMENTS["growth"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {"httpMethod": "GET", "resource": "/v1/organization/settings", "path": "/v1/organization/settings", "headers": {}}
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["workspace_id"] == "ws_1"
    assert body["integrations"]["candid"]["enabled"] is True
    assert body["integrations"]["charityNavigator"]["enabled"] is False
    assert body["billing"]["allowOverage"] is True
    assert body["billing"]["monthlyRequestCap"] is None


def test_resolve_evaluation_context_applies_org_feature_flag_overrides():
    module = _load_module()
    identity_table = FakeIdentityDynamoTable()
    identity_resource = FakeIdentityDynamoResource(identity_table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=identity_resource)
    plans = DynamoPlanRepository(dynamodb_resource=identity_resource)
    subscriptions = DynamoSubscriptionRepository(dynamodb_resource=identity_resource)
    subscription_service = SubscriptionService(
        organizations=organizations,
        plans=plans,
        subscriptions=subscriptions,
    )
    feature_service = FeatureFlagService(
        organizations=organizations,
        subscriptions=subscriptions,
        flags=DynamoFeatureFlagRepository(dynamodb_resource=identity_resource),
        subscription_service=subscription_service,
    )
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Org One",
            slug="org-one",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    subscription_service.upsert_subscription(
        organization_id="org_1",
        plan_id="starter",
        billing_cycle_start="2026-03-28T00:00:00+00:00",
        billing_cycle_end="2026-04-27T00:00:00+00:00",
    )
    feature_service.set_override(
        organization_id="org_1",
        flag_key=FeatureFlagKey.ENABLE_CANDID.value,
        enabled=True,
    )
    module.portal_feature_flag_service = feature_service

    class _IntegrationService:
        def resolve_context(self, *, workspace_id, account_id):
            return load_organization_integration_settings("[]").resolve(workspace_id=workspace_id, account_id=account_id)

    module.organization_integration_settings_service = _IntegrationService()

    context = module._resolve_evaluation_context(
        SimpleNamespace(
            workspace_id="org_1",
            account_id="org_1",
            metadata={"organization_api_key": "true", "organization_id": "org_1", "tenant_scoped_request": "true"},
        )
    )

    assert context.setting_for("candid").enabled is True
    assert context.setting_for("charity_navigator").enabled is False


def test_put_organization_integrations_updates_settings():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore()
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id="ws_1",
                account_id="acct_1",
                plan="pro",
                entitlements=DEFAULT_ENTITLEMENTS["pro"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "PUT",
        "resource": "/v1/organization/settings",
        "path": "/v1/organization/settings",
        "headers": {},
        "body": json.dumps({"integrations": {"candid": {"enabled": True, "requiredForEvaluation": True}}}),
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["source"] == "stored"
    assert body["integrations"]["candid"]["requiredForEvaluation"] is True
    assert body["billing"]["allowOverage"] is True
    assert body["billing"]["monthlyRequestCap"] is None

    fetched = module.organization_integration_settings_store.get_settings(workspace_id="ws_1", account_id="acct_1")
    assert fetched["integrations"]["candid"]["enabled"] is True


def test_put_organization_integrations_allows_billing_update_for_growth_plan():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore()
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id="ws_1",
                account_id="acct_1",
                plan="growth",
                entitlements=DEFAULT_ENTITLEMENTS["growth"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "PUT",
        "resource": "/v1/organization/settings",
        "path": "/v1/organization/settings",
        "headers": {},
        "body": json.dumps(
            {"billing": {"allowOverage": False, "monthlyRequestCap": 750}}
        ),
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["billing"]["allowOverage"] is False
    assert body["billing"]["monthlyRequestCap"] == 750
    fetched = module.organization_integration_settings_store.get_billing_settings(account_id="acct_1")
    assert fetched["billing"]["allowOverage"] is False
    assert fetched["billing"]["monthlyRequestCap"] == 750


def test_put_organization_integrations_rejects_integration_update_for_growth_plan():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore()
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id="ws_1",
                account_id="acct_1",
                plan="growth",
                entitlements=DEFAULT_ENTITLEMENTS["growth"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "PUT",
        "resource": "/v1/organization/settings",
        "path": "/v1/organization/settings",
        "headers": {},
        "body": json.dumps({"integrations": {"candid": {"enabled": True, "requiredForEvaluation": False}}}),
    }
    result = module.handler(event, None)
    message = _response_error_message(result)

    assert result["statusCode"] == 403
    assert "integration settings changes" in message


def test_put_organization_integrations_rejects_required_disabled():
    module = _load_module()
    module.organization_integration_settings_store = InMemoryOrganizationIntegrationSettingsStore()
    module.organization_integration_settings_service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=module.organization_integration_settings_store,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id="ws_1",
                account_id="acct_1",
                plan="pro",
                entitlements=DEFAULT_ENTITLEMENTS["pro"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "PUT",
        "resource": "/v1/organization/settings",
        "path": "/v1/organization/settings",
        "headers": {},
        "body": json.dumps({"integrations": {"candid": {"enabled": False, "requiredForEvaluation": True}}}),
    }
    result = module.handler(event, None)
    message = _response_error_message(result)

    assert result["statusCode"] == 400
    assert "requiredForEvaluation" in message


def test_post_organization_billing_checkout_session_returns_checkout_url():
    module = _load_module()
    stripe_client = _StripeCheckoutClient()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Billing Account", "ein": "123456789"})
    module.billing_checkout_service = BillingCheckoutService(
        store=module.control_plane_service.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=stripe_client,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="free",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {
        "httpMethod": "POST",
        "resource": "/v1/organization/billing/checkout-session",
        "path": "/v1/organization/billing/checkout-session",
        "headers": {},
        "body": json.dumps(
            {
                "plan_code": "growth",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            }
        ),
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["plan_code"] == "growth"
    assert body["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_123"
    assert body["reused"] is False
    assert stripe_client.session_calls == 1


def test_post_stripe_webhook_route_processes_valid_signed_event(monkeypatch):
    monkeypatch.setenv("STRIPE_BILLING_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_PRICE_IDS", '{"growth":"price_growth"}')
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Webhook Account", "ein": "123456789"})
    payload = json.dumps(
        {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "created": 1770000000,
            "data": {
                "object": {
                    "object": "checkout.session",
                    "id": "cs_123",
                    "mode": "subscription",
                    "customer": "cus_123",
                    "subscription": "sub_123",
                    "client_reference_id": account["id"],
                    "metadata": {"account_id": account["id"], "requested_plan_code": "growth"},
                }
            },
        },
        separators=(",", ":"),
    )
    signature = _stripe_signature(payload, secret="whsec_test")

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/webhooks/stripe",
            "path": "/v1/webhooks/stripe",
            "headers": {"Stripe-Signature": signature},
            "body": payload,
        },
        None,
    )

    assert result["statusCode"] == 200
    body = _response_data(result)
    assert body["processed"] is True
    assert module.control_plane_service.store.get_subscription(account["id"]).stripe_customer_id == "cus_123"


def test_post_organization_billing_plan_change_returns_plan_payload():
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Plan Change Account", "ein": "123456789"})

    class _PlanChangeService:
        def change_plan(self, *, account_id: str, payload: dict[str, object]) -> dict[str, object]:
            assert account_id == account["id"]
            assert payload == {"plan_code": "growth"}
            return {
                "account_id": account_id,
                "current_plan_code": "pro",
                "pending_plan_code": "growth",
                "effective_from": "2026-03-01T00:00:00+00:00",
                "effective_to": None,
                "billing_period_start": "2026-03-01T00:00:00+00:00",
                "billing_period_end": "2026-04-01T00:00:00+00:00",
                "pending_plan_effective_at": "2026-04-01T00:00:00+00:00",
                "billing_status": "active",
                "change_type": "downgrade_scheduled",
                "reused": False,
            }

    module.billing_plan_change_service = _PlanChangeService()

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="pro",
                entitlements=DEFAULT_ENTITLEMENTS["pro"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organization/billing/plan-change",
            "path": "/v1/organization/billing/plan-change",
            "headers": {},
            "body": json.dumps({"plan_code": "growth"}),
        },
        None,
    )

    assert result["statusCode"] == 200
    body = _response_data(result)
    assert body["current_plan_code"] == "pro"
    assert body["pending_plan_code"] == "growth"
    assert body["change_type"] == "downgrade_scheduled"


def test_post_organization_billing_portal_session_returns_portal_url():
    module = _load_module()
    stripe_client = _StripePortalClient()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Portal Account", "ein": "123456789"})
    module.control_plane_service.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="growth",
            status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_end="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-01T00:00:00+00:00",
        )
    )
    module.billing_portal_service = BillingPortalService(
        store=module.control_plane_service.store,
        config=StripeCheckoutConfig(enabled=True, secret_key="sk_test_123", price_ids={"growth": "price_growth"}),
        stripe_client=stripe_client,
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="growth",
                entitlements=DEFAULT_ENTITLEMENTS["growth"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organization/billing/portal-session",
            "path": "/v1/organization/billing/portal-session",
            "headers": {},
            "body": json.dumps({"return_url": "https://example.com/billing"}),
        },
        None,
    )

    assert result["statusCode"] == 200
    body = _response_data(result)
    assert body["portal_url"] == "https://billing.stripe.com/p/session/test_123"
    assert stripe_client.session_calls == 1


def test_get_organization_billing_subscription_returns_product_focused_summary():
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Visibility Account", "ein": "123456789"})
    module.control_plane_service.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="pro",
            status="active",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            billing_status="active",
            billing_period_start="2026-03-01T00:00:00+00:00",
            billing_period_end="2026-04-01T00:00:00+00:00",
            pending_plan_code="growth",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-01T00:00:00+00:00",
        )
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:read",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="pro",
                entitlements=DEFAULT_ENTITLEMENTS["pro"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organization/billing/subscription",
            "path": "/v1/organization/billing/subscription",
            "headers": {},
        },
        None,
    )

    assert result["statusCode"] == 200
    body = _response_data(result)
    assert body == {
        "plan": "pro",
        "effective_access_plan": "pro",
        "billing_status": "active",
        "renewal_date": "2026-04-01T00:00:00+00:00",
        "pending_downgrade": {
            "plan": "growth",
            "effective_at": "2026-04-01T00:00:00+00:00",
        },
        "trial": None,
    }


def test_organization_billing_subscription_requires_account_context():
    module = _load_module()

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:read",),
                metadata={},
                workspace_id=None,
                account_id=None,
                plan="free",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organization/billing/subscription",
            "path": "/v1/organization/billing/subscription",
            "headers": {},
        },
        None,
    )

    assert result["statusCode"] == 403
    assert "authenticated workspace or account context" in _response_error_message(result)


def test_get_organization_billing_subscription_includes_trial_status_and_effective_access_plan():
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Trial Account", "ein": "123456789"})
    module.control_plane_service.store.put_subscription(
        ManagedSubscription(
            account_id=account["id"],
            plan_code="free",
            status="active",
            effective_from="2026-03-19T00:00:00+00:00",
            trial_status="active",
            trial_started_at="2026-03-19T00:00:00+00:00",
            trial_ends_at="2026-04-02T00:00:00+00:00",
            trial_trigger_event="POST /v1/verify",
            trial_consumed=True,
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    module.entitlement_service = None
    module.billing_visibility_service = None
    module.trial_lifecycle_service = None

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:read",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="free",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/organization/billing/subscription",
            "path": "/v1/organization/billing/subscription",
            "headers": {},
        },
        None,
    )

    assert result["statusCode"] == 200
    assert _response_data(result) == {
        "plan": "free",
        "effective_access_plan": "growth",
        "billing_status": "active",
        "renewal_date": None,
        "pending_downgrade": None,
        "trial": {
            "active": True,
            "status": "active",
            "ends_at": "2026-04-02T00:00:00+00:00",
        },
    }


def test_get_public_plan_catalog_returns_backend_driven_plan_metadata():
    module = _load_module()

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/plans",
            "path": "/v1/plans",
            "headers": {},
        },
        None,
    )

    assert result["statusCode"] == 200
    envelope = _response_envelope(result)
    plans = {plan["plan_code"]: plan for plan in envelope["data"]["plans"]}

    assert envelope["plan"] == "public"
    assert list(plans.keys()) == ["free", "starter", "growth", "pro", "enterprise"]

    assert plans["free"]["included_usage"]["monthly_requests"] == 250
    assert plans["free"]["feature_availability"]["verification"] is True
    assert plans["free"]["feature_availability"]["financial_trends"] is False

    assert plans["growth"]["included_usage"]["monthly_requests"] == 10000
    assert plans["growth"]["per_request_pricing"]["amount_usd_micros"] == 3000
    assert plans["growth"]["feature_availability"]["benchmarking"] is True

    assert plans["pro"]["included_usage"]["requests_per_minute"] == 600
    assert plans["pro"]["feature_availability"]["organization_settings"] is True

    assert plans["enterprise"]["included_usage"]["monthly_requests"] == 1000000
    assert plans["enterprise"]["feature_availability"]["monitoring"] is True


def test_first_authenticated_customer_request_starts_trial_before_feature_gating(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("FREE_TRIAL_ENABLED", "true")
    monkeypatch.setenv("FREE_TRIAL_DURATION_DAYS", "14")
    monkeypatch.setenv("FREE_TRIAL_PLAN_CODE", "growth")
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    module.auth_context_provider = None
    module.quota_metering_hook = None
    module.entitlement_service = None
    module.trial_lifecycle_service = None
    module.billing_visibility_service = None
    account = module.control_plane_service.create_account({"name": "Trial Account", "ein": "123456789"})
    api_key_payload = module.control_plane_service.create_api_key(
        account["id"],
        {"plan": "free", "scopes": ["verify:write"]},
    )
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Trial Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())
    module.usage_store = InMemoryUsageStore()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/verify/batch",
            "path": "/v1/verify/batch",
            "headers": {"x-api-key": api_key_payload["secret"]},
            "body": json.dumps({"items": [{"ein": "123456789"}]}),
        },
        None,
    )

    assert result["statusCode"] == 200
    envelope = _response_envelope(result)
    assert envelope["plan"] == "growth"
    updated = module.control_plane_service.store.get_subscription(account["id"])
    assert updated is not None
    assert updated.plan_code == "free"
    assert updated.trial_status == "active"
    assert updated.trial_trigger_event == "POST /v1/verify/batch"


def test_post_stripe_webhook_route_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("STRIPE_BILLING_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_PRICE_IDS", '{"growth":"price_growth"}')
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    module = _load_module()
    payload = json.dumps(
        {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "created": 1770000000,
            "data": {"object": {"object": "checkout.session"}},
        },
        separators=(",", ":"),
    )

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/webhooks/stripe",
            "path": "/v1/webhooks/stripe",
            "headers": {"Stripe-Signature": "t=1770000000,v1=bad"},
            "body": payload,
        },
        None,
    )

    assert result["statusCode"] == 400
    assert "signature" in _response_error_message(result).lower()


def test_post_organization_billing_checkout_session_rejects_invalid_plan():
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Billing Account", "ein": "123456789"})
    module.billing_checkout_service = BillingCheckoutService(
        store=module.control_plane_service.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=_StripeCheckoutClient(),
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="free",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organization/billing/checkout-session",
            "path": "/v1/organization/billing/checkout-session",
            "headers": {},
            "body": json.dumps(
                {
                    "plan_code": "unknown",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                }
            ),
        },
        None,
    )

    assert result["statusCode"] == 400
    assert "plan_code is invalid" in _response_error_message(result)


def test_post_organization_billing_checkout_session_returns_provider_error():
    module = _load_module()
    module.control_plane_service = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = module.control_plane_service.create_account({"name": "Billing Account", "ein": "123456789"})
    module.billing_checkout_service = BillingCheckoutService(
        store=module.control_plane_service.store,
        config=StripeCheckoutConfig(
            enabled=True,
            secret_key="sk_test_123",
            price_ids={"growth": "price_growth"},
        ),
        stripe_client=_FailingStripeCheckoutClient(),
    )

    class _AuthProvider:
        def extract_context(self, event):
            return SimpleNamespace(
                subject="tenant",
                scopes=("verify:write",),
                metadata={},
                workspace_id=account["id"],
                account_id=account["id"],
                plan="free",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            return None

        def on_response(self, auth_context, route_key, status_code):
            return None

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/organization/billing/checkout-session",
            "path": "/v1/organization/billing/checkout-session",
            "headers": {},
            "body": json.dumps(
                {
                    "plan_code": "growth",
                    "success_url": "https://example.com/success",
                    "cancel_url": "https://example.com/cancel",
                }
            ),
        },
        None,
    )

    assert result["statusCode"] == 502
    assert "Stripe rejected the request" in _response_error_message(result)
    assert _response_envelope(result)["meta"]["support"]["brand_name"] == "VerifyForGood"


def test_handler_returns_hard_stop_quota_response_when_overage_disabled():
    module = _load_module()
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store.increment_usage("org_1", month_key, 250)
    module.quota_metering_hook = ApiKeyQuotaMeteringHook(
        store,
        billing_settings_resolver=_BillingSettingsResolver(False),
    )

    class _AuthProvider:
        def extract_context(self, event):
            return AuthContext(
                account_id="org_1",
                credential_id="key_1",
                auth_method="api_key",
                plan="free",
                scopes=("verify:read",),
                rate_limit_profile="free",
                workspace_id="org_1",
                subject="api_key:key_1",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
                metadata={
                    "organization_id": "org_1",
                    "tenant_scoped_request": "true",
                    "organization_api_key": "true",
                },
            )

    module.auth_context_provider = _AuthProvider()

    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofit/{ein}",
        "path": "/v1/nonprofit/123456789",
        "pathParameters": {"ein": "123456789"},
        "headers": {},
    }
    result = module.handler(event, None)
    envelope = _response_envelope(result)

    assert result["statusCode"] == 429
    assert envelope["errors"][0]["code"] == "quota_exceeded_hard_stop"
    assert "enable pay per request" in envelope["errors"][0]["message"]


def test_handler_restricts_product_access_when_payment_failed():
    module = _load_module()
    module.quota_metering_hook = ApiKeyQuotaMeteringHook(InMemoryUsageStore(), billing_settings_resolver=_BillingSettingsResolver(True))

    class _AuthProvider:
        def extract_context(self, event):
            return AuthContext(
                account_id="org_1",
                credential_id="key_1",
                auth_method="api_key",
                plan="growth",
                scopes=("verify:read",),
                rate_limit_profile="growth",
                workspace_id="org_1",
                subject="api_key:key_1",
                subscription=Subscription(
                    account_id="org_1",
                    plan_code="growth",
                    status="active",
                    billing_status="payment_failed",
                ),
                entitlements=DEFAULT_ENTITLEMENTS["growth"],
                metadata={
                    "organization_id": "org_1",
                    "tenant_scoped_request": "true",
                    "organization_api_key": "true",
                },
            )

    module.auth_context_provider = _AuthProvider()

    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofit/{ein}",
        "path": "/v1/nonprofit/123456789",
        "pathParameters": {"ein": "123456789"},
        "headers": {},
    }
    result = module.handler(event, None)
    envelope = _response_envelope(result)

    assert result["statusCode"] == 402
    assert envelope["errors"][0]["code"] == "billing_past_due"
    assert "temporarily restricted" in envelope["errors"][0]["message"]


def test_batch_hard_stop_uses_batch_item_count():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store.increment_usage("acct_1", month_key, 9999)
    module.quota_metering_hook = ApiKeyQuotaMeteringHook(
        store,
        billing_settings_resolver=_BillingSettingsResolver(False),
    )

    class _AuthProvider:
        def extract_context(self, event):
            return AuthContext(
                account_id="acct_1",
                credential_id="key_1",
                auth_method="api_key",
                plan="growth",
                scopes=("verify:write",),
                rate_limit_profile="growth",
                workspace_id="ws_1",
                subject="api_key:key_1",
                entitlements=DEFAULT_ENTITLEMENTS["growth"],
                metadata={},
            )

    module.auth_context_provider = _AuthProvider()

    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "headers": {},
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321"}]}),
    }
    result = module.handler(event, None)

    assert result["statusCode"] == 429
    assert _response_envelope(result)["errors"][0]["code"] == "quota_exceeded_hard_stop"


def test_post_verify_batch_all_success():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321", "name": "Batch Org"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["batch_summary"]["total"] == 2
    assert body["batch_summary"]["success"] == 2
    assert body["batch_summary"]["error"] == 0


def test_post_verify_batch_partial_invalid_input():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "invalid"}, {"ein": "987654321"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    body = _response_data(module.handler(event, None))
    assert body["batch_summary"]["success"] == 2
    assert body["batch_summary"]["error"] == 1
    assert body["batch_summary"]["counts_by_error"]["invalid_ein"] == 1


def test_post_verify_batch_missing_ein_rows():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "body": json.dumps({"items": [{"name": "No EIN"}, {"ein": "123456789"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    body = _response_data(module.handler(event, None))
    assert body["batch_summary"]["error"] == 1
    assert body["batch_summary"]["counts_by_error"]["missing_ein"] == 1


def test_post_verify_batch_duplicate_eins_are_processed_independently():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.athena_client = _mock_client(record=_sample_record("Batch Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "123456789"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    body = _response_data(module.handler(event, None))
    assert body["batch_summary"]["total"] == 2
    assert body["batch_summary"]["success"] == 2
    assert len(body["items"]) == 2


def test_post_verify_batch_enforces_size_limit():
    module = _load_module()
    module.BATCH_VERIFY_MAX_SIZE = 1
    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    assert result["statusCode"] == 400
    assert "maximum of 1" in _response_error_message(result)


def test_post_verify_batch_reuses_cache_for_get_style_item():
    module = _load_module()
    module.SERVING_DDB_ENABLED = True
    module.PROFILE_TABLE_NAME = "profiles"
    module.BATCH_VERIFY_MAX_SIZE = 25
    module.profile_store = SimpleNamespace(
        get_profile=lambda ein: {
            "organization": {"ein": "12-3456789", "name": "Cached Org"},
            "verification": {"irs_status": "active"},
            "scores": {"overall": 88},
            "score_explanation": {"model_version": SCORING_MODEL_VERSION},
            "model_version": SCORING_MODEL_VERSION,
            "decision": {"status": "approve"},
            "audit": {"model_version": SCORING_MODEL_VERSION},
            "summary": {"decision_status": "approve"},
            "evidence": {"model_version": SCORING_MODEL_VERSION, "factors": []},
            "state_compliance": {"registration_status": "active", "compliance_flags": []},
        },
        put_profile=lambda item: None,
    )

    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "body": json.dumps({"items": [{"ein": "123456789"}]}),
        "pathParameters": None,
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["items"][0]["item"]["organization"]["name"] == "Cached Org"


def test_nonprofits_search_exactish_name():
    module = _load_module()
    _install_tenant_auth(module)
    module.SEARCH_DEFAULT_LIMIT = 20
    module.SEARCH_MAX_LIMIT = 50
    module.athena_client = _mock_client(
        search_rows=[
            {
                "ein": "123456789",
                "name": "Helping Hands Foundation",
                "state": "IL",
                "subsection": "03",
                "status": "1",
                "tax_period": "202501",
            }
        ]
    )
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/search",
        "path": "/v1/nonprofits/search",
        "queryStringParameters": {"q": "helping hands"},
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["items"][0]["name"] == "Helping Hands Foundation"
    assert body["items"][0]["ein"] == "12-3456789"


def test_nonprofits_search_filtered_search():
    module = _load_module()
    _install_tenant_auth(module)
    captured = {}

    def search_nonprofits(**kwargs):
        captured.update(kwargs)
        return "qid-s", []

    module.athena_client = SimpleNamespace(search_nonprofits=search_nonprofits)
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/search",
        "path": "/v1/nonprofits/search",
        "queryStringParameters": {"q": "org", "state": "il", "subsection": "03", "active_only": "true", "limit": "5"},
    }
    result = module.handler(event, None)
    assert result["statusCode"] == 200
    assert captured["state"] == "IL"
    assert captured["subsection"] == "03"
    assert captured["active_only"] is True
    assert captured["limit"] == 5


def test_nonprofits_search_pagination_cursor():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(
        search_rows=[
            {"ein": "123456789", "name": "A Org", "state": "IL", "subsection": "03", "status": "1", "tax_period": "202501"},
            {"ein": "223456789", "name": "B Org", "state": "IL", "subsection": "03", "status": "1", "tax_period": "202501"},
        ]
    )
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/search",
        "path": "/v1/nonprofits/search",
        "queryStringParameters": {"q": "org", "limit": "2"},
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["pagination"]["next_cursor"] is not None


def test_nonprofits_search_invalid_limit_handling():
    module = _load_module()
    _install_tenant_auth(module)
    module.SEARCH_MAX_LIMIT = 10
    module.athena_client = _mock_client(search_rows=[])
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/search",
        "path": "/v1/nonprofits/search",
        "queryStringParameters": {"q": "org", "limit": "100"},
    }
    result = module.handler(event, None)
    assert result["statusCode"] == 400
    assert "between 1 and 10" in _response_error_message(result)


def test_nonprofits_search_requires_tenant_context_before_client_access():
    module = _load_module()
    module.athena_client = SimpleNamespace(
        search_nonprofits=lambda **kwargs: (_ for _ in ()).throw(AssertionError("search client should not be called")),
    )
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/search",
        "path": "/v1/nonprofits/search",
        "queryStringParameters": {"q": "org"},
        "headers": {},
    }

    result = module.handler(event, None)

    assert result["statusCode"] == 401


def test_nonprofits_search_rejects_authenticated_non_tenant_context():
    module = _load_module()
    module.athena_client = SimpleNamespace(
        search_nonprofits=lambda **kwargs: (_ for _ in ()).throw(AssertionError("search client should not be called")),
    )

    class _AuthProvider:
        def extract_context(self, event):
            return AuthContext(
                account_id="acct_1",
                credential_id="key_1",
                auth_method="api_key",
                plan="free",
                scopes=("verify:read",),
                rate_limit_profile="free",
                workspace_id="ws_1",
                subject="api_key:key_1",
                entitlements=DEFAULT_ENTITLEMENTS["free"],
                metadata={},
            )

    module.auth_context_provider = _AuthProvider()
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/search",
        "path": "/v1/nonprofits/search",
        "queryStringParameters": {"q": "org"},
        "headers": {"x-api-key": "csk_dev_001.secret"},
    }

    result = module.handler(event, None)

    assert result["statusCode"] == 403


def test_tenant_lookup_tracks_org_usage_only_on_success():
    module = _load_module()
    _install_tenant_auth(module)
    identity_table = FakeIdentityDynamoTable()
    identity_resource = FakeIdentityDynamoResource(identity_table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=identity_resource)
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Org One",
            slug="org-one",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    usage_service = module.UsageService(
        organizations=organizations,
        usage=module.DynamoUsageRepository(dynamodb_resource=identity_resource),
    )
    module.quota_metering_hook = ApiKeyQuotaMeteringHook(
        InMemoryUsageStore(),
        billing_settings_resolver=_BillingSettingsResolver(True),
        organization_usage_tracker=module._PortalOrganizationUsageTracker(usage_service),
    )
    module.athena_client = _mock_client(record=_sample_record("Metered Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    ok_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )
    month_key = monthly_period_for()
    usage = module.DynamoUsageRepository(dynamodb_resource=identity_resource).list_for_period("org_1", month_key)

    assert ok_result["statusCode"] == 200
    assert {item.metric_type.value: item.request_count for item in usage} == {
        "api_requests": 1,
        "nonprofit_lookups": 1,
        "nonprofit_lookup_requests": 1,
    }

    bad_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/12-34A6789",
            "pathParameters": {"ein": "12-34A6789"},
            "queryStringParameters": None,
        },
        None,
    )
    usage_after_bad = module.DynamoUsageRepository(dynamodb_resource=identity_resource).list_for_period("org_1", month_key)

    assert bad_result["statusCode"] == 400
    assert {item.metric_type.value: item.request_count for item in usage_after_bad} == {
        "api_requests": 1,
        "nonprofit_lookups": 1,
        "nonprofit_lookup_requests": 1,
    }


def test_tenant_search_and_filings_track_route_specific_usage():
    module = _load_module()
    _install_tenant_auth(module, scopes=("verify:read", "nonprofits:read"))
    identity_table = FakeIdentityDynamoTable()
    identity_resource = FakeIdentityDynamoResource(identity_table)
    organizations = DynamoOrganizationRepository(dynamodb_resource=identity_resource)
    organizations.create(
        OrganizationRecord(
            organization_id="org_1",
            name="Org One",
            slug="org-one",
            created_at="2026-03-28T00:00:00+00:00",
            updated_at="2026-03-28T00:00:00+00:00",
        )
    )
    usage_service = module.UsageService(
        organizations=organizations,
        usage=module.DynamoUsageRepository(dynamodb_resource=identity_resource),
    )
    module.quota_metering_hook = ApiKeyQuotaMeteringHook(
        InMemoryUsageStore(),
        billing_settings_resolver=_BillingSettingsResolver(True),
        organization_usage_tracker=module._PortalOrganizationUsageTracker(usage_service),
    )
    module.athena_client = _mock_client(
        record=_sample_record("Metered Org"),
        search_rows=[{"ein": "123456789", "name": "Metered Org", "state": "IL", "subsection": "03", "status": "1", "tax_period": "202501"}],
        filing_rows=[],
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    search_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/search",
            "path": "/v1/nonprofits/search",
            "queryStringParameters": {"q": "metered"},
        },
        None,
    )
    filings_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}/filings",
            "path": "/v1/nonprofit/123456789/filings",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )
    month_key = monthly_period_for()
    usage = module.DynamoUsageRepository(dynamodb_resource=identity_resource).list_for_period("org_1", month_key)

    assert search_result["statusCode"] == 200
    assert filings_result["statusCode"] == 200
    assert {item.metric_type.value: item.request_count for item in usage} == {
        "api_requests": 2,
        "nonprofit_lookups": 2,
        "search_requests": 1,
        "filing_lookup_requests": 1,
    }


def test_nonprofits_sources_supported_source_lookup():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "state_registry_mock",
                        "status": "matched",
                        "fields": {
                            "registration_status": "active",
                            "registration_jurisdiction": "IL",
                            "registration_expiration_date": "2026-12-31",
                            "solicitation_permitted": True,
                            "compliance_flags": [],
                        },
                        "source": {"record_id": "sr-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    }
                ],
                "failures": [],
            }
        )
    )
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/{ein}/sources/{source_name}",
        "path": "/v1/nonprofits/123456789/sources/state_registry_mock",
        "pathParameters": {"ein": "123456789", "source_name": "state_registry_mock"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["source"]["source_name"] == "state_registry_mock"
    assert body["source"]["normalized_data"]["registration_status"] == "active"


def test_successful_nonprofit_routes_create_audit_events_with_sanitized_metadata():
    module = _load_module()
    _install_tenant_auth(module)
    identity_resource = _install_audit_store(module)
    module.athena_client = _mock_client(
        record=_sample_record("Audited Org"),
        search_rows=[
            {
                "ein": "123456789",
                "name": "Audited Org",
                "state": "IL",
                "subsection": "03",
                "status": "1",
                "tax_period": "202501",
            }
        ],
        filing_rows=[
            {
                "tax_year": "2024",
                "return_type": "990",
                "filing_date": "2025-01-01",
                "amended_return": "false",
                "parse_status": "parsed",
            }
        ],
    )
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None, evaluation_context=None, jurisdiction_state=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [],
                "failures": [],
                "integration_evaluation": {
                    "integrations": [
                        {
                            "integration_id": "candid",
                            "attempted": False,
                            "availability_status": "tenant_disabled",
                            "tenant_enabled": False,
                            "required_for_eligibility": False,
                        }
                    ],
                    "attempted_integrations": [],
                    "used_integrations": [],
                    "required_unmet_integrations": [],
                    "failure_integrations": [],
                },
            }
        )
    )

    lookup_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": {"subsection": "03", "weighting_profile": "compliance_heavy_v1"},
        },
        None,
    )
    search_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/search",
            "path": "/v1/nonprofits/search",
            "queryStringParameters": {"q": "audited org", "limit": "5", "state": "il", "active_only": "true"},
        },
        None,
    )
    filings_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}/filings",
            "path": "/v1/nonprofit/123456789/filings",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )
    sources_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/{ein}/sources",
            "path": "/v1/nonprofits/123456789/sources",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )
    audits = DynamoAuditLogRepository(dynamodb_resource=identity_resource).list_for_organization("org_1")
    lookup_audit = _audit_by_event_type(audits, AuditEventType.NONPROFIT_LOOKUP)[0]
    search_audit = _audit_by_event_type(audits, AuditEventType.NONPROFIT_SEARCH)[0]
    filings_audit = _audit_by_event_type(audits, AuditEventType.NONPROFIT_FILINGS_ACCESS)[0]
    sources_audit = _audit_by_event_type(audits, AuditEventType.NONPROFIT_SOURCE_ACCESS)[0]

    assert lookup_result["statusCode"] == 200
    assert search_result["statusCode"] == 200
    assert filings_result["statusCode"] == 200
    assert sources_result["statusCode"] == 200
    assert len(audits) == 4
    assert lookup_audit.actor_user_id is None
    assert lookup_audit.metadata["endpoint"] == "GET /v1/nonprofit/{ein}"
    assert lookup_audit.metadata["ein"] == "123456789"
    assert lookup_audit.metadata["query_subsection"] == "03"
    assert lookup_audit.metadata["response_sources"] == ["candid"]
    assert search_audit.metadata["query_text"] == "audited org"
    assert search_audit.metadata["query_state"] == "il"
    assert search_audit.metadata["query_active_only"] is True
    assert search_audit.metadata["result_count"] == 1
    assert filings_audit.metadata["filing_count"] == 1
    assert sources_audit.metadata["response_sources"] == []


def test_nonprofit_source_detail_audit_event_records_source_name_and_sources():
    module = _load_module()
    _install_tenant_auth(module)
    identity_resource = _install_audit_store(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "state_registry_mock",
                        "status": "matched",
                        "fields": {
                            "registration_status": "active",
                        },
                        "source": {"record_id": "sr-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    }
                ],
                "failures": [],
            }
        )
    )

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/{ein}/sources/{source_name}",
            "path": "/v1/nonprofits/123456789/sources/state_registry_mock",
            "pathParameters": {"ein": "123456789", "source_name": "state_registry_mock"},
            "queryStringParameters": None,
        },
        None,
    )

    audits = DynamoAuditLogRepository(dynamodb_resource=identity_resource).list_for_organization("org_1")
    audit = _audit_by_event_type(audits, AuditEventType.NONPROFIT_SOURCE_ACCESS)[0]

    assert result["statusCode"] == 200
    assert audit.metadata["source_name"] == "state_registry_mock"
    assert audit.metadata["response_sources"] == ["state_registry_mock"]


def test_portal_session_nonprofit_audit_event_records_actor_user_id():
    module = _load_module()
    _install_tenant_auth(
        module,
        auth_method="portal_session",
        credential_id="user_portal_1",
        scopes=("verify:read", "nonprofits:read"),
    )
    identity_resource = _install_audit_store(module)
    module.athena_client = _mock_client(record=_sample_record("Portal Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None, evaluation_context=None, jurisdiction_state=None: _mock_enrichment())

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )

    audits = DynamoAuditLogRepository(dynamodb_resource=identity_resource).list_for_organization("org_1")

    assert result["statusCode"] == 200
    assert audits[0].actor_user_id == "user_portal_1"
    assert audits[0].metadata["user_id"] == "user_portal_1"
    assert audits[0].metadata["auth_method"] == "portal_session"


def test_nonprofit_audit_logging_failures_are_non_blocking():
    module = _load_module()
    _install_tenant_auth(module)

    class _FailingAuditRepository:
        def create(self, record):
            raise RuntimeError("audit store unavailable")

        def list_for_organization(self, organization_id):
            return []

        def list_identity_events(self):
            return []

    module.portal_audit_log_service = AuditLogService(
        repository=_FailingAuditRepository(),
    )
    module.athena_client = _mock_client(record=_sample_record("Audit Failure Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None, evaluation_context=None, jurisdiction_state=None: _mock_enrichment())

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )

    assert result["statusCode"] == 200


def test_nonprofit_audit_logging_skips_non_successful_responses():
    module = _load_module()
    _install_tenant_auth(module)
    identity_resource = _install_audit_store(module)
    module.athena_client = _mock_client(record=_sample_record("Audit Skip Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None, evaluation_context=None, jurisdiction_state=None: _mock_enrichment())

    invalid_lookup_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/12-34A6789",
            "pathParameters": {"ein": "12-34A6789"},
            "queryStringParameters": None,
        },
        None,
    )
    unsupported_source_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/{ein}/sources/{source_name}",
            "path": "/v1/nonprofits/123456789/sources/unknown_source",
            "pathParameters": {"ein": "123456789", "source_name": "unknown_source"},
            "queryStringParameters": None,
        },
        None,
    )

    audits = DynamoAuditLogRepository(dynamodb_resource=identity_resource).list_for_organization("org_1")

    assert invalid_lookup_result["statusCode"] == 400
    assert unsupported_source_result["statusCode"] == 404
    assert audits == []


def test_lookup_nonprofit_surfaces_disabled_premium_integrations_in_existing_metadata():
    module = _load_module()
    _install_tenant_auth(module)

    class _FeatureFlagService:
        def apply_evaluation_context_overrides(self, *, organization_id, context):
            return EvaluationContext(
                organization_integration_settings={
                    "candid": OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False),
                    "charity_navigator": OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False),
                }
            )

    module.portal_feature_flag_service = _FeatureFlagService()
    module.nonprofit_service = None
    module.athena_client = _mock_client(record=_sample_record("Flagged Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None, evaluation_context=None, jurisdiction_state=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [],
                "failures": [],
                "integration_evaluation": {
                    "integrations": [
                        {
                            "integration_id": "candid",
                            "offered": True,
                            "credentials_present": True,
                            "tenant_enabled": evaluation_context.setting_for("candid").enabled,
                            "required_for_eligibility": False,
                            "attempted": False,
                            "availability_status": "tenant_disabled",
                            "requirement_status": "not_required",
                        },
                        {
                            "integration_id": "charity_navigator",
                            "offered": True,
                            "credentials_present": True,
                            "tenant_enabled": evaluation_context.setting_for("charity_navigator").enabled,
                            "required_for_eligibility": False,
                            "attempted": False,
                            "availability_status": "tenant_disabled",
                            "requirement_status": "not_required",
                        },
                    ],
                    "attempted_integrations": [],
                    "used_integrations": [],
                    "required_unmet_integrations": [],
                    "failure_integrations": [],
                },
            }
        )
    )

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )
    body = _response_data(result)

    assert result["statusCode"] == 200
    states = {item["integration_id"]: item for item in body["integration_evaluation"]["integrations"]}
    assert states["candid"]["availability_status"] == "tenant_disabled"
    assert states["candid"]["tenant_enabled"] is False
    assert states["charity_navigator"]["availability_status"] == "tenant_disabled"
    assert body["enrichment"]["providers"] == []


def test_nonprofits_sources_omit_disabled_premium_integrations_cleanly():
    module = _load_module()
    _install_tenant_auth(module)

    class _FeatureFlagService:
        def apply_evaluation_context_overrides(self, *, organization_id, context):
            return EvaluationContext(
                organization_integration_settings={
                    "candid": OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False),
                    "charity_navigator": OrganizationIntegrationSetting(enabled=False, required_for_eligibility=False),
                }
            )

    module.portal_feature_flag_service = _FeatureFlagService()
    module.nonprofit_service = None
    module.athena_client = _mock_client(record=_sample_record("Flagged Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None, evaluation_context=None, jurisdiction_state=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [],
                "failures": [],
                "integration_evaluation": {
                    "integrations": [
                        {
                            "integration_id": "candid",
                            "offered": True,
                            "credentials_present": True,
                            "tenant_enabled": evaluation_context.setting_for("candid").enabled,
                            "required_for_eligibility": False,
                            "attempted": False,
                            "availability_status": "tenant_disabled",
                            "requirement_status": "not_required",
                        },
                        {
                            "integration_id": "charity_navigator",
                            "offered": True,
                            "credentials_present": True,
                            "tenant_enabled": evaluation_context.setting_for("charity_navigator").enabled,
                            "required_for_eligibility": False,
                            "attempted": False,
                            "availability_status": "tenant_disabled",
                            "requirement_status": "not_required",
                        },
                    ],
                    "attempted_integrations": [],
                    "used_integrations": [],
                    "required_unmet_integrations": [],
                    "failure_integrations": [],
                },
            }
        )
    )

    result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofits/{ein}/sources",
            "path": "/v1/nonprofits/123456789/sources",
            "pathParameters": {"ein": "123456789"},
            "queryStringParameters": None,
        },
        None,
    )
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["sources"] == []
    assert body["failures"] == []


def test_nonprofits_sources_unsupported_source_name():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/{ein}/sources/{source_name}",
        "path": "/v1/nonprofits/123456789/sources/unknown_source",
        "pathParameters": {"ein": "123456789", "source_name": "unknown_source"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    assert result["statusCode"] == 404
    assert "Unsupported source name" in _response_error_message(result)


def test_nonprofits_compliance_no_source_data_case():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/{ein}/compliance",
        "path": "/v1/nonprofits/123456789/compliance",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["compliance"]["status"] == "unavailable"


def test_nonprofits_sources_no_source_data_case():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/{ein}/sources",
        "path": "/v1/nonprofits/123456789/sources",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["sources"] == []
    assert body["failures"] == []


def test_nonprofits_compliance_summary_aggregation():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "state_registry_mock",
                        "status": "matched",
                        "fields": {
                            "registration_status": "active",
                            "registration_jurisdiction": "IL",
                            "registration_expiration_date": "2026-12-31",
                            "solicitation_permitted": True,
                            "compliance_flags": ["late_filing_notice"],
                        },
                        "source": {"record_id": "sr-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    },
                    {
                        "name": "state_business_mock",
                        "status": "matched",
                        "fields": {
                            "entity_status": "good_standing",
                            "good_standing": True,
                            "compliance_flags": ["registered_agent_issue"],
                        },
                        "source": {"record_id": "sb-1", "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    },
                ],
                "failures": [],
            }
        )
    )
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/{ein}/compliance",
        "path": "/v1/nonprofits/123456789/compliance",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["compliance"]["status"] == "available"
    assert body["compliance"]["registration_status"] == "active"
    assert body["compliance"]["state_business_status"] == "good_standing"
    assert body["compliance"]["compliance_flags"] == ["late_filing_notice", "registered_agent_issue"]


def test_nonprofits_federal_awards_summary_response():
    module = _load_module()
    _install_tenant_auth(module)
    module.athena_client = _mock_client(record=_sample_record("Source Org"))
    module.enrichment_service = SimpleNamespace(
        enrich=lambda ein, organization_name=None: SimpleNamespace(
            to_dict=lambda: {
                "providers": [
                    {
                        "name": "usaspending_mock",
                        "status": "matched",
                        "fields": {
                            "award_count": 5,
                            "total_obligations_usd": 320000.0,
                            "latest_award_date": "2025-11-01",
                        },
                        "source": {"record_id": None, "fetched_at": "2026-03-12T00:00:00+00:00", "licensed": False},
                    }
                ],
                "failures": [],
            }
        )
    )
    event = {
        "httpMethod": "GET",
        "resource": "/v1/nonprofits/{ein}/federal-awards",
        "path": "/v1/nonprofits/123456789/federal-awards",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": None,
    }
    result = module.handler(event, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["federal_awards"]["status"] == "available"
    assert body["federal_awards"]["award_count"] == 5


def test_handler_invokes_auth_and_quota_hooks():
    module = _load_module()
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _mock_client(record=_sample_record("Hook Org"))
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: _mock_enrichment())

    calls = []

    class _AuthProvider:
        def extract_context(self, event):
            calls.append(("auth", event.get("httpMethod")))
            return SimpleNamespace(
                subject="api_key:key_1",
                scopes=(),
                metadata={"organization_id": "org_1", "tenant_scoped_request": "true", "organization_api_key": "true"},
                auth_method="api_key",
                credential_id="key_1",
                account_id="org_1",
                workspace_id="org_1",
                plan="pro",
                entitlements=DEFAULT_ENTITLEMENTS["pro"],
            )

    class _QuotaHook:
        def on_request(self, auth_context, route_key):
            calls.append(("request", route_key, auth_context.subject))

        def on_response(self, auth_context, route_key, status_code):
            calls.append(("response", route_key, status_code))

    module.auth_context_provider = _AuthProvider()
    module.quota_metering_hook = _QuotaHook()

    event = {"httpMethod": "GET", "pathParameters": {"ein": "123456789"}, "queryStringParameters": None}
    result = module.handler(event, None)

    assert result["statusCode"] == 200
    assert calls[0] == ("auth", "GET")
    assert calls[1][0] == "request"
    assert calls[-1][0] == "response"
    assert calls[-1][2] == 200


def test_ops_ingest_runs_listing_and_detail(monkeypatch):
    module, admin_key = _load_admin_module(monkeypatch)
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=50: [{"ingest_run_id": "ing-1", "status": "success"}] if run_type == "ingest" else [],
        get_run=lambda run_type, run_id: {"ingest_run_id": run_id, "status": "partial_success"} if run_type == "ingest" else None,
        get_run_items=lambda run_type, run_id, item_name: [{"ein": "123456789"}] if (run_type, item_name) == ("ingest", "filings") else None,
    )
    module.OPS_METADATA_BUCKET = "test-bucket"

    headers = {"x-admin-key": admin_key}
    list_result = module.handler({"httpMethod": "GET", "resource": "/v1/ops/ingest/runs", "headers": headers}, None)
    detail_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/ops/ingest/runs/{ingest_run_id}",
            "pathParameters": {"ingest_run_id": "ing-1"},
            "headers": headers,
        },
        None,
    )
    filings_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/ops/ingest/runs/{ingest_run_id}/filings",
            "pathParameters": {"ingest_run_id": "ing-1"},
            "headers": headers,
        },
        None,
    )
    assert list_result["statusCode"] == 200
    assert detail_result["statusCode"] == 200
    assert filings_result["statusCode"] == 200
    assert _response_envelope(list_result)["plan"] == "admin"


def test_ops_refresh_runs_listing_and_not_found(monkeypatch):
    module, admin_key = _load_admin_module(monkeypatch)
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=50: [{"refresh_run_id": "ref-1", "status": "completed"}] if run_type == "refresh" else [],
        get_run=lambda run_type, run_id: None,
        get_run_items=lambda run_type, run_id, item_name: None,
    )
    module.OPS_METADATA_BUCKET = "test-bucket"
    headers = {"x-admin-key": admin_key}
    list_result = module.handler({"httpMethod": "GET", "resource": "/v1/ops/refresh/runs", "headers": headers}, None)
    detail_result = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/ops/refresh/runs/{refresh_run_id}",
            "pathParameters": {"refresh_run_id": "ref-missing"},
            "headers": headers,
        },
        None,
    )
    assert list_result["statusCode"] == 200
    assert detail_result["statusCode"] == 404


def test_ops_pipeline_status_lookup_and_not_found(monkeypatch):
    module, admin_key = _load_admin_module(monkeypatch)
    module.OPS_METADATA_BUCKET = "test-bucket"
    module.profile_store = SimpleNamespace(get_profile=lambda ein: {"materialized_at": "2026-03-12T00:00:00Z", "source_hash": "abc", "model_version": SCORING_MODEL_VERSION, "environment": "dev"})
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=100: [{"ingest_run_id": "ing-1", "status": "success"}] if run_type == "ingest" else [{"refresh_run_id": "ref-1", "status": "completed"}],
        get_run_items=lambda run_type, run_id, item_name: [{"ein": "123456789"}],
        get_run=lambda run_type, run_id: None,
    )
    headers = {"x-admin-key": admin_key}
    ok = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/ops/nonprofits/{ein}/pipeline-status",
            "pathParameters": {"ein": "123456789"},
            "headers": headers,
        },
        None,
    )
    assert ok["statusCode"] == 200

    module.profile_store = SimpleNamespace(get_profile=lambda ein: None)
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=100: [],
        get_run_items=lambda run_type, run_id, item_name: [],
        get_run=lambda run_type, run_id: None,
    )
    missing = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/ops/nonprofits/{ein}/pipeline-status",
            "pathParameters": {"ein": "123456789"},
            "headers": headers,
        },
        None,
    )
    assert missing["statusCode"] == 404


def test_ops_form990_runs_post_queues_orchestrator(monkeypatch):
    monkeypatch.setenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", "form990-orchestrator")
    module, admin_key = _load_admin_module(monkeypatch)
    captured = {}

    class _LambdaClient:
        def invoke(self, **kwargs):
            captured.update(kwargs)
            return {"StatusCode": 202}

    module.lambda_invoke_client = _LambdaClient()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": json.dumps({"mode": "incremental", "target_years": ["2026"]}),
        },
        None,
    )

    body = _response_data(result)
    invoke_payload = json.loads(captured["Payload"].decode("utf-8"))

    assert result["statusCode"] == 202
    assert _response_envelope(result)["plan"] == "admin"
    assert captured["FunctionName"] == "form990-orchestrator"
    assert captured["InvocationType"] == "Event"
    assert body["status"] == "queued"
    assert body["execution_mode"] == "orchestrated"
    assert body["mode"] == "incremental"
    assert body["target_years"] == ["2026"]
    assert re.fullmatch(r"\d{8}T\d{6}Z-manual-[0-9a-f]{8}", body["run_id"])
    assert body["inspection_paths"]["ingest_run"] == f"/v1/ops/ingest/runs/{body['run_id']}"
    assert invoke_payload == {
        "run_id": body["run_id"],
        "execution_mode": "orchestrated",
        "mode": "incremental",
        "target_years": ["2026"],
    }


def test_ops_form990_runs_post_rejects_invalid_json(monkeypatch):
    monkeypatch.setenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", "form990-orchestrator")
    module, admin_key = _load_admin_module(monkeypatch)

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": "{bad json",
        },
        None,
    )

    assert result["statusCode"] == 400
    assert _response_error_message(result) == "Request body must be valid JSON"


def test_ops_form990_runs_post_rejects_invalid_mode(monkeypatch):
    monkeypatch.setenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", "form990-orchestrator")
    module, admin_key = _load_admin_module(monkeypatch)

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": json.dumps({"mode": "full"}),
        },
        None,
    )

    assert result["statusCode"] == 400
    assert _response_error_message(result) == "mode must be one of: incremental, bootstrap"


def test_ops_form990_runs_post_rejects_invalid_target_years(monkeypatch):
    monkeypatch.setenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", "form990-orchestrator")
    module, admin_key = _load_admin_module(monkeypatch)

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": json.dumps({"target_years": "2026"}),
        },
        None,
    )

    assert result["statusCode"] == 400
    assert _response_error_message(result) == "target_years must be an array of year strings"


def test_ops_form990_runs_post_rejects_unknown_fields(monkeypatch):
    monkeypatch.setenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", "form990-orchestrator")
    module, admin_key = _load_admin_module(monkeypatch)

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": json.dumps({"mode": "incremental", "unexpected": True}),
        },
        None,
    )

    assert result["statusCode"] == 400
    assert _response_error_message(result) == "Unsupported request field(s): unexpected"


def test_ops_form990_runs_post_requires_orchestrator_configuration(monkeypatch):
    monkeypatch.delenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", raising=False)
    module, admin_key = _load_admin_module(monkeypatch)

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": json.dumps({}),
        },
        None,
    )

    assert result["statusCode"] == 503
    assert _response_error_message(result) == "Form 990 orchestrator is not configured"


def test_ops_form990_runs_post_returns_500_when_invoke_fails(monkeypatch):
    monkeypatch.setenv("FORM990_ORCHESTRATOR_FUNCTION_NAME", "form990-orchestrator")
    module, admin_key = _load_admin_module(monkeypatch)

    class _LambdaClient:
        def invoke(self, **kwargs):
            raise RuntimeError("boom")

    module.lambda_invoke_client = _LambdaClient()

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-admin-key": admin_key},
            "body": json.dumps({}),
        },
        None,
    )

    assert result["statusCode"] == 500
    assert _response_error_message(result) == "Failed to queue Form 990 run"


def test_ops_routes_require_admin_key(monkeypatch):
    module, _admin_key = _load_admin_module(monkeypatch)
    module.OPS_METADATA_BUCKET = "test-bucket"
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=50: [],
        get_run=lambda run_type, run_id: None,
        get_run_items=lambda run_type, run_id, item_name: None,
    )

    result = module.handler({"httpMethod": "POST", "resource": "/v1/ops/form990/runs", "headers": {}, "body": json.dumps({})}, None)

    assert result["statusCode"] == 401
    assert _response_envelope(result)["plan"] == "public"


def test_ops_routes_reject_customer_api_key(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="ops_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="pro",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    module, _admin_key = _load_admin_module(monkeypatch)
    module.OPS_METADATA_BUCKET = "test-bucket"
    module.ops_run_store = SimpleNamespace(
        list_run_summaries=lambda run_type, limit=50: [],
        get_run=lambda run_type, run_id: None,
        get_run_items=lambda run_type, run_id, item_name: None,
    )

    result = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/ops/form990/runs",
            "headers": {"x-api-key": display_key},
            "body": json.dumps({}),
        },
        None,
    )

    assert result["statusCode"] == 401
