# Portal Identity, Organization Onboarding, and Membership Status

## Status

Current implementation snapshot (bounded):

- customer-account persistence uses PostgreSQL-backed relational tables
- customer-account tables use generated `BIGINT` primary keys across users, organizations, memberships, plans, subscriptions, API keys, and audit logs
- authenticated portal sessions can resolve active organization membership/context for the current user

This file is an implementation-status snapshot only. It does not own identity architecture, product policy, or roadmap priority; current merged code, tests, migrations, and the relevant `INIT-004` records govern implemented behavior.

## Next Phase

Reconcile any remaining identity, membership, organization-context, and authorization work under `INIT-004` against current code and tests before implementation.

## Scope

- Identity domain modeling
- Organization onboarding and membership context
- PostgreSQL customer-account persistence
- Service-layer contracts
- Portal organization-context behavior

## Deployment Notes

Historical DynamoDB identity-schema and GSI guidance previously recorded here is stale for the current PostgreSQL customer-account baseline and has been removed from this status snapshot. Check current infrastructure, migrations, and runtime configuration before making persistence or deployment changes.
