from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import boto3
from sqlalchemy import select

from verification.platform import resolve_postgres_sqlalchemy_url
from verification_platform.customer_accounts.audit_logging import AuditRecord
from verification_platform.customer_accounts.audit_repository import _audit_from_item
from verification_platform.customer_accounts.dynamodb_identity import (
    _api_key_from_item,
    _membership_from_item,
    _organization_from_item,
    _plan_from_item,
    _subscription_from_item,
    _user_from_item,
)
from verification_platform.customer_accounts.sqlalchemy_db import (
    CustomerAccountsBase,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
    customer_accounts_session_scope,
)
from verification_platform.customer_accounts.sqlalchemy_models import (
    OrganizationApiKeyModel,
    OrganizationAuditLogModel,
    OrganizationMembershipModel,
    OrganizationModel,
    OrganizationSubscriptionModel,
    PlanModel,
    UserModel,
)


@dataclass(frozen=True)
class CustomerAccountsBackfillStats:
    users: int = 0
    organizations: int = 0
    memberships: int = 0
    plans: int = 0
    subscriptions: int = 0
    api_keys: int = 0
    audit_logs: int = 0

    @property
    def total(self) -> int:
        return self.users + self.organizations + self.memberships + self.plans + self.subscriptions + self.api_keys + self.audit_logs


def backfill_customer_accounts_from_dynamodb(
    env: Mapping[str, str] | None = None,
    *,
    identity_table_name: str,
    sqlalchemy_url: str | None = None,
    dynamodb_resource: Any | None = None,
    table: Any | None = None,
    secrets_client: Any | None = None,
) -> CustomerAccountsBackfillStats:
    source = env or os.environ
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    engine = build_customer_accounts_engine(resolved_url)
    CustomerAccountsBase.metadata.create_all(engine)
    session_factory = build_customer_accounts_session_factory(engine)
    identity_table = table or (dynamodb_resource or boto3.resource("dynamodb")).Table(identity_table_name)
    items = list(_scan_identity_items(identity_table))

    stats = CustomerAccountsBackfillStats(
        users=sum(1 for item in items if item.get("type") == "USER"),
        organizations=sum(1 for item in items if item.get("type") == "ORG"),
        memberships=sum(1 for item in items if item.get("type") == "MEMBERSHIP"),
        plans=sum(1 for item in items if item.get("type") == "PLAN"),
        subscriptions=sum(1 for item in items if item.get("type") == "SUBSCRIPTION"),
        api_keys=sum(1 for item in items if item.get("type") == "API_KEY"),
        audit_logs=sum(1 for item in items if item.get("type") == "AUDIT"),
    )

    user_id_map: dict[str, int] = {}
    organization_id_map: dict[str, int] = {}
    plan_id_map: dict[str, int] = {}

    with customer_accounts_session_scope(session_factory) as session:
        for item in items:
            item_type = str(item.get("type") or "")
            if item_type == "USER":
                record = _user_from_item(item)
                model = session.scalar(select(UserModel).where(UserModel.normalized_email == record.normalized_email).limit(1))
                if model is None:
                    model = UserModel(
                        email=record.email,
                        normalized_email=record.normalized_email,
                        full_name=record.full_name,
                        created_at=_parse_timestamp(record.created_at),
                        updated_at=_parse_timestamp(record.updated_at),
                        password_hash=record.password_hash,
                        identity_provider_type=record.identity_provider_type.value,
                        external_subject_id=record.external_subject_id,
                    )
                    session.add(model)
                    session.flush()
                user_id_map[str(record.user_id)] = int(model.user_id)
            elif item_type == "ORG":
                record = _organization_from_item(item)
                model = session.scalar(select(OrganizationModel).where(OrganizationModel.slug == record.slug).limit(1))
                if model is None:
                    model = OrganizationModel(
                        name=record.name,
                        slug=record.slug,
                        created_at=_parse_timestamp(record.created_at),
                        updated_at=_parse_timestamp(record.updated_at),
                        contact_email=record.contact_email,
                        deleted_at=_parse_timestamp(record.deleted_at) if record.deleted_at else None,
                        deleted_by_user_id=None,
                    )
                    session.add(model)
                    session.flush()
                organization_id_map[str(record.organization_id)] = int(model.organization_id)
            elif item_type == "PLAN":
                record = _plan_from_item(item)
                plan_code = record.plan_code or str(record.plan_id or "")
                model = session.scalar(select(PlanModel).where(PlanModel.plan_code == plan_code).limit(1))
                if model is None:
                    model = PlanModel(
                        plan_name=record.plan_name,
                        plan_code=plan_code,
                        monthly_price=record.monthly_price,
                        feature_flags=list(record.feature_flags),
                        request_limit=record.request_limit,
                        description=record.description,
                    )
                    session.add(model)
                    session.flush()
                plan_id_map[str(record.plan_id)] = int(model.plan_id)
                plan_id_map[plan_code] = int(model.plan_id)

        for item in items:
            item_type = str(item.get("type") or "")
            if item_type == "MEMBERSHIP":
                record = _membership_from_item(item)
                organization_id = organization_id_map.get(str(record.organization_id))
                user_id = user_id_map.get(str(record.user_id))
                if organization_id is None or user_id is None:
                    continue
                model = session.scalar(
                    select(OrganizationMembershipModel)
                    .where(
                        OrganizationMembershipModel.organization_id == organization_id,
                        OrganizationMembershipModel.user_id == user_id,
                    )
                    .limit(1)
                )
                if model is None:
                    session.add(
                        OrganizationMembershipModel(
                            organization_id=organization_id,
                            user_id=user_id,
                            role=record.role.value,
                            status=record.status.value,
                            created_at=_parse_timestamp(record.created_at),
                            updated_at=_parse_timestamp(record.updated_at),
                        )
                    )
                else:
                    model.role = record.role.value
                    model.status = record.status.value
                    model.updated_at = _parse_timestamp(record.updated_at)
            elif item_type == "SUBSCRIPTION":
                record = _subscription_from_item(item)
                organization_id = organization_id_map.get(str(record.organization_id))
                plan_id = plan_id_map.get(str(record.plan_id))
                if organization_id is None or plan_id is None:
                    continue
                model = session.scalar(
                    select(OrganizationSubscriptionModel)
                    .where(OrganizationSubscriptionModel.organization_id == organization_id)
                    .limit(1)
                )
                if model is None:
                    session.add(
                        OrganizationSubscriptionModel(
                            organization_id=organization_id,
                            plan_id=plan_id,
                            status=record.status.value,
                            billing_cycle_start=_parse_timestamp(record.billing_cycle_start),
                            billing_cycle_end=_parse_timestamp(record.billing_cycle_end),
                            created_at=_parse_timestamp(record.created_at),
                            pending_plan_id=plan_id_map.get(str(record.pending_plan_id)) if record.pending_plan_id else None,
                            pending_plan_effective_at=_parse_timestamp(record.pending_plan_effective_at) if record.pending_plan_effective_at else None,
                            cancel_at_period_end=bool(record.cancel_at_period_end),
                            updated_at=_parse_timestamp(record.updated_at) if record.updated_at else None,
                            grace_period_ends_at=_parse_timestamp(record.grace_period_ends_at) if record.grace_period_ends_at else None,
                            billing_status=record.billing_status,
                        )
                    )
                else:
                    model.plan_id = plan_id
                    model.status = record.status.value
                    model.billing_cycle_start = _parse_timestamp(record.billing_cycle_start)
                    model.billing_cycle_end = _parse_timestamp(record.billing_cycle_end)
                    model.created_at = _parse_timestamp(record.created_at)
                    model.pending_plan_id = plan_id_map.get(str(record.pending_plan_id)) if record.pending_plan_id else None
                    model.pending_plan_effective_at = _parse_timestamp(record.pending_plan_effective_at) if record.pending_plan_effective_at else None
                    model.cancel_at_period_end = bool(record.cancel_at_period_end)
                    model.updated_at = _parse_timestamp(record.updated_at) if record.updated_at else None
                    model.grace_period_ends_at = _parse_timestamp(record.grace_period_ends_at) if record.grace_period_ends_at else None
                    model.billing_status = record.billing_status
            elif item_type == "API_KEY":
                record = _api_key_from_item(item)
                organization_id = organization_id_map.get(str(record.organization_id))
                created_by_user_id = user_id_map.get(str(record.created_by_user_id))
                if organization_id is None or created_by_user_id is None:
                    continue
                model = session.scalar(
                    select(OrganizationApiKeyModel)
                    .where(
                        OrganizationApiKeyModel.organization_id == organization_id,
                        OrganizationApiKeyModel.hashed_key_value == record.hashed_key_value,
                    )
                    .limit(1)
                )
                if model is None:
                    session.add(
                        OrganizationApiKeyModel(
                            organization_id=organization_id,
                            hashed_key_value=record.hashed_key_value,
                            display_name=record.display_name,
                            created_at=_parse_timestamp(record.created_at),
                            created_by_user_id=created_by_user_id,
                            status=record.status.value,
                            last_used_at=_parse_timestamp(record.last_used_at) if record.last_used_at else None,
                        )
                    )
                else:
                    model.display_name = record.display_name
                    model.status = record.status.value
                    model.last_used_at = _parse_timestamp(record.last_used_at) if record.last_used_at else None
            elif item_type == "AUDIT":
                record = _audit_from_item(item)
                organization_id = organization_id_map.get(str(record.organization_id)) if record.organization_id else None
                actor_user_id = user_id_map.get(str(record.actor_user_id)) if record.actor_user_id else None
                target_user_id = user_id_map.get(str(record.target_user_id)) if record.target_user_id else None
                model = session.scalar(
                    select(OrganizationAuditLogModel)
                    .where(
                        OrganizationAuditLogModel.organization_id == organization_id,
                        OrganizationAuditLogModel.event_type == record.event_type.value,
                        OrganizationAuditLogModel.timestamp == _parse_timestamp(record.timestamp),
                    )
                    .limit(1)
                )
                if model is None:
                    session.add(
                        OrganizationAuditLogModel(
                            event_type=record.event_type.value,
                            actor_user_id=actor_user_id,
                            organization_id=organization_id,
                            target_user_id=target_user_id,
                            timestamp=_parse_timestamp(record.timestamp),
                            metadata_json=dict(record.metadata),
                        )
                    )
                else:
                    model.actor_user_id = actor_user_id
                    model.target_user_id = target_user_id
                    model.metadata_json = dict(record.metadata)

        session.flush()

    return stats


def _scan_identity_items(table: Any) -> Iterable[dict[str, Any]]:
    if hasattr(table, "scan"):
        scan_kwargs: dict[str, Any] = {}
        while True:
            response = table.scan(**scan_kwargs)
            for item in response.get("Items") or []:
                yield dict(item)
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
        return

    items = getattr(table, "_items", None)
    if isinstance(items, dict):
        for item in items.values():
            yield dict(item)
        return

    raise ValueError("Identity table does not support scan and does not expose fake-table items")


def _parse_timestamp(value: str | None) -> datetime:
    normalized = str(value or "").strip()
    if not normalized:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill customer-account identity records from DynamoDB into PostgreSQL.")
    parser.add_argument("--identity-table-name", default=os.environ.get("IDENTITY_TABLE_NAME", "identity"))
    parser.add_argument("--sqlalchemy-url", default=os.environ.get("PLATFORM_POSTGRES_URL", ""))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    stats = backfill_customer_accounts_from_dynamodb(
        os.environ,
        identity_table_name=str(args.identity_table_name or "identity"),
        sqlalchemy_url=(str(args.sqlalchemy_url).strip() or None),
    )
    payload = asdict(stats)
    payload["total"] = stats.total
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

