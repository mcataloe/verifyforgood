from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import importlib
from typing import Any

from verification.auth.oauth import StoredOAuthClientRecord
from verification.auth.service import StoredApiKeyRecord

from .models import Account, ManagedApiKey, ManagedBillingCustomer, ManagedBillingEvent, ManagedOAuthClient, ManagedSubscription, ManagedTrialHistory


class DynamoControlPlaneStore:
    def __init__(self, table_name: str, dynamodb_resource: Any | None = None) -> None:
        self._table_name = table_name
        self._resource = dynamodb_resource or _load_boto3().resource("dynamodb")
        self._table = self._resource.Table(table_name)

    def list_accounts(self) -> list[Account]:
        response = self._table.query(
            IndexName="entity_listing",
            KeyConditionExpression="gsi2pk = :gsi2pk",
            ExpressionAttributeValues={":gsi2pk": "ENTITY#ACCOUNT"},
        )
        items = response.get("Items") or []
        return [_account_from_item(item) for item in items if item.get("type") == "ACCOUNT"]

    def get_account(self, account_id: str) -> Account | None:
        response = self._table.get_item(Key={"pk": _account_pk(account_id), "sk": "ACCOUNT"})
        item = response.get("Item")
        if item is None:
            return None
        return _account_from_item(item)

    def put_account(self, account: Account) -> None:
        self._table.put_item(Item=_account_item(account))

    def get_subscription(self, account_id: str) -> ManagedSubscription | None:
        response = self._table.get_item(Key={"pk": _account_pk(account_id), "sk": "SUBSCRIPTION"})
        item = response.get("Item")
        if item is None:
            return None
        return _subscription_from_item(item)

    def put_subscription(self, subscription: ManagedSubscription) -> None:
        self._table.put_item(Item=_subscription_item(subscription))

    def get_billing_customer(self, account_id: str) -> ManagedBillingCustomer | None:
        response = self._table.get_item(Key={"pk": _account_pk(account_id), "sk": "BILLING_CUSTOMER"})
        item = response.get("Item")
        if item is None:
            return None
        return _billing_customer_from_item(item)

    def put_billing_customer(self, customer: ManagedBillingCustomer) -> None:
        self._table.put_item(Item=_billing_customer_item(customer))

    def get_billing_customer_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedBillingCustomer | None:
        response = self._table.query(
            IndexName="entity_listing",
            KeyConditionExpression="gsi2pk = :gsi2pk",
            ExpressionAttributeValues={":gsi2pk": f"ENTITY#BILLING_CUSTOMER#{stripe_customer_id}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _billing_customer_from_item(items[0])

    def get_subscription_by_stripe_customer_id(self, stripe_customer_id: str) -> ManagedSubscription | None:
        response = self._table.query(
            IndexName="credential_lookup",
            KeyConditionExpression="gsi1pk = :gsi1pk",
            ExpressionAttributeValues={":gsi1pk": f"STRIPE#CUSTOMER#{stripe_customer_id}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _subscription_from_item(items[0])

    def get_subscription_by_stripe_subscription_id(self, stripe_subscription_id: str) -> ManagedSubscription | None:
        response = self._table.query(
            IndexName="entity_listing",
            KeyConditionExpression="gsi2pk = :gsi2pk",
            ExpressionAttributeValues={":gsi2pk": f"STRIPE#SUBSCRIPTION#{stripe_subscription_id}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _subscription_from_item(items[0])

    def get_billing_event(self, event_id: str) -> ManagedBillingEvent | None:
        response = self._table.get_item(Key={"pk": _billing_event_pk(event_id), "sk": "EVENT"})
        item = response.get("Item")
        if item is None:
            return None
        return _billing_event_from_item(item)

    def put_billing_event(self, event: ManagedBillingEvent) -> None:
        self._table.put_item(Item=_billing_event_item(event))

    def get_trial_history(self, ein: str) -> ManagedTrialHistory | None:
        response = self._table.get_item(Key={"pk": _trial_history_pk(ein), "sk": "TRIAL"})
        item = response.get("Item")
        if item is None:
            return None
        return _trial_history_from_item(item)

    def put_trial_history(self, history: ManagedTrialHistory) -> None:
        self._table.put_item(Item=_trial_history_item(history))

    def list_api_keys(self, account_id: str) -> list[ManagedApiKey]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _account_pk(account_id), ":prefix": "APIKEY#"},
        )
        items = response.get("Items") or []
        return [_api_key_model_from_item(item) for item in items if item.get("type") == "API_KEY"]

    def get_api_key(self, account_id: str, key_id: str) -> tuple[ManagedApiKey, StoredApiKeyRecord] | None:
        response = self._table.get_item(Key={"pk": _account_pk(account_id), "sk": f"APIKEY#{key_id}"})
        item = response.get("Item")
        if item is None:
            return None
        return _api_key_model_from_item(item), _api_key_record_from_item(item)

    def get_api_key_record(self, key_id: str) -> StoredApiKeyRecord | None:
        response = self._table.query(
            IndexName="credential_lookup",
            KeyConditionExpression="gsi1pk = :gsi1pk",
            ExpressionAttributeValues={":gsi1pk": f"CREDENTIAL#APIKEY#{key_id}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _api_key_record_from_item(items[0])

    def put_api_key(self, model: ManagedApiKey, record: StoredApiKeyRecord) -> None:
        self._table.put_item(Item=_api_key_item(model, record))

    def list_oauth_clients(self, account_id: str) -> list[ManagedOAuthClient]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :prefix)",
            ExpressionAttributeValues={":pk": _account_pk(account_id), ":prefix": "OAUTHCLIENT#"},
        )
        items = response.get("Items") or []
        return [_oauth_client_model_from_item(item) for item in items if item.get("type") == "OAUTH_CLIENT"]

    def get_oauth_client(self, account_id: str, client_id: str) -> tuple[ManagedOAuthClient, StoredOAuthClientRecord] | None:
        response = self._table.get_item(Key={"pk": _account_pk(account_id), "sk": f"OAUTHCLIENT#{client_id}"})
        item = response.get("Item")
        if item is None:
            return None
        return _oauth_client_model_from_item(item), _oauth_client_record_from_item(item)

    def get_oauth_client_record(self, client_id: str) -> StoredOAuthClientRecord | None:
        response = self._table.query(
            IndexName="credential_lookup",
            KeyConditionExpression="gsi1pk = :gsi1pk",
            ExpressionAttributeValues={":gsi1pk": f"CREDENTIAL#OAUTHCLIENT#{client_id}"},
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return _oauth_client_record_from_item(items[0])

    def put_oauth_client(self, model: ManagedOAuthClient, record: StoredOAuthClientRecord) -> None:
        self._table.put_item(Item=_oauth_client_item(model, record))

    def get_usage(self, account_id: str, month_key: str) -> int:
        response = self._table.get_item(Key={"pk": _account_pk(account_id), "sk": f"USAGE#{month_key}"})
        item = response.get("Item")
        if item is None:
            return 0
        return _int_value(item.get("request_count"))

    def increment_usage(self, account_id: str, month_key: str, units: int = 1) -> int:
        delta = max(0, int(units))
        updated_at = datetime.now(timezone.utc).isoformat()
        response = self._table.update_item(
            Key={"pk": _account_pk(account_id), "sk": f"USAGE#{month_key}"},
            UpdateExpression="SET #type = :type, account_id = :account_id, period_key = :period_key, updated_at = :updated_at ADD request_count :delta",
            ExpressionAttributeNames={"#type": "type"},
            ExpressionAttributeValues={
                ":type": "USAGE",
                ":account_id": account_id,
                ":period_key": month_key,
                ":updated_at": updated_at,
                ":delta": delta,
            },
            ReturnValues="ALL_NEW",
        )
        return _int_value((response.get("Attributes") or {}).get("request_count"))

    def increment(self, account_id: str, month_key: str) -> None:
        self.increment_usage(account_id, month_key, units=1)


def _account_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _account_item(account: Account) -> dict[str, Any]:
    return {
        "pk": _account_pk(account.id),
        "sk": "ACCOUNT",
        "gsi2pk": "ENTITY#ACCOUNT",
        "gsi2sk": f"{account.created_at}#{account.id}",
        "type": "ACCOUNT",
        "account_id": account.id,
        "name": account.name,
        "ein": account.ein,
        "status": account.status,
        "created_at": account.created_at,
    }


def _subscription_item(subscription: ManagedSubscription) -> dict[str, Any]:
    item = {
        "pk": _account_pk(subscription.account_id),
        "sk": "SUBSCRIPTION",
        "type": "SUBSCRIPTION",
        "account_id": subscription.account_id,
        "plan_code": subscription.plan_code,
        "status": subscription.status,
        "created_at": subscription.created_at,
        "effective_from": subscription.effective_from,
        "effective_to": subscription.effective_to,
        "stripe_customer_id": subscription.stripe_customer_id,
        "stripe_subscription_id": subscription.stripe_subscription_id,
        "billing_status": subscription.billing_status,
        "billing_period_start": subscription.billing_period_start,
        "billing_period_end": subscription.billing_period_end,
        "grace_period_ends_at": subscription.grace_period_ends_at,
        "trial_status": subscription.trial_status,
        "trial_started_at": subscription.trial_started_at,
        "trial_ends_at": subscription.trial_ends_at,
        "trial_trigger_event": subscription.trial_trigger_event,
        "trial_consumed": subscription.trial_consumed,
        "trial_termination_reason": subscription.trial_termination_reason,
        "pending_plan_code": subscription.pending_plan_code,
        "pending_plan_effective_at": subscription.pending_plan_effective_at,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "stripe_subscription_schedule_id": subscription.stripe_subscription_schedule_id,
        "pending_checkout_session_id": subscription.pending_checkout_session_id,
        "pending_checkout_session_url": subscription.pending_checkout_session_url,
        "pending_checkout_expires_at": subscription.pending_checkout_expires_at,
        "updated_at": subscription.updated_at,
    }
    if subscription.stripe_customer_id:
        item["gsi1pk"] = f"STRIPE#CUSTOMER#{subscription.stripe_customer_id}"
        item["gsi1sk"] = _account_pk(subscription.account_id)
    if subscription.stripe_subscription_id:
        item["gsi2pk"] = f"STRIPE#SUBSCRIPTION#{subscription.stripe_subscription_id}"
        item["gsi2sk"] = _account_pk(subscription.account_id)
    return item


def _billing_customer_item(customer: ManagedBillingCustomer) -> dict[str, Any]:
    return {
        "pk": _account_pk(customer.account_id),
        "sk": "BILLING_CUSTOMER",
        "gsi2pk": f"ENTITY#BILLING_CUSTOMER#{customer.stripe_customer_id}",
        "gsi2sk": _account_pk(customer.account_id),
        "type": "BILLING_CUSTOMER",
        "account_id": customer.account_id,
        "organization_id": customer.organization_id,
        "stripe_customer_id": customer.stripe_customer_id,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
    }


def _billing_event_pk(event_id: str) -> str:
    return f"BILLINGEVENT#{event_id}"


def _trial_history_pk(ein: str) -> str:
    return f"TRIALHISTORY#{ein}"


def _billing_event_item(event: ManagedBillingEvent) -> dict[str, Any]:
    return {
        "pk": _billing_event_pk(event.event_id),
        "sk": "EVENT",
        "type": "BILLING_EVENT",
        "event_id": event.event_id,
        "event_type": event.event_type,
        "processed_at": event.processed_at,
        "account_id": event.account_id,
        "processing_outcome": event.processing_outcome,
        "stripe_customer_id": event.stripe_customer_id,
        "stripe_subscription_id": event.stripe_subscription_id,
        "stripe_invoice_id": event.stripe_invoice_id,
        "gross_amount": event.gross_amount,
        "tax_amount": event.tax_amount,
        "invoice_total": event.invoice_total,
        "currency": event.currency,
        "webhook_created_at": event.webhook_created_at,
        "payload_fingerprint": event.payload_fingerprint,
    }


def _trial_history_item(history: ManagedTrialHistory) -> dict[str, Any]:
    return {
        "pk": _trial_history_pk(history.ein),
        "sk": "TRIAL",
        "type": "TRIAL_HISTORY",
        "ein": history.ein,
        "trial_consumed": history.trial_consumed,
        "first_account_id": history.first_account_id,
        "last_account_id": history.last_account_id,
        "trial_started_at": history.trial_started_at,
        "trial_ended_at": history.trial_ended_at,
        "last_status": history.last_status,
        "last_termination_reason": history.last_termination_reason,
        "updated_at": history.updated_at,
    }


def _api_key_item(model: ManagedApiKey, record: StoredApiKeyRecord) -> dict[str, Any]:
    return {
        "pk": _account_pk(model.account_id),
        "sk": f"APIKEY#{model.key_id}",
        "gsi1pk": f"CREDENTIAL#APIKEY#{model.key_id}",
        "gsi1sk": _account_pk(model.account_id),
        "type": "API_KEY",
        "key_id": model.key_id,
        "account_id": model.account_id,
        "workspace_id": record.workspace_id,
        "scopes": list(record.scopes),
        "status": model.status,
        "created_at": model.created_at,
        "secret_hash": record.secret_hash,
        "plan_id": record.plan_id,
        "rate_limit_profile": record.rate_limit_profile,
        "revoked": record.revoked,
    }


def _oauth_client_item(model: ManagedOAuthClient, record: StoredOAuthClientRecord) -> dict[str, Any]:
    return {
        "pk": _account_pk(model.account_id),
        "sk": f"OAUTHCLIENT#{model.client_id}",
        "gsi1pk": f"CREDENTIAL#OAUTHCLIENT#{model.client_id}",
        "gsi1sk": _account_pk(model.account_id),
        "type": "OAUTH_CLIENT",
        "client_id": model.client_id,
        "account_id": model.account_id,
        "workspace_id": record.workspace_id,
        "scopes": list(record.scopes),
        "status": model.status,
        "created_at": model.created_at,
        "client_secret_hash": record.client_secret_hash,
        "plan_id": record.plan_id,
        "rate_limit_profile": record.rate_limit_profile,
        "revoked": record.revoked,
    }


def _account_from_item(item: dict[str, Any]) -> Account:
    return Account(
        id=str(item.get("account_id") or ""),
        name=str(item.get("name") or ""),
        status=str(item.get("status") or "active"),
        created_at=str(item.get("created_at") or ""),
        ein=_optional_string(item.get("ein")),
    )


def _subscription_from_item(item: dict[str, Any]) -> ManagedSubscription:
    return ManagedSubscription(
        account_id=str(item.get("account_id") or ""),
        plan_code=str(item.get("plan_code") or "free"),
        status=str(item.get("status") or "active"),
        created_at=_optional_string(item.get("created_at")),
        effective_from=_optional_string(item.get("effective_from")),
        effective_to=_optional_string(item.get("effective_to")),
        stripe_customer_id=_optional_string(item.get("stripe_customer_id")),
        stripe_subscription_id=_optional_string(item.get("stripe_subscription_id")),
        billing_status=_optional_string(item.get("billing_status")),
        billing_period_start=_optional_string(item.get("billing_period_start")),
        billing_period_end=_optional_string(item.get("billing_period_end")),
        grace_period_ends_at=_optional_string(item.get("grace_period_ends_at")),
        trial_status=_optional_string(item.get("trial_status")),
        trial_started_at=_optional_string(item.get("trial_started_at")),
        trial_ends_at=_optional_string(item.get("trial_ends_at")),
        trial_trigger_event=_optional_string(item.get("trial_trigger_event")),
        trial_consumed=bool(item.get("trial_consumed", False)),
        trial_termination_reason=_optional_string(item.get("trial_termination_reason")),
        pending_plan_code=_optional_string(item.get("pending_plan_code")),
        pending_plan_effective_at=_optional_string(item.get("pending_plan_effective_at")),
        cancel_at_period_end=bool(item.get("cancel_at_period_end", False)),
        stripe_subscription_schedule_id=_optional_string(item.get("stripe_subscription_schedule_id")),
        pending_checkout_session_id=_optional_string(item.get("pending_checkout_session_id")),
        pending_checkout_session_url=_optional_string(item.get("pending_checkout_session_url")),
        pending_checkout_expires_at=_optional_string(item.get("pending_checkout_expires_at")),
        updated_at=_optional_string(item.get("updated_at")),
    )


def _billing_customer_from_item(item: dict[str, Any]) -> ManagedBillingCustomer:
    return ManagedBillingCustomer(
        account_id=str(item.get("account_id") or ""),
        organization_id=str(item.get("organization_id") or item.get("account_id") or ""),
        stripe_customer_id=str(item.get("stripe_customer_id") or ""),
        created_at=str(item.get("created_at") or ""),
        updated_at=str(item.get("updated_at") or ""),
    )


def _trial_history_from_item(item: dict[str, Any]) -> ManagedTrialHistory:
    return ManagedTrialHistory(
        ein=str(item.get("ein") or ""),
        trial_consumed=bool(item.get("trial_consumed", False)),
        first_account_id=_optional_string(item.get("first_account_id")),
        last_account_id=_optional_string(item.get("last_account_id")),
        trial_started_at=_optional_string(item.get("trial_started_at")),
        trial_ended_at=_optional_string(item.get("trial_ended_at")),
        last_status=_optional_string(item.get("last_status")),
        last_termination_reason=_optional_string(item.get("last_termination_reason")),
        updated_at=_optional_string(item.get("updated_at")),
    )


def _billing_event_from_item(item: dict[str, Any]) -> ManagedBillingEvent:
    return ManagedBillingEvent(
        event_id=str(item.get("event_id") or ""),
        event_type=str(item.get("event_type") or ""),
        processed_at=str(item.get("processed_at") or ""),
        account_id=_optional_string(item.get("account_id")),
        processing_outcome=_optional_string(item.get("processing_outcome")),
        stripe_customer_id=_optional_string(item.get("stripe_customer_id")),
        stripe_subscription_id=_optional_string(item.get("stripe_subscription_id")),
        stripe_invoice_id=_optional_string(item.get("stripe_invoice_id")),
        gross_amount=_optional_int(item.get("gross_amount")),
        tax_amount=_optional_int(item.get("tax_amount")),
        invoice_total=_optional_int(item.get("invoice_total")),
        currency=_optional_string(item.get("currency")),
        webhook_created_at=_optional_string(item.get("webhook_created_at")),
        payload_fingerprint=_optional_string(item.get("payload_fingerprint")),
    )


def _api_key_model_from_item(item: dict[str, Any]) -> ManagedApiKey:
    return ManagedApiKey(
        key_id=str(item.get("key_id") or ""),
        account_id=str(item.get("account_id") or ""),
        status=str(item.get("status") or "active"),
        created_at=str(item.get("created_at") or ""),
        plan=str(item.get("plan_id") or "free"),
        scopes=tuple(str(scope) for scope in (item.get("scopes") or [])),
        rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
    )


def _api_key_record_from_item(item: dict[str, Any]) -> StoredApiKeyRecord:
    return StoredApiKeyRecord(
        key_id=str(item.get("key_id") or ""),
        secret_hash=str(item.get("secret_hash") or ""),
        account_id=str(item.get("account_id") or ""),
        workspace_id=str(item.get("workspace_id") or ""),
        scopes=tuple(str(scope) for scope in (item.get("scopes") or [])),
        revoked=bool(item.get("revoked", False)),
        plan_id=str(item.get("plan_id") or "free"),
        rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
    )


def _oauth_client_model_from_item(item: dict[str, Any]) -> ManagedOAuthClient:
    return ManagedOAuthClient(
        client_id=str(item.get("client_id") or ""),
        account_id=str(item.get("account_id") or ""),
        status=str(item.get("status") or "active"),
        created_at=str(item.get("created_at") or ""),
        plan=str(item.get("plan_id") or "free"),
        scopes=tuple(str(scope) for scope in (item.get("scopes") or [])),
        rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
    )


def _oauth_client_record_from_item(item: dict[str, Any]) -> StoredOAuthClientRecord:
    return StoredOAuthClientRecord(
        client_id=str(item.get("client_id") or ""),
        client_secret_hash=str(item.get("client_secret_hash") or ""),
        account_id=str(item.get("account_id") or ""),
        workspace_id=str(item.get("workspace_id") or ""),
        scopes=tuple(str(scope) for scope in (item.get("scopes") or [])),
        revoked=bool(item.get("revoked", False)),
        plan_id=str(item.get("plan_id") or "free"),
        rate_limit_profile=str(item.get("rate_limit_profile") or item.get("plan_id") or "free"),
    )


def _optional_string(value: Any) -> str | None:
    candidate = str(value or "").strip()
    return candidate or None


def _int_value(value: Any) -> int:
    if isinstance(value, Decimal):
        return int(value)
    if value is None:
        return 0
    return int(value)


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return _int_value(value)


class FakeDynamoTable:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict[str, Any]] = {}

    def put_item(self, Item):  # noqa: N803
        self._items[(Item["pk"], Item["sk"])] = deepcopy(Item)
        return {}

    def get_item(self, Key):  # noqa: N803
        item = self._items.get((Key["pk"], Key["sk"]))
        return {"Item": deepcopy(item)} if item is not None else {}

    def query(self, IndexName=None, KeyConditionExpression=None, ExpressionAttributeValues=None, Limit=None):  # noqa: N803
        values = ExpressionAttributeValues or {}
        items = list(self._items.values())
        if IndexName == "entity_listing":
            matches = [item for item in items if item.get("gsi2pk") == values.get(":gsi2pk")]
            matches.sort(key=lambda item: str(item.get("gsi2sk") or ""))
        elif IndexName == "credential_lookup":
            matches = [item for item in items if item.get("gsi1pk") == values.get(":gsi1pk")]
            matches.sort(key=lambda item: str(item.get("gsi1sk") or ""))
        elif KeyConditionExpression == "pk = :pk AND begins_with(sk, :prefix)":
            matches = [
                item
                for item in items
                if item.get("pk") == values.get(":pk") and str(item.get("sk") or "").startswith(str(values.get(":prefix") or ""))
            ]
            matches.sort(key=lambda item: str(item.get("sk") or ""))
        else:
            matches = [item for item in items if item.get("pk") == values.get(":pk")]
            matches.sort(key=lambda item: str(item.get("sk") or ""))
        if Limit is not None:
            matches = matches[:Limit]
        return {"Items": [deepcopy(item) for item in matches]}

    def update_item(
        self,
        Key,
        UpdateExpression,
        ExpressionAttributeNames=None,
        ExpressionAttributeValues=None,
        ReturnValues=None,
    ):  # noqa: N803
        item = deepcopy(self._items.get((Key["pk"], Key["sk"]), {"pk": Key["pk"], "sk": Key["sk"]}))
        names = ExpressionAttributeNames or {}
        values = ExpressionAttributeValues or {}
        set_section, add_section = UpdateExpression.split(" ADD ", 1)
        for assignment in set_section.replace("SET ", "", 1).split(", "):
            attribute, value_ref = assignment.split(" = ", 1)
            attribute_name = names.get(attribute, attribute)
            item[attribute_name] = deepcopy(values[value_ref])
        add_attribute, add_value_ref = add_section.split(" ", 1)
        current = _int_value(item.get(add_attribute))
        item[add_attribute] = current + _int_value(values[add_value_ref])
        self._items[(Key["pk"], Key["sk"])] = item
        if ReturnValues == "ALL_NEW":
            return {"Attributes": deepcopy(item)}
        return {}


class FakeDynamoResource:
    def __init__(self, table: FakeDynamoTable) -> None:
        self._table = table

    def Table(self, name: str):  # noqa: N802
        return self._table


def _load_boto3():
    try:
        return importlib.import_module("boto3")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "boto3 is required for DynamoDB-backed control-plane storage. "
            "The installed boto3/botocore environment could not be imported."
        ) from exc

