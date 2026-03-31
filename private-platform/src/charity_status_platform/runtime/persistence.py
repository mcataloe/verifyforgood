from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from charity_status.platform import load_platform_persistence_config, resolve_postgres_sqlalchemy_url
from charity_status_platform.customer_accounts import (
    AuditLogRepository,
    ApiKeyRepository,
    DynamoApiKeyRepository,
    DynamoAuditLogRepository,
    DynamoFeatureFlagRepository,
    DynamoInvitationRepository,
    DynamoMembershipRepository,
    DynamoOrganizationRepository,
    DynamoPlanRepository,
    DynamoSubscriptionRepository,
    DynamoUsageRepository,
    DynamoUserRepository,
    FeatureFlagRepository,
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    PlanRepository,
    SqlAlchemyApiKeyRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyUserRepository,
    SubscriptionRepository,
    UsageRepository,
    UserRepository,
    build_customer_accounts_session_factory,
)
from charity_status_platform.nonprofits import SqlAlchemyNonprofitRepository


@dataclass(frozen=True)
class CustomerAccountsPostgresRepositories:
    users: SqlAlchemyUserRepository
    organizations: SqlAlchemyOrganizationRepository
    memberships: SqlAlchemyMembershipRepository
    plans: SqlAlchemyPlanRepository
    subscriptions: SqlAlchemySubscriptionRepository
    api_keys: SqlAlchemyApiKeyRepository
    audits: SqlAlchemyAuditLogRepository


@dataclass(frozen=True)
class CustomerAccountsRepositories:
    users: UserRepository
    organizations: OrganizationRepository
    memberships: MembershipRepository
    invitations: InvitationRepository
    plans: PlanRepository
    subscriptions: SubscriptionRepository
    api_keys: ApiKeyRepository
    usage: UsageRepository
    flags: FeatureFlagRepository
    audits: AuditLogRepository
    identity_backend: str


def build_nonprofit_postgres_repository(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> SqlAlchemyNonprofitRepository | None:
    source = env or os.environ
    persistence_config = load_platform_persistence_config(source)
    if persistence_config.nonprofit_store_backend != "postgres":
        return None
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    session_factory = build_customer_accounts_session_factory(resolved_url)
    return SqlAlchemyNonprofitRepository(session_factory)


def build_customer_accounts_postgres_repositories(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> CustomerAccountsPostgresRepositories | None:
    source = env or os.environ
    persistence_config = load_platform_persistence_config(source)
    if persistence_config.identity_store_backend != "postgres":
        return None
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    session_factory = build_customer_accounts_session_factory(resolved_url)
    return CustomerAccountsPostgresRepositories(
        users=SqlAlchemyUserRepository(session_factory),
        organizations=SqlAlchemyOrganizationRepository(session_factory),
        memberships=SqlAlchemyMembershipRepository(session_factory),
        plans=SqlAlchemyPlanRepository(session_factory),
        subscriptions=SqlAlchemySubscriptionRepository(session_factory),
        api_keys=SqlAlchemyApiKeyRepository(session_factory),
        audits=SqlAlchemyAuditLogRepository(session_factory),
    )


def build_customer_accounts_repositories(
    env: Mapping[str, str] | None = None,
    *,
    identity_table_name: str,
    sqlalchemy_url: str | None = None,
    dynamodb_resource: Any | None = None,
    secrets_client: Any | None = None,
) -> CustomerAccountsRepositories:
    source = env or os.environ
    persistence_config = load_platform_persistence_config(source)
    invitations = DynamoInvitationRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource)
    usage = DynamoUsageRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource)
    flags = DynamoFeatureFlagRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource)

    if persistence_config.identity_store_backend == "postgres":
        postgres_bundle = build_customer_accounts_postgres_repositories(
            source,
            sqlalchemy_url=sqlalchemy_url,
            secrets_client=secrets_client,
        )
        if postgres_bundle is None:
            raise ValueError("PostgreSQL identity backend was selected but PostgreSQL repositories could not be built")
        return CustomerAccountsRepositories(
            users=postgres_bundle.users,
            organizations=postgres_bundle.organizations,
            memberships=postgres_bundle.memberships,
            invitations=invitations,
            plans=postgres_bundle.plans,
            subscriptions=postgres_bundle.subscriptions,
            api_keys=postgres_bundle.api_keys,
            usage=usage,
            flags=flags,
            audits=postgres_bundle.audits,
            identity_backend="postgres",
        )

    return CustomerAccountsRepositories(
        users=DynamoUserRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        organizations=DynamoOrganizationRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        memberships=DynamoMembershipRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        invitations=invitations,
        plans=DynamoPlanRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        subscriptions=DynamoSubscriptionRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        api_keys=DynamoApiKeyRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        usage=usage,
        flags=flags,
        audits=DynamoAuditLogRepository(table_name=identity_table_name, dynamodb_resource=dynamodb_resource),
        identity_backend="dynamodb",
    )
