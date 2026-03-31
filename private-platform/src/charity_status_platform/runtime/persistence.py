from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from charity_status.platform import load_platform_persistence_config, resolve_postgres_sqlalchemy_url
from charity_status_platform.customer_accounts import (
    SqlAlchemyApiKeyRepository,
    SqlAlchemyAuditLogRepository,
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyUserRepository,
    build_customer_accounts_session_factory,
)


@dataclass(frozen=True)
class CustomerAccountsPostgresRepositories:
    users: SqlAlchemyUserRepository
    organizations: SqlAlchemyOrganizationRepository
    memberships: SqlAlchemyMembershipRepository
    plans: SqlAlchemyPlanRepository
    subscriptions: SqlAlchemySubscriptionRepository
    api_keys: SqlAlchemyApiKeyRepository
    audits: SqlAlchemyAuditLogRepository


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
