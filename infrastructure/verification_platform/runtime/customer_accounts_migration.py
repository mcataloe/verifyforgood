from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

import boto3
from sqlalchemy import select

from verification.platform import resolve_postgres_sqlalchemy_url
from verification_platform.customer_accounts import (
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
    organization_slug_by_id = {
        _text(item.get("organization_id")): _text(item.get("slug"))
        for item in items
        if str(item.get("type") or "").strip().upper() == "ORG" and _text(item.get("organization_id")) and _text(item.get("slug"))
    }
    user_email_by_id = {
        _text(item.get("user_id")): (_text(item.get("normalized_email")) or _text(item.get("email")))
        for item in items
        if str(item.get("type") or "").strip().upper() == "USER" and _text(item.get("user_id")) and (_text(item.get("normalized_email")) or _text(item.get("email")))
    }
    for item in items:
        item_type = str(item.get("type") or "").strip().upper()
        bucket = type_to_bucket.get(item_type)
        if bucket is None:
            unsupported_items += 1
            continue
        key = _identity_key_for_item(
            item_type,
            item,
            organization_slug_by_id=organization_slug_by_id,
            user_email_by_id=user_email_by_id,
        )
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


def _identity_key_for_item(
    item_type: str,
    item: dict[str, Any],
    *,
    organization_slug_by_id: dict[str | None, str | None],
    user_email_by_id: dict[str | None, str | None],
) -> str | None:
    if item_type == "USER":
        return _text(item.get("normalized_email")) or _text(item.get("email"))
    if item_type == "ORG":
        return _text(item.get("slug"))
    if item_type == "MEMBERSHIP":
        organization_slug = organization_slug_by_id.get(_text(item.get("organization_id")))
        user_email = user_email_by_id.get(_text(item.get("user_id")))
        return None if not organization_slug or not user_email else f"{organization_slug}|{user_email}"
    if item_type == "PLAN":
        return _text(item.get("plan_code")) or _text(item.get("plan_id"))
    if item_type == "SUBSCRIPTION":
        return organization_slug_by_id.get(_text(item.get("organization_id")))
    if item_type == "API_KEY":
        organization_id = organization_slug_by_id.get(_text(item.get("organization_id")))
        key_hash = _text(item.get("hashed_key_value"))
        return None if not organization_id or not key_hash else f"{organization_id}|{key_hash}"
    if item_type == "AUDIT":
        event_type = _text(item.get("event_type"))
        organization_id = organization_slug_by_id.get(_text(item.get("organization_id"))) or ""
        timestamp = _text(item.get("timestamp"))
        return None if not event_type or not timestamp else f"{organization_id}|{event_type}|{timestamp}"
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
        present_users = set(session.scalars(select(UserModel.normalized_email)).all()) if expected_keys["users"] else set()
        present_organizations = set(session.scalars(select(OrganizationModel.slug)).all()) if expected_keys["organizations"] else set()
        present_plans = set(session.scalars(select(PlanModel.plan_code)).all()) if expected_keys["plans"] else set()
        present_subscriptions = set(
            session.execute(
                select(OrganizationModel.slug)
                .join(OrganizationSubscriptionModel, OrganizationSubscriptionModel.organization_id == OrganizationModel.organization_id)
            ).scalars().all()
        ) if expected_keys["subscriptions"] else set()
        present_api_keys = set(
            f"{slug}|{hashed_key_value}"
            for slug, hashed_key_value in session.execute(
                select(OrganizationModel.slug, OrganizationApiKeyModel.hashed_key_value)
                .join(OrganizationApiKeyModel, OrganizationApiKeyModel.organization_id == OrganizationModel.organization_id)
            ).all()
        ) if expected_keys["api_keys"] else set()
        present_audits = set(
            f"{slug or ''}|{event_type}|{_format_timestamp(timestamp)}"
            for slug, event_type, timestamp in session.execute(
                select(OrganizationModel.slug, OrganizationAuditLogModel.event_type, OrganizationAuditLogModel.timestamp)
                .select_from(OrganizationAuditLogModel)
                .join(OrganizationModel, OrganizationAuditLogModel.organization_id == OrganizationModel.organization_id, isouter=True)
            ).all()
        ) if expected_keys["audit_logs"] else set()
        present_memberships = set(
            f"{slug}|{normalized_email}"
            for slug, normalized_email in session.execute(
                select(OrganizationModel.slug, UserModel.normalized_email)
                .select_from(OrganizationMembershipModel)
                .join(OrganizationModel, OrganizationMembershipModel.organization_id == OrganizationModel.organization_id)
                .join(UserModel, OrganizationMembershipModel.user_id == UserModel.user_id)
            ).all()
        ) if expected_keys["memberships"] else set()

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


def _format_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        current = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    normalized = str(value or "").strip()
    return normalized.replace("Z", "+00:00")


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

