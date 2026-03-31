# Identity Datastore Selection

## Status

superseded by staged PostgreSQL pivot

## Decision

Use DynamoDB only as the provisional early-development datastore for portal
identity and customer-account persistence, and pivot the platform's relational
application domains toward PostgreSQL as the primary long-term datastore.

## Context

- Cost minimization is a priority during the early stage.
- The platform should remain serverless initially where practical.
- The identity domain is relational in nature and has now grown to include:
  - users
  - organizations
  - memberships
  - invitations
  - subscriptions
  - usage
  - audit events
- The control-plane and organization-settings domains also contain relational
  records and are currently persisted through DynamoDB adapters.
- Future portal billing, SSO, reporting, multi-organization management, and
  audit requirements make relational constraints and joins a better fit than
  continuing to expand the current single-table design.

## Consequences

- A repository abstraction layer is required between domain services and persistence.
- Business logic should not couple directly to DynamoDB item shapes or access patterns.
- The conceptual domain model should remain normalized even if the physical storage model is denormalized.
- Follow-on phases should preserve the current repository and service contracts
  while adding PostgreSQL-backed adapters and runtime store selection.
- DynamoDB should remain available during the migration as a compatibility
  backend and rollback option until each migrated domain has completed
  backfill, parity validation, and cutover.
- Athena/S3-backed nonprofit, filing, and enrichment datasets remain out of
  scope for this datastore decision and are evaluated separately.
