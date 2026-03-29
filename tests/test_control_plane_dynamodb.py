from __future__ import annotations

import importlib
import json
import re
import sys
from types import SimpleNamespace

from charity_status.auth import build_admin_key_record, build_api_key_record
from charity_status.auth.errors import QuotaExceededError
from charity_status.auth.oauth import authenticate_oauth_client_credentials
from charity_status.auth.service import authenticate_api_key, enforce_quota_and_scope
from charity_status.control_plane import (
    Account,
    ControlPlaneService,
    DynamoControlPlaneStore,
    FakeDynamoResource,
    FakeDynamoTable,
    ManagedApiKey,
    ManagedBillingEvent,
    ManagedSubscription,
    ManagedTrialHistory,
)
from charity_status.enrichments import DynamoOrganizationIntegrationSettingsStore, OrganizationIntegrationSettingsService, load_organization_integration_settings


class _BillingSettingsResolver:
    def __init__(self, allow_overage: bool) -> None:
        self._allow_overage = allow_overage

    def allow_overage(self, account_id: str) -> bool:
        return self._allow_overage


def _query_stub():
    return SimpleNamespace(
        lookup_nonprofit=lambda ein, subsection=None: (
            "qid-1",
            {
                "ein": ein,
                "name": "X",
                "state": "IL",
                "status": "1",
                "deductibility": "1",
                "subsection": "03",
                "ntee_cd": "P20",
                "tax_period": "202501",
                "filing_req_cd": "1",
                "asset_amt": "",
                "income_amt": "",
                "revenue_amt": "",
            },
        ),
        lookup_form990_enrichment=lambda ein: ({}, {}, {}, {}),
        lookup_peer_benchmark=lambda group: {"count": 0, "metrics": {}},
        list_form990_filings=lambda ein, limit=10: ("qid-f", []),
        search_nonprofits=lambda **kwargs: ("qid-s", []),
    )


class _ApiKeyLookupStore:
    def __init__(self, store: DynamoControlPlaneStore) -> None:
        self._store = store

    def get(self, key_id: str):
        return self._store.get_api_key_record(key_id)


class _OAuthLookupStore:
    def __init__(self, store: DynamoControlPlaneStore) -> None:
        self._store = store

    def get(self, client_id: str):
        return self._store.get_oauth_client_record(client_id)


def test_dynamo_control_plane_persists_accounts_and_subscriptions_across_service_instances():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)

    service = ControlPlaneService(store=DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))
    created = service.create_account({"name": "Dynamo Account", "ein": "12-3456789"})
    account_id = created["id"]
    service.update_subscription(
        account_id,
        {
            "plan_code": "pro",
            "status": "active",
            "effective_from": "2026-03-18T00:00:00+00:00",
        },
    )

    reloaded = ControlPlaneService(store=DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))

    assert re.fullmatch(r"acct_[0-9a-f]{32}", account_id)
    assert reloaded.get_account(account_id)["name"] == "Dynamo Account"
    assert reloaded.get_account(account_id)["subscription"] == "pro"
    assert reloaded.get_account(account_id)["ein"] == "123456789"
    assert reloaded.get_subscription(account_id)["plan_code"] == "pro"
    assert reloaded.list_accounts()[0]["id"] == account_id
    assert reloaded.list_accounts()[0]["subscription"] == "pro"


def test_dynamo_control_plane_managed_credentials_authenticate_from_lookup_records():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    account = service.create_account({"name": "Auth Account", "ein": "123456789"})
    account_id = account["id"]

    api_key_payload = service.create_api_key(account_id, {"plan": "growth"})
    oauth_payload = service.create_oauth_client(account_id, {"plan": "growth"})
    key_id = api_key_payload["api_key"]["key_id"]
    client_id = oauth_payload["oauth_client"]["client_id"]

    api_principal = authenticate_api_key({"x-api-key": api_key_payload["secret"]}, _ApiKeyLookupStore(store))
    oauth_principal = authenticate_oauth_client_credentials(
        client_id,
        oauth_payload["client_secret"],
        _OAuthLookupStore(store),
    )

    api_record = store.get_api_key_record(key_id)
    oauth_record = store.get_oauth_client_record(client_id)

    assert api_principal.account_id == account_id
    assert oauth_principal.account_id == account_id
    assert re.fullmatch(r"key_[0-9a-f]{32}", key_id)
    assert re.fullmatch(r"client_[0-9a-f]{32}", client_id)
    assert api_record is not None and api_record.secret_hash != api_key_payload["secret"]
    assert oauth_record is not None and oauth_record.client_secret_hash != oauth_payload["client_secret"]


def test_dynamo_usage_persists_quota_state_across_service_reinitialization():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    account = service.create_account({"name": "Quota Account", "ein": "123456789"})
    account_id = account["id"]
    api_key_payload = service.create_api_key(account_id, {"plan": "free"})

    principal = authenticate_api_key({"x-api-key": api_key_payload["secret"]}, _ApiKeyLookupStore(store))
    month_key, _, _ = enforce_quota_and_scope(principal, "GET /v1/nonprofit/{ein}", store)
    store.increment_usage(account_id, month_key, 250)

    reloaded_store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    try:
        enforce_quota_and_scope(
            principal,
            "GET /v1/nonprofit/{ein}",
            reloaded_store,
            billing_settings_resolver=_BillingSettingsResolver(False),
        )
    except QuotaExceededError:
        pass
    else:
        assert False, "Expected QuotaExceededError"


def test_dynamo_organization_settings_billing_round_trip():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoOrganizationIntegrationSettingsStore("organization-settings", dynamodb_resource=resource)
    service = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=store,
    )

    updated = service.update_settings(
        workspace_id="ws_1",
        account_id="acct_1",
        payload={"billing": {"allowOverage": False, "monthlyRequestCap": 750}},
    )
    reloaded = OrganizationIntegrationSettingsService(
        fallback_resolver=load_organization_integration_settings("[]"),
        store=DynamoOrganizationIntegrationSettingsStore("organization-settings", dynamodb_resource=resource),
    )
    current = reloaded.get_settings(workspace_id="ws_1", account_id="acct_1")

    assert updated.billing_settings.allow_overage is False
    assert updated.billing_settings.monthly_request_cap == 750
    assert current.billing_settings.allow_overage is False
    assert current.billing_settings.monthly_request_cap == 750
    assert current.to_dict()["billing"]["allowOverage"] is False
    assert current.to_dict()["billing"]["monthlyRequestCap"] == 750


def test_dynamo_control_plane_persists_pending_stripe_checkout_linkage():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    account = service.create_account({"name": "Billing Account", "ein": "123456789"})
    account_id = account["id"]

    service.store.put_subscription(
        ManagedSubscription(
            account_id=account_id,
            plan_code="free",
            status="active",
            effective_from="2026-03-18T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            billing_status="checkout_pending",
            pending_plan_code="growth",
            pending_checkout_session_id="cs_test_123",
            pending_checkout_session_url="https://checkout.stripe.com/c/pay/cs_test_123",
            pending_checkout_expires_at="2099-03-20T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )

    reloaded = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource).get_subscription(account_id)

    assert reloaded is not None
    assert reloaded.stripe_customer_id == "cus_test_123"
    assert reloaded.billing_status == "checkout_pending"
    assert reloaded.pending_plan_code == "growth"
    assert reloaded.pending_checkout_session_id == "cs_test_123"
    assert reloaded.pending_checkout_session_url == "https://checkout.stripe.com/c/pay/cs_test_123"


def test_dynamo_control_plane_supports_stripe_lookup_and_billing_event_round_trip():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    account = service.create_account({"name": "Billing Account", "ein": "123456789"})
    account_id = account["id"]

    store.put_subscription(
        ManagedSubscription(
            account_id=account_id,
            plan_code="growth",
            status="active",
            effective_from="2026-03-18T00:00:00+00:00",
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            stripe_subscription_schedule_id="sub_sched_test_123",
            billing_status="active",
            pending_plan_code="starter",
            pending_plan_effective_at="2026-04-01T00:00:00+00:00",
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )
    store.put_billing_event(
        ManagedBillingEvent(
            event_id="evt_test_123",
            event_type="invoice.paid",
            processed_at="2026-03-19T00:00:00+00:00",
            account_id=account_id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            stripe_invoice_id="in_test_123",
            gross_amount=10000,
            tax_amount=800,
            invoice_total=10800,
            currency="usd",
        )
    )

    by_customer = store.get_subscription_by_stripe_customer_id("cus_test_123")
    by_subscription = store.get_subscription_by_stripe_subscription_id("sub_test_123")
    billing_event = store.get_billing_event("evt_test_123")

    assert by_customer is not None and by_customer.account_id == account_id
    assert by_subscription is not None and by_subscription.account_id == account_id
    assert by_subscription.pending_plan_code == "starter"
    assert by_subscription.pending_plan_effective_at == "2026-04-01T00:00:00+00:00"
    assert by_subscription.stripe_subscription_schedule_id == "sub_sched_test_123"
    assert billing_event is not None
    assert billing_event.stripe_invoice_id == "in_test_123"
    assert billing_event.invoice_total == 10800


def test_dynamo_control_plane_persists_trial_state_on_subscription_records():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)
    account = service.create_account({"name": "Trial Account", "ein": "123456789"})
    account_id = account["id"]

    store.put_subscription(
        ManagedSubscription(
            account_id=account_id,
            plan_code="free",
            status="active",
            effective_from="2026-03-19T00:00:00+00:00",
            trial_status="active",
            trial_started_at="2026-03-19T00:00:00+00:00",
            trial_ends_at="2026-04-02T00:00:00+00:00",
            trial_trigger_event="GET /v1/nonprofit/{ein}",
            trial_consumed=True,
            updated_at="2026-03-19T00:00:00+00:00",
        )
    )

    reloaded = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource).get_subscription(account_id)

    assert reloaded is not None
    assert reloaded.trial_status == "active"
    assert reloaded.trial_started_at == "2026-03-19T00:00:00+00:00"
    assert reloaded.trial_ends_at == "2026-04-02T00:00:00+00:00"
    assert reloaded.trial_trigger_event == "GET /v1/nonprofit/{ein}"
    assert reloaded.trial_consumed is True


def test_dynamo_control_plane_persists_trial_history_by_ein():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)

    store.put_trial_history(
        ManagedTrialHistory(
            ein="123456789",
            trial_consumed=True,
            first_account_id="acct_first",
            last_account_id="acct_last",
            trial_started_at="2026-03-19T00:00:00+00:00",
            trial_ended_at="2026-04-02T00:00:00+00:00",
            last_status="expired",
            last_termination_reason="expired_to_free",
            updated_at="2026-04-02T00:00:00+00:00",
        )
    )

    reloaded = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource).get_trial_history("123456789")

    assert reloaded is not None
    assert reloaded.first_account_id == "acct_first"
    assert reloaded.last_account_id == "acct_last"
    assert reloaded.last_status == "expired"
    assert reloaded.last_termination_reason == "expired_to_free"


def test_lambda_query_uses_dynamo_control_plane_when_table_name_is_configured(monkeypatch):
    import charity_status.control_plane.dynamodb_store as dynamodb_module

    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    admin_key, admin_record = build_admin_key_record("root", secret="admin-secret")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "true")
    monkeypatch.setenv("API_KEY_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", "[]")
    monkeypatch.setenv("ADMIN_KEY_RECORDS_JSON", json.dumps([admin_record.__dict__]))
    monkeypatch.setenv("CONTROL_PLANE_TABLE_NAME", "control-plane")
    monkeypatch.setattr(dynamodb_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))

    created = module.handler(
        {
            "httpMethod": "POST",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {"x-admin-key": admin_key, "Content-Type": "application/json"},
            "body": json.dumps({"name": "Lambda Dynamo", "ein": "123456789"}),
        },
        None,
    )
    assert created["statusCode"] == 201
    created_account_id = json.loads(created["body"])["data"]["id"]
    assert re.fullmatch(r"acct_[0-9a-f]{32}", created_account_id)

    module.control_plane_service = None

    listed = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/admin/accounts",
            "path": "/v1/admin/accounts",
            "headers": {"x-admin-key": admin_key},
        },
        None,
    )
    payload = json.loads(listed["body"])

    assert listed["statusCode"] == 200
    assert payload["data"]["items"][0]["id"] == created_account_id
    assert payload["data"]["items"][0]["ein"] == "123456789"


def test_managed_api_key_takes_precedence_over_bootstrap_env_record(monkeypatch):
    import charity_status.control_plane.dynamodb_store as dynamodb_module

    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    admin_key, admin_record = build_admin_key_record("root", secret="admin-secret")
    bootstrap_secret, bootstrap_record = build_api_key_record(
        key_id="dup_key",
        secret="env-secret",
        account_id="acct_bootstrap",
        workspace_id="acct_bootstrap",
        scopes=["verify:read"],
        plan_id="free",
    )
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("OAUTH_M2M_ENABLED", "false")
    monkeypatch.setenv("API_KEY_RECORDS_JSON", json.dumps([bootstrap_record.__dict__]))
    monkeypatch.setenv("OAUTH_TOKEN_RECORDS_JSON", "[]")
    monkeypatch.setenv("OAUTH_CLIENT_RECORDS_JSON", "[]")
    monkeypatch.setenv("ADMIN_KEY_RECORDS_JSON", json.dumps([admin_record.__dict__]))
    monkeypatch.setenv("CONTROL_PLANE_TABLE_NAME", "control-plane")
    monkeypatch.setattr(dynamodb_module.boto3, "resource", lambda service_name: resource)
    sys.modules.pop("infrastructure.lambda_query", None)
    module = importlib.import_module("infrastructure.lambda_query")
    module.SERVING_DDB_ENABLED = False
    module.athena_client = _query_stub()
    module.enrichment_service = SimpleNamespace(enrich=lambda ein, organization_name=None: SimpleNamespace(to_dict=lambda: {"providers": [], "failures": []}))
    service = module._get_control_plane_service()
    account = service.create_account({"name": "Managed Account", "ein": "123456789"})
    account_id = account["id"]
    managed_secret, managed_record = build_api_key_record(
        key_id="dup_key",
        secret="managed-secret",
        account_id=account_id,
        workspace_id=account_id,
        scopes=["verify:read"],
        plan_id="growth",
    )
    service.store.put_api_key(
        ManagedApiKey(
            key_id=managed_record.key_id,
            account_id=account_id,
            status="active",
            created_at="2026-03-18T00:00:00+00:00",
            plan=managed_record.plan_id,
            scopes=managed_record.scopes,
            rate_limit_profile=managed_record.rate_limit_profile,
        ),
        managed_record,
    )

    managed_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": managed_secret},
        },
        None,
    )
    bootstrap_response = module.handler(
        {
            "httpMethod": "GET",
            "resource": "/v1/nonprofit/{ein}",
            "path": "/v1/nonprofit/123456789",
            "pathParameters": {"ein": "123456789"},
            "headers": {"x-api-key": bootstrap_secret},
        },
        None,
    )

    assert managed_response["statusCode"] == 403
    assert bootstrap_response["statusCode"] == 401


def test_existing_non_uuid_identifiers_remain_readable_in_dynamo_store():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    store = DynamoControlPlaneStore("control-plane", dynamodb_resource=resource)
    service = ControlPlaneService(store=store)

    legacy_account_id = "acct_legacy"
    service.store.put_account(
        Account(
            id=legacy_account_id,
            name="Legacy Account",
            status="active",
            created_at="2026-03-18T00:00:00+00:00",
        )
    )
    service.store.put_subscription(
        ManagedSubscription(
            account_id=legacy_account_id,
            plan_code="free",
            status="active",
            effective_from="2026-03-18T00:00:00+00:00",
            effective_to=None,
        )
    )

    assert service.get_account(legacy_account_id)["id"] == legacy_account_id
    assert service.get_account(legacy_account_id)["subscription"] == "free"
    assert service.get_account(legacy_account_id)["ein"] is None


def test_legacy_dynamo_account_without_subscription_returns_null_subscription():
    table = FakeDynamoTable()
    resource = FakeDynamoResource(table)
    service = ControlPlaneService(store=DynamoControlPlaneStore("control-plane", dynamodb_resource=resource))

    service.store.put_account(
        Account(
            id="acct_legacy_no_sub",
            name="Legacy No Subscription",
            status="active",
            created_at="2026-03-18T00:00:00+00:00",
        )
    )

    account = service.get_account("acct_legacy_no_sub")

    assert account["subscription"] is None
