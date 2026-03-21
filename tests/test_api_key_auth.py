from __future__ import annotations

import importlib
import json
import sys
from types import SimpleNamespace

from charity_status.auth import InMemoryUsageStore, StaticApiKeyStore, build_api_key_record
from charity_status.auth.errors import AuthenticationError, AuthorizationError, BillingAccessError, QuotaExceededError
from charity_status.auth.service import authenticate_api_key, enforce_quota_and_scope
from charity_status.auth.models import ApiPlan, AuthenticatedPrincipal
from charity_status.billing import DEFAULT_ENTITLEMENTS, EntitlementService, Subscription
from charity_status.billing.trials import TrialConfig, TrialLifecycleService
from charity_status.billing.service import monthly_period_for
from charity_status.control_plane import ControlPlaneService, InMemoryControlPlaneStore
from charity_status.platform.auth import ApiKeyAuthContextProvider
from charity_status.platform.auth import ApiKeyQuotaMeteringHook


class _BillingSettingsResolver:
    def __init__(
        self,
        allow_overage: bool,
        monthly_request_limit: int | None = None,
    ) -> None:
        self._allow_overage = allow_overage
        self._monthly_request_limit = monthly_request_limit

    def allow_overage(self, account_id: str) -> bool:
        return self._allow_overage

    def monthly_request_limit(self, account_id: str, default_limit: int) -> int:
        return self._monthly_request_limit or default_limit


def test_valid_key_authenticates():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    assert principal.account_id == "acct_1"
    assert principal.plan.monthly_limit == 250
    assert principal.auth_method == "api_key"
    assert principal.rate_limit_profile == "free"


def test_api_key_plaintext_only_returned_at_creation():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
    )
    assert display_key.endswith(".test-secret")
    assert not hasattr(record, "secret")
    assert record.secret_hash != "test-secret"


def test_api_key_provider_returns_normalized_auth_context():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    event = {"headers": {"x-api-key": display_key}}

    context = ApiKeyAuthContextProvider(StaticApiKeyStore([record])).extract_context(event)

    assert context.account_id == "acct_1"
    assert context.credential_id == "dev_001"
    assert context.auth_method == "api_key"
    assert context.plan == "free"
    assert context.subscription is not None
    assert context.subscription.plan_code == "free"
    assert context.entitlements is not None
    assert context.entitlements.monthly_request_limit == 250
    assert context.rate_limit_profile == "free"
    assert event["_auth_context"] is context


def test_invalid_key_rejected():
    _, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
    )
    try:
        authenticate_api_key({"x-api-key": "csk_dev_001.badsecret"}, StaticApiKeyStore([record]))
    except AuthenticationError as exc:
        assert "Invalid API key" in str(exc)
    else:
        assert False, "Expected AuthenticationError"


def test_revoked_key_rejected():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        revoked=True,
    )
    try:
        authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    except AuthenticationError as exc:
        assert "revoked" in str(exc)
    else:
        assert False, "Expected AuthenticationError"


def test_missing_key_rejected():
    try:
        authenticate_api_key({}, StaticApiKeyStore([]))
    except AuthenticationError as exc:
        assert "Missing API key" in str(exc)
    else:
        assert False, "Expected AuthenticationError"


def test_quota_allows_overage_by_default():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store._usage[("acct_1", month_key)] = 250

    resolved_month, used, limit = enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", store)

    assert resolved_month == month_key
    assert used == 250
    assert limit == 250


def test_quota_hard_stop_when_overage_disabled():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store._usage[("acct_1", month_key)] = 250
    try:
        enforce_quota_and_scope(
            principal,
            "GET /v1/nonprofit/{ein}",
            store,
            billing_settings_resolver=_BillingSettingsResolver(False),
        )
    except QuotaExceededError as exc:
        assert exc.code == "quota_exceeded_hard_stop"
        assert "enable pay per request" in str(exc)
    else:
        assert False, "Expected QuotaExceededError"


def test_quota_uses_configured_monthly_request_cap_when_present():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="growth",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store._usage[("acct_1", month_key)] = 500

    try:
        enforce_quota_and_scope(
            principal,
            "GET /v1/nonprofit/{ein}",
            store,
            billing_settings_resolver=_BillingSettingsResolver(
                False,
                monthly_request_limit=500,
            ),
        )
    except QuotaExceededError as exc:
        assert exc.code == "quota_exceeded_hard_stop"
    else:
        assert False, "Expected QuotaExceededError"


def test_non_billable_checkout_route_bypasses_quota_hard_stop():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:write"],
        plan_id="free",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store._usage[("acct_1", month_key)] = 250

    resolved_month, used, limit = enforce_quota_and_scope(
        principal,
        "POST /v1/organization/billing/checkout-session",
        store,
        billing_settings_resolver=_BillingSettingsResolver(False),
        consumed_units=0,
    )

    assert resolved_month == month_key
    assert used == 250
    assert limit == 250


def test_non_billable_plan_change_route_bypasses_quota_hard_stop():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:write"],
        plan_id="free",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store._usage[("acct_1", month_key)] = 250

    resolved_month, used, limit = enforce_quota_and_scope(
        principal,
        "POST /v1/organization/billing/plan-change",
        store,
        billing_settings_resolver=_BillingSettingsResolver(False),
        consumed_units=0,
    )

    assert resolved_month == month_key
    assert used == 250
    assert limit == 250


def test_active_paid_subscription_allows_product_access():
    principal = AuthenticatedPrincipal(
        credential_id="key_1",
        account_id="acct_1",
        workspace_id="ws_1",
        plan=ApiPlan(plan_id="growth", monthly_limit=10000, entitlements=DEFAULT_ENTITLEMENTS["growth"]),
        scopes=("verify:read",),
        auth_method="api_key",
        rate_limit_profile="growth",
        subscription=Subscription(
            account_id="acct_1",
            plan_code="growth",
            status="active",
            billing_status="active",
        ),
        entitlements=DEFAULT_ENTITLEMENTS["growth"],
    )

    resolved_month, used, limit = enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", InMemoryUsageStore())

    assert resolved_month == monthly_period_for()
    assert used == 0
    assert limit == 10000


def test_past_due_billing_restricts_product_access():
    principal = AuthenticatedPrincipal(
        credential_id="key_1",
        account_id="acct_1",
        workspace_id="ws_1",
        plan=ApiPlan(plan_id="growth", monthly_limit=10000, entitlements=DEFAULT_ENTITLEMENTS["growth"]),
        scopes=("verify:read",),
        auth_method="api_key",
        rate_limit_profile="growth",
        subscription=Subscription(
            account_id="acct_1",
            plan_code="growth",
            status="active",
            billing_status="past_due",
        ),
        entitlements=DEFAULT_ENTITLEMENTS["growth"],
    )

    try:
        enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", InMemoryUsageStore())
    except BillingAccessError as exc:
        assert exc.code == "billing_past_due"
        assert exc.status_code == 402
    else:
        assert False, "Expected BillingAccessError"


def test_canceled_subscription_blocks_product_access():
    principal = AuthenticatedPrincipal(
        credential_id="key_1",
        account_id="acct_1",
        workspace_id="ws_1",
        plan=ApiPlan(plan_id="growth", monthly_limit=10000, entitlements=DEFAULT_ENTITLEMENTS["growth"]),
        scopes=("verify:read",),
        auth_method="api_key",
        rate_limit_profile="growth",
        subscription=Subscription(
            account_id="acct_1",
            plan_code="growth",
            status="canceled",
            billing_status="canceled",
        ),
        entitlements=DEFAULT_ENTITLEMENTS["growth"],
    )

    try:
        enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", InMemoryUsageStore())
    except BillingAccessError as exc:
        assert exc.code == "billing_canceled"
        assert exc.status_code == 402
    else:
        assert False, "Expected BillingAccessError"


def test_pending_downgrade_does_not_reduce_current_cycle_entitlements():
    principal = AuthenticatedPrincipal(
        credential_id="key_1",
        account_id="acct_1",
        workspace_id="ws_1",
        plan=ApiPlan(plan_id="pro", monthly_limit=100000, entitlements=DEFAULT_ENTITLEMENTS["pro"]),
        scopes=("verify:write",),
        auth_method="api_key",
        rate_limit_profile="pro",
        subscription=Subscription(
            account_id="acct_1",
            plan_code="pro",
            status="active",
            billing_status="active",
            pending_plan_code="growth",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
        ),
        entitlements=DEFAULT_ENTITLEMENTS["pro"],
    )

    resolved_month, used, limit = enforce_quota_and_scope(principal, "PUT /v1/organization/settings", InMemoryUsageStore())

    assert resolved_month == monthly_period_for()
    assert used == 0
    assert limit == 100000


def test_quota_metering_continues_past_limit_when_overage_allowed():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    event = {"headers": {"x-api-key": display_key}}
    context = ApiKeyAuthContextProvider(StaticApiKeyStore([record])).extract_context(event)
    store = InMemoryUsageStore()
    month_key = monthly_period_for()
    store._usage[("acct_1", month_key)] = 250

    hook = ApiKeyQuotaMeteringHook(store, billing_settings_resolver=_BillingSettingsResolver(True))
    hook.on_request(context, "GET /v1/nonprofit/{ein}")
    hook.on_response(context, "GET /v1/nonprofit/{ein}", 200)

    assert store.get_usage("acct_1", month_key) == 251


def test_quota_hook_starts_trial_on_first_customer_product_request():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id=account["id"],
        workspace_id=account["id"],
        scopes=["verify:write"],
        plan_id="free",
    )
    entitlement_service = EntitlementService(
        subscription_loader=lambda account_id: control_plane.store.get_subscription(account_id).to_subscription(),
        trial_config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    context = ApiKeyAuthContextProvider(
        StaticApiKeyStore([record]),
        entitlement_service=entitlement_service,
    ).extract_context({"headers": {"x-api-key": display_key}})
    hook = ApiKeyQuotaMeteringHook(
        InMemoryUsageStore(),
        entitlement_service=entitlement_service,
        trial_lifecycle_service=TrialLifecycleService(
            store=control_plane.store,
            config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
        ),
    )

    hook.on_request(context, "POST /v1/verify/batch")

    assert context.plan == "growth"
    assert context.subscription is not None
    assert context.subscription.plan_code == "free"
    assert context.subscription.trial_status == "active"
    assert context.entitlements is not None
    assert context.entitlements.plan_code == "growth"


def test_quota_hook_does_not_start_trial_for_billing_visibility_route():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id=account["id"],
        workspace_id=account["id"],
        scopes=["verify:read"],
        plan_id="free",
    )
    entitlement_service = EntitlementService(
        subscription_loader=lambda account_id: control_plane.store.get_subscription(account_id).to_subscription(),
        trial_config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    context = ApiKeyAuthContextProvider(
        StaticApiKeyStore([record]),
        entitlement_service=entitlement_service,
    ).extract_context({"headers": {"x-api-key": display_key}})
    hook = ApiKeyQuotaMeteringHook(
        InMemoryUsageStore(),
        entitlement_service=entitlement_service,
        trial_lifecycle_service=TrialLifecycleService(
            store=control_plane.store,
            config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
        ),
    )

    hook.on_request(context, "GET /v1/organization/billing/subscription")

    assert context.plan == "free"
    assert context.subscription is not None
    assert context.subscription.trial_status == "never_started"


def test_scoped_access_denied():
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    principal = authenticate_api_key({"x-api-key": display_key}, StaticApiKeyStore([record]))
    try:
        enforce_quota_and_scope(principal, "GET /v1/nonprofits/{ein}/federal-awards", InMemoryUsageStore())
    except AuthorizationError:
        pass
    else:
        assert False, "Expected AuthorizationError"


def test_lambda_query_enforces_auth_and_quota(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:read"],
        plan_id="free",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", {"ein": ein, "name": "X", "state": "IL", "status": "1", "deductibility": "1", "subsection": "03", "ntee_cd": "P20", "tax_period": "202501", "filing_req_cd": "1", "asset_amt": "", "income_amt": "", "revenue_amt": ""}),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()

    ok = module.handler({"httpMethod": "GET", "resource": "/v1/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {"x-api-key": display_key}}, None)
    assert ok["statusCode"] == 200
    missing = module.handler({"httpMethod": "GET", "resource": "/v1/nonprofit/{ein}", "pathParameters": {"ein": "123456789"}, "headers": {}}, None)
    assert missing["statusCode"] == 401


def test_entitlement_blocks_batch_for_free(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="dev_001",
        secret="test-secret",
        account_id="acct_1",
        workspace_id="ws_1",
        scopes=["verify:write"],
        plan_id="free",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "headers": {"x-api-key": display_key},
        "body": json.dumps({"items": [{"ein": "123456789"}]}),
    }
    response = module.handler(event, None)
    assert response["statusCode"] == 403


def test_batch_metering_counts_items_for_growth_plan(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    display_key, record = build_api_key_record(
        key_id="growth_001",
        secret="test-secret",
        account_id="acct_2",
        workspace_id="ws_2",
        scopes=["verify:write"],
        plan_id="growth",
    )
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([record.__dict__]))
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: ("qid-1", {"ein": ein, "name": "X", "state": "IL", "status": "1", "deductibility": "1", "subsection": "03", "ntee_cd": "P20", "tax_period": "202501", "filing_req_cd": "1", "asset_amt": "", "income_amt": "", "revenue_amt": ""}),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    module.usage_store = InMemoryUsageStore()
    event = {
        "httpMethod": "POST",
        "resource": "/v1/verify/batch",
        "path": "/v1/verify/batch",
        "headers": {"x-api-key": display_key},
        "body": json.dumps({"items": [{"ein": "123456789"}, {"ein": "987654321"}]}),
    }
    response = module.handler(event, None)
    assert response["statusCode"] == 200
    assert sum(module.usage_store._usage.values()) == 2
