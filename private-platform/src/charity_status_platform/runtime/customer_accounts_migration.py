from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

import boto3
from sqlalchemy import select

from charity_status.platform import resolve_postgres_sqlalchemy_url
from charity_status_platform.customer_accounts import (
    OrganizationApiKeyModel,
    OrganizationAuditLogModel,
    OrganizationMembershipModel,
    OrganizationModel,
    OrganizationSubscriptionModel,
    PlanModel,
    UserModel,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
    customer_accounts_session_scope,
)

from .customer_accounts_backfill import CustomerAccountsBackfillStats, _scan_identity_items, backfill_customer_accounts_from_dynamodb
from .migration_validation import MigrationEntityValidation, build_entity_validation


@dataclass(frozen=True)
class CustomerAccountsMigrationReport:
    dry_run: bool
    scanned_items: int
    source_counts: CustomerAccountsBackfillStats
    target_counts: CustomerAccountsBackfillStats
    unsupported_items: int = 0
    invalid_items: int = 0
    validation: dict[str, MigrationEntityValidation] = field(default_factory=dict)
    sample_invalid_items: tuple[dict[str, str], ...] = ()


def run_customer_accounts_migration(
    env: Mapping[str, str] | None = None,
    *,
    identity_table_name: str,
    sqlalchemy_url: str | None = None,
    dynamodb_resource: Any | None = None,
    table: Any | None = None,
    dry_run: bool = False,
    sample_limit: int = 20,
    secrets_client: Any | None = None,
) -> CustomerAccountsMigrationReport:
    source = env or os.environ
    identity_table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(identity_table_name)
    items = list(_scan_identity_items(identity_table))
    expected_keys, invalid_items, unsupported_items = _collect_expected_identity_keys(items, sample_limit=sample_limit)
    source_counts = _counts_from_expected_keys(expected_keys)

    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    engine = build_customer_accounts_engine(resolved_url)
    UserModel.metadata.create_all(engine)
    if not dry_run:
        backfill_customer_accounts_from_dynamodb(
            source,
            identity_table_name=identity_table_name,
            sqlalchemy_url=resolved_url,
            dynamodb_resource=dynamodb_resource,
            table=identity_table,
            secrets_client=secrets_client,
        )

    target_counts, validation = _validate_customer_accounts_targets(
        sqlalchemy_url=resolved_url,
        expected_keys=expected_keys,
        sample_limit=sample_limit,
    )
    return CustomerAccountsMigrationReport(
        dry_run=dry_run,
        scanned_items=len(items),
        source_counts=source_counts,
        target_counts=target_counts,
        unsupported_items=unsupported_items,
        invalid_items=len(invalid_items),
        validation=validation,
        sample_invalid_items=tuple(invalid_items[:sample_limit]),
    )


def _collect_expected_identity_keys(
    items: list[dict[str, Any]],
    *,
    sample_limit: int,
) -> tuple[dict[str, set[str]], list[dict[str, str]], int]:
    expected_keys: dict[str, set[str]] = {
        "users": set(),
        "organizations": set(),
        "memberships": set(),
        "plans": set(),
        "subscriptions": set(),
        "api_keys": set(),
        "audit_logs": set(),
    }
    invalid_items: list[dict[str, str]] = []
    unsupported_items = 0
    type_to_bucket = {
        "USER": "users",
        "ORG": "organizations",
        "MEMBERSHIP": "memberships",
        "PLAN": "plans",
        "SUBSCRIPTION": "subscriptions",
        "API_KEY": "api_keys",
        "AUDIT": "audit_logs",
    }
    for item in items:
        item_type = str(item.get("type") or "").strip().upper()
        bucket = type_to_bucket.get(item_type)
        if bucket is None:
            unsupported_items += 1
            continue
        key = _identity_key_for_item(item_type, item)
        if key is None:
            invalid_items.append(
                {
                    "type": item_type,
                    "pk": str(item.get("pk") or ""),
                    "sk": str(item.get("sk") or ""),
                    "error": "missing primary identity key fields",
                }
            )
            continue
        expected_keys[bucket].add(key)
    return expected_keys, invalid_items[:sample_limit], unsupported_items


def _identity_key_for_item(item_type: str, item: dict[str, Any]) -> str | None:
    if item_type == "USER":
        return _text(item.get("user_id"))
    if item_type == "ORG":
        return _text(item.get("organization_id"))
    if item_type == "MEMBERSHIP":
        organization_id = _text(item.get("organization_id"))
        user_id = _text(item.get("user_id"))
        return None if not organization_id or not user_id else f"{organization_id}|{user_id}"
    if item_type == "PLAN":
        return _text(item.get("plan_id"))
    if item_type == "SUBSCRIPTION":
        return _text(item.get("subscription_id"))
    if item_type == "API_KEY":
        return _text(item.get("key_id"))
    if item_type == "AUDIT":
        return _text(item.get("audit_id"))
    return None


def _counts_from_expected_keys(expected_keys: dict[str, set[str]]) -> CustomerAccountsBackfillStats:
    return CustomerAccountsBackfillStats(
        users=len(expected_keys["users"]),
        organizations=len(expected_keys["organizations"]),
        memberships=len(expected_keys["memberships"]),
        plans=len(expected_keys["plans"]),
        subscriptions=len(expected_keys["subscriptions"]),
        api_keys=len(expected_keys["api_keys"]),
        audit_logs=len(expected_keys["audit_logs"]),
    )


def _validate_customer_accounts_targets(
    *,
    sqlalchemy_url: str,
    expected_keys: dict[str, set[str]],
    sample_limit: int,
) -> tuple[CustomerAccountsBackfillStats, dict[str, MigrationEntityValidation]]:
    engine = build_customer_accounts_engine(sqlalchemy_url)
    session_factory = build_customer_accounts_session_factory(engine)
    with customer_accounts_session_scope(session_factory) as session:
        present_users = set(session.scalars(select(UserModel.user_id).where(UserModel.user_id.in_(expected_keys["users"]))).all()) if expected_keys["users"] else set()
        present_organizations = set(
            session.scalars(select(OrganizationModel.organization_id).where(OrganizationModel.organization_id.in_(expected_keys["organizations"]))).all()
        ) if expected_keys["organizations"] else set()
        present_plans = set(session.scalars(select(PlanModel.plan_id).where(PlanModel.plan_id.in_(expected_keys["plans"]))).all()) if expected_keys["plans"] else set()
        present_subscriptions = set(
            session.scalars(select(OrganizationSubscriptionModel.subscription_id).where(OrganizationSubscriptionModel.subscription_id.in_(expected_keys["subscriptions"]))).all()
        ) if expected_keys["subscriptions"] else set()
        present_api_keys = set(
            session.scalars(select(OrganizationApiKeyModel.key_id).where(OrganizationApiKeyModel.key_id.in_(expected_keys["api_keys"]))).all()
        ) if expected_keys["api_keys"] else set()
        present_audits = set(
            session.scalars(select(OrganizationAuditLogModel.audit_id).where(OrganizationAuditLogModel.audit_id.in_(expected_keys["audit_logs"]))).all()
        ) if expected_keys["audit_logs"] else set()
        present_memberships = set()
        if expected_keys["memberships"]:
            rows = session.execute(
                select(OrganizationMembershipModel.organization_id, OrganizationMembershipModel.user_id).where(
                    OrganizationMembershipModel.organization_id.in_({key.split("|", 1)[0] for key in expected_keys["memberships"]}),
                    OrganizationMembershipModel.user_id.in_({key.split("|", 1)[1] for key in expected_keys["memberships"]}),
                )
            ).all()
            present_memberships = {f"{organization_id}|{user_id}" for organization_id, user_id in rows}

    validation = {
        "users": build_entity_validation(expected_keys=expected_keys["users"], present_keys=present_users, sample_limit=sample_limit),
        "organizations": build_entity_validation(expected_keys=expected_keys["organizations"], present_keys=present_organizations, sample_limit=sample_limit),
        "memberships": build_entity_validation(expected_keys=expected_keys["memberships"], present_keys=present_memberships, sample_limit=sample_limit),
        "plans": build_entity_validation(expected_keys=expected_keys["plans"], present_keys=present_plans, sample_limit=sample_limit),
        "subscriptions": build_entity_validation(expected_keys=expected_keys["subscriptions"], present_keys=present_subscriptions, sample_limit=sample_limit),
        "api_keys": build_entity_validation(expected_keys=expected_keys["api_keys"], present_keys=present_api_keys, sample_limit=sample_limit),
        "audit_logs": build_entity_validation(expected_keys=expected_keys["audit_logs"], present_keys=present_audits, sample_limit=sample_limit),
    }
    target_counts = CustomerAccountsBackfillStats(
        users=validation["users"].present,
        organizations=validation["organizations"].present,
        memberships=validation["memberships"].present,
        plans=validation["plans"].present,
        subscriptions=validation["subscriptions"].present,
        api_keys=validation["api_keys"].present,
        audit_logs=validation["audit_logs"].present,
    )
    return target_counts, validation


def _text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run customer-account PostgreSQL migration with validation reporting.")
    parser.add_argument("--identity-table-name", default=os.environ.get("IDENTITY_TABLE_NAME", "identity"))
    parser.add_argument("--sqlalchemy-url", default=os.environ.get("PLATFORM_POSTGRES_URL", ""))
    parser.add_argument("--dry-run", action="store_true", help="Skip writes and only validate current PostgreSQL contents against DynamoDB.")
    parser.add_argument("--sample-limit", type=int, default=20, help="Maximum number of missing/invalid keys to include in the JSON report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_customer_accounts_migration(
        os.environ,
        identity_table_name=str(args.identity_table_name or "identity"),
        sqlalchemy_url=(str(args.sqlalchemy_url).strip() or None),
        dry_run=bool(args.dry_run),
        sample_limit=max(1, int(args.sample_limit)),
    )
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
