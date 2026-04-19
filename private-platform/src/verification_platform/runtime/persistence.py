from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from verification.platform import (
    load_platform_persistence_config,
    resolve_nonprofit_postgres_sqlalchemy_url,
    resolve_postgres_sqlalchemy_url,
)
from verification_platform.customer_accounts import (
    AuditLogRepository,
    ApiKeyRepository,
    FeatureFlagRepository,
    InvitationRepository,
    MembershipRepository,
    OrganizationRepository,
    PlanRepository,
    SqlAlchemyApiKeyRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyFeatureFlagRepository,
    SqlAlchemyInvitationRepository,
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyUsageRepository,
    SqlAlchemyUserRepository,
    SubscriptionRepository,
    UsageRepository,
    UserRepository,
    build_customer_accounts_session_factory,
)
from verification_platform.nonprofits import (
    PostgresNonprofitQueryClient,
    SqlAlchemyNonprofitRepository,
    build_nonprofit_session_factory,
)


@dataclass(frozen=True)
class CustomerAccountsPostgresRepositories:
    users: SqlAlchemyUserRepository
    organizations: SqlAlchemyOrganizationRepository
    memberships: SqlAlchemyMembershipRepository
    invitations: SqlAlchemyInvitationRepository
    plans: SqlAlchemyPlanRepository
    subscriptions: SqlAlchemySubscriptionRepository
    api_keys: SqlAlchemyApiKeyRepository
    usage: SqlAlchemyUsageRepository
    flags: SqlAlchemyFeatureFlagRepository
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
    if (
        persistence_config.nonprofit_store_backend != "postgres"
        and persistence_config.nonprofit_query_backend != "postgres"
    ):
        return None
    resolved_url = sqlalchemy_url or resolve_nonprofit_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    session_factory = build_nonprofit_session_factory(resolved_url)
    return SqlAlchemyNonprofitRepository(session_factory)


def build_nonprofit_query_client(
    *,
    athena_client: Any,
    env: Mapping[str, str] | None = None,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> Any:
    source = env or os.environ
    persistence_config = load_platform_persistence_config(source)
    if persistence_config.nonprofit_query_backend != "postgres":
        return athena_client
    repository = build_nonprofit_postgres_repository(
        source,
        sqlalchemy_url=sqlalchemy_url,
        secrets_client=secrets_client,
    )
    if repository is None:
        raise ValueError("PostgreSQL nonprofit query backend was selected but the PostgreSQL repository could not be built")
    return PostgresNonprofitQueryClient(repository=repository, delegate_client=athena_client)


def build_customer_accounts_postgres_repositories(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> CustomerAccountsPostgresRepositories:
    source = env or os.environ
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    session_factory = build_customer_accounts_session_factory(resolved_url)
    return CustomerAccountsPostgresRepositories(
        users=SqlAlchemyUserRepository(session_factory),
        organizations=SqlAlchemyOrganizationRepository(session_factory),
        memberships=SqlAlchemyMembershipRepository(session_factory),
        invitations=SqlAlchemyInvitationRepository(session_factory),
        plans=SqlAlchemyPlanRepository(session_factory),
        subscriptions=SqlAlchemySubscriptionRepository(session_factory),
        api_keys=SqlAlchemyApiKeyRepository(session_factory),
        usage=SqlAlchemyUsageRepository(session_factory),
        flags=SqlAlchemyFeatureFlagRepository(session_factory),
        audits=SqlAlchemyAuditLogRepository(session_factory),
    )


def build_customer_accounts_repositories(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    secrets_client: Any | None = None,
) -> CustomerAccountsRepositories:
    source = env or os.environ
    postgres_bundle = build_customer_accounts_postgres_repositories(
        source,
        sqlalchemy_url=sqlalchemy_url,
        secrets_client=secrets_client,
    )
    return CustomerAccountsRepositories(
        users=postgres_bundle.users,
        organizations=postgres_bundle.organizations,
        memberships=postgres_bundle.memberships,
        invitations=postgres_bundle.invitations,
        plans=postgres_bundle.plans,
        subscriptions=postgres_bundle.subscriptions,
        api_keys=postgres_bundle.api_keys,
        usage=postgres_bundle.usage,
        flags=postgres_bundle.flags,
        audits=postgres_bundle.audits,
        identity_backend="postgres",
    )

