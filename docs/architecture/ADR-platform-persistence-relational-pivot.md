# Platform Persistence Relational Pivot

## Status

accepted

## Decision

Adopt PostgreSQL on Amazon RDS as the primary persistence target for the
platform's relational application domains and migrate incrementally from the
current DynamoDB-heavy model instead of performing a single cutover.

The current environment target is Amazon RDS for PostgreSQL on
`db.t4g.micro`. The codebase should keep persistence selection modular so the
runtime can evolve to larger instance classes or managed PostgreSQL variants
later without changing service contracts.

## Context

The repository currently uses DynamoDB for several distinct platform
persistence concerns:

- `identity` table
  - portal users, organizations, memberships, invitations, org API keys,
    plans, subscriptions, usage, feature flags, and audit events
- `organization_settings` table
  - organization integration and billing settings
- `control_plane` table
  - accounts, billing customers, subscriptions, billing events, trial history,
    control-plane API keys, OAuth clients, and usage
- `profiles` table
  - materialized nonprofit-serving cache

The portal identity and control-plane domains are strongly relational:

- membership joins connect users and organizations
- organization settings and subscriptions are naturally one-to-one or one-to-many
- billing and audit records benefit from relational constraints and indexed joins
- multi-organization access, SSO, support tooling, and reporting all become
  simpler with normalized records

The repo already has useful abstraction seams:

- repository protocols in
  `private-platform/src/verification_platform/customer_accounts/identity_repositories.py`
- `ControlPlaneStore` protocol in
  `infrastructure/verification/control_plane/service.py`
- service layers that are mostly storage-agnostic above those protocols

## Decision Details

### Domains to move first

Move relational platform/application data to PostgreSQL in stages:

1. portal identity and customer-account data
   - users
   - organizations
   - memberships
   - invitations
2. organization settings, org audit, feature flags, org API keys, org usage,
   and org subscriptions
3. control-plane billing/account data
   - accounts
   - billing customers
   - billing events
   - trial history
   - control-plane API keys
   - OAuth clients
   - account usage

### Domains staying separate for now

Do not include these in the initial nonprofit runtime cutover:

- nonprofit/source/search/filing datasets in Athena/S3
- Form 990 ingest storage and Glue catalog structures
- `profiles` serving cache unless a later serving redesign justifies moving it

An additive nonprofit relational schema may still be introduced before runtime
cutover so canonical nonprofit identity, filings, source provenance, and
compliance snapshots have a stable PostgreSQL target model.

### Migration shape

Use additive migration rather than replacement:

- keep existing service and route contracts stable
- add PostgreSQL adapters behind existing repository/store protocols
- add runtime store-selection/bootstrap seams by domain
- backfill PostgreSQL before switching critical reads
- use per-domain cutovers with rollback flags
- use temporary dual-write only where necessary

## Consequences

- The next implementation phases should focus on bootstrap/config seams and
  PostgreSQL repository parity rather than rewriting business logic.
- The first runtime cutover phase should move customer-account identity data
  to PostgreSQL while leaving invitations, usage, feature flags, and
  organization settings on DynamoDB as a narrow compatibility layer.
- Test strategy should shift from Dynamo-only fake-table tests toward
  backend-agnostic repository contract coverage plus targeted adapter tests.
- Infrastructure must add PostgreSQL networking, secrets, and runtime
  configuration while keeping existing DynamoDB resources available during the
  migration.

