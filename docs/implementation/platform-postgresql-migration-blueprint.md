# Platform PostgreSQL Migration Blueprint

## Summary

This document is the implementation blueprint for the platform's incremental
move from DynamoDB-heavy persistence toward PostgreSQL-backed relational
storage.

This phase does not remove DynamoDB or change route contracts. It records the
current coupling points, the target relational schema direction, and the
follow-on sequence needed to cut over safely.

## Current DynamoDB Coupling Inventory

### 1. Portal identity and customer accounts

Primary code:

- `private-platform/src/charity_status_platform/customer_accounts/dynamodb_identity.py`
- `private-platform/src/charity_status_platform/customer_accounts/audit_repository.py`

Current stored entity families:

- users
- organizations
- memberships
- invitations
- org API keys
- plans
- subscriptions
- usage buckets
- feature flags
- audit records

Current DynamoDB-specific semantics:

- single-table entity prefixes
- GSIs for:
  - email lookup
  - user membership lookup
  - invitation token lookup
  - organization slug lookup
  - API key lookup
  - plan catalog lookup
- additive usage counter writes
- audit records colocated under organization partitions

Primary downstream services:

- `organization_service.py`
- `membership_service.py`
- `api_key_service.py`
- `subscription_service.py`
- `usage_service.py`
- `feature_flag_service.py`
- `organization_context_service.py`
- `organization_activity_service.py`
- `organization_settings_service.py`
- `organization_support_service.py`
- `identity_access/auth_service.py`
- `infrastructure/lambda_query.py`

### 2. Organization settings

Primary code:

- `infrastructure/charity_status/enrichments/organization_settings_service.py`

Current stored concerns:

- org integration settings
- org billing preferences

This is already abstracted behind a dedicated store protocol and should move as
its own relational slice after the identity core.

### 3. Control-plane and billing data

Primary code:

- `infrastructure/charity_status/control_plane/dynamodb_store.py`
- `infrastructure/charity_status/control_plane/service.py`

Current stored concerns:

- accounts
- subscriptions
- billing customers
- billing events
- trial history
- control-plane API keys
- OAuth clients
- usage

Primary downstream consumers:

- `infrastructure/charity_status/billing/*`
- `infrastructure/lambda_query.py`
- control-plane and billing tests

### 4. Additional DynamoDB runtime dependencies

Infrastructure and runtime are coupled through:

- `infrastructure/main.tf`
- `infrastructure/aws_lambda.tf`
- `infrastructure/aws_iam.tf`
- `infrastructure/lambda_query.py`

Current table/env assumptions:

- `IDENTITY_TABLE_NAME`
- `ORGANIZATION_SETTINGS_TABLE_NAME`
- `CONTROL_PLANE_TABLE_NAME`
- `PROFILE_TABLE_NAME`

### 5. Test suites most affected

Most migration-sensitive tests currently depend on Dynamo-specific fakes or
store selection:

- `tests/test_identity_dynamodb.py`
- `tests/test_portal_auth.py`
- `tests/test_organization_*`
- `tests/test_membership_management.py`
- `tests/test_lambda_query.py`
- `tests/test_control_plane_dynamodb.py`
- billing/control-plane tests that instantiate `DynamoControlPlaneStore`

## Target PostgreSQL-First Relational Model

### Move first

#### Portal identity and customer accounts

- `users`
  - `user_id` primary key
  - unique `normalized_email`
  - provider fields for local password and future SSO
- `organizations`
  - `organization_id` primary key
  - unique slug
  - contact email
  - soft-delete fields
- `organization_memberships`
  - foreign keys to users and organizations
  - unique `(organization_id, user_id)`
  - role and status
- `organization_invitations`
  - unique token
  - email, role, status, invited_by_user_id
- `organization_api_keys`
  - unique key id
  - org foreign key
- `organization_feature_flags`
  - unique `(organization_id, flag_key)`
- `organization_usage_monthly`
  - unique `(organization_id, metric_type, period_month)`
- `organization_audit_events`
  - append-only audit log keyed by organization and timestamp
- `plans`
  - plan catalog
- `organization_subscriptions`
  - org foreign key
  - current and pending subscription fields

#### Organization settings

- `organization_settings`
  - one row per organization or explicit settings aggregate
  - integration settings payload
  - billing preference fields now stored separately in DynamoDB

#### Control-plane and billing

- `accounts`
- `billing_customers`
- `billing_events`
- `trial_histories`
- `account_api_keys`
- `oauth_clients`
- `account_usage_monthly`

### Keep separate for now

Do not move nonprofit request handling in the initial pivot:

- Athena/S3 nonprofit source and search data
- Form 990 ingest artifacts and Glue catalog datasets
- `profiles` materialized-serving cache
- state-registry and source-provider data

Phase 24E adds an additive PostgreSQL nonprofit schema foundation for:

- `nonprofits`
- `nonprofit_filings`
- `nonprofit_sources`
- `compliance_checks`

That schema is intentionally additive. Phase 24G narrows the read-path gap by
allowing lookup, search, and filings reads to use PostgreSQL behind an
explicit selector, while Athena still remains in play for enrichment-heavy
nonprofit reads and the serving cache remains unchanged.

## Repository and Runtime Refactor Direction

### Preserve existing contracts

Keep these stable:

- customer-account repository protocols in `identity_repositories.py`
- `AuditLogRepository`
- `ControlPlaneStore`
- route and response contracts in `lambda_query.py`

### Additive bootstrap plan

Introduce a persistence bootstrap/factory layer in follow-on phases:

- select DynamoDB or PostgreSQL implementation by domain
- keep domain-level service wiring unchanged
- allow temporary mixed mode
  - PostgreSQL for migrated domains
  - DynamoDB for not-yet-migrated domains

### Dynamo-to-relational adaptation notes

- replace GSI-driven access paths with explicit unique indexes and foreign keys
- replace single-table prefixes with normalized tables
- keep soft delete as application-visible hide behavior for organizations
- keep audit and billing events append-only
- choose one authoritative writer for usage counters during each migration step

## Recommended Migration Order

### Phase 24A

- document inventory
- define target relational model
- define runtime/bootstrap direction

### Phase 24B

- add PostgreSQL runtime configuration and adapter bootstrap seams
- add Terraform scaffolding for RDS PostgreSQL on `db.t4g.micro`
- keep production reads and writes on DynamoDB

### Phase 24C

- implement PostgreSQL repositories for:
  - users
  - organizations
  - memberships
  - plans
  - subscriptions
  - org API keys
  - org audit logs
- add SQLAlchemy and Alembic foundation
- keep invitations, backfill tooling, and runtime cutover as follow-on work

### Phase 24D

- cut over the active customer-account identity runtime to PostgreSQL for:
  - users
  - organizations
  - memberships
  - plans
  - org subscriptions
  - org API keys
  - shared identity and org audit logs
- keep invitations, usage, feature flags, and organization settings on
  DynamoDB as a temporary compatibility layer
- add DynamoDB-to-PostgreSQL backfill tooling and rollback guidance

### Phase 24E

- add nonprofit relational schema foundation for:
  - canonical nonprofit identity
  - filing records
  - source provenance records
  - compliance snapshot records
- keep Athena and serving-cache nonprofit reads unchanged

### Phase 24F

- refactor Form 990 ingestion persistence so normalized nonprofit rows,
  filings, and filing-source provenance can be written into PostgreSQL
- keep ingest discovery catalogs, raw source storage, and downstream nonprofit
  read paths unchanged
- make nonprofit ingest PostgreSQL persistence opt-in until ingest workers have
  fully standardized database connectivity in deployed environments

### Phase 24G

- add a PostgreSQL nonprofit query backend for:
  - EIN lookup
  - nonprofit search
  - filings retrieval
- keep the verification lookup flow hybrid:
  - canonical nonprofit row and latest filing facts from PostgreSQL
  - peer-benchmark and Form 990 enrichment from Athena
- keep source, compliance, and federal-awards routes enrichment-driven for now

### Phase 24H

- add reusable migration wrappers with:
  - dry-run mode
  - per-entity validation reporting
  - missing/invalid record samples
- keep the raw identity backfill function available, but prefer the migration
  wrapper during operational cutover
- backfill nonprofit PostgreSQL rows from:
  - Athena canonical nonprofit and filing reads
  - Dynamo materialized profile cache snapshots for source/compliance data when
    available
- document cutover, verification, and rollback in a dedicated runbook

### Later control-plane phase

- migrate control-plane:
  - accounts
  - billing customers
  - billing events
  - trials
  - control-plane API keys
  - OAuth clients
  - account usage

### Later

- reassess `profiles` serving cache
- keep nonprofit/search/source persistence separate unless a later product need
  changes that decision

## Compatibility, Rollback, and Test Strategy

### Compatibility

- preserve service interfaces
- preserve route payloads
- preserve frontend expectations
- keep DynamoDB adapters available during transition
- allow mixed mode where PostgreSQL owns migrated identity tables while
  DynamoDB still serves invitations, usage, feature flags, and settings

### Rollback

- use per-domain read-source selection
- keep fallback flags back to DynamoDB until each domain cutover is stable
- avoid full dual-write unless the domain needs it for safe transition
- for Phase 24D, keep `PLATFORM_IDENTITY_STORE_BACKEND=dynamodb` as the
  immediate rollback switch after backfill

### Tests to add in later phases

- repository contract parity tests for DynamoDB and PostgreSQL adapters
- auth and org-context restore parity tests
- billing/control-plane parity tests
- route integration tests through `lambda_query.py`
- backfill verification tests

### Test-fixture direction

- move shared service tests toward backend-agnostic repository fixtures
- keep adapter-specific tests for:
  - DynamoDB item/index behavior
  - PostgreSQL schema/query behavior

## Minimal Config Scaffolding for Follow-On Phases

Planned additions:

- PostgreSQL connection env vars and secret references
- domain-level persistence selection flags
- Terraform resources for:
  - RDS PostgreSQL
  - subnet group
  - security groups
  - credentials/secrets wiring
- Lambda connectivity guidance for VPC access

Existing DynamoDB env vars stay in place until each domain migrates.
