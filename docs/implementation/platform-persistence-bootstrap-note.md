# Platform Persistence Bootstrap Note

## Intent

This note now records the completed cutover posture. PostgreSQL is the active
runtime backend for the platform relational domains, while route and service
contracts remain stable.

## Current Rules

- keep existing repository and store protocols as the primary seam
- use PostgreSQL as the only supported runtime datastore for customer accounts,
  organization settings, and control-plane/billing storage
- keep nonprofit lookup/search/filings backend selection limited to Athena vs
  PostgreSQL
- do not reintroduce DynamoDB runtime env vars or mixed-mode backend selectors

## Active Runtime Config

- PostgreSQL connection string or equivalent host/user/password/db settings
- secret-backed credentials for Lambda/runtime use

Current additive env names for the first PostgreSQL bootstrap phase:

- `PLATFORM_POSTGRES_ENABLED`
- `PLATFORM_POSTGRES_SECRET_ARN`
- `PLATFORM_POSTGRES_HOST`
- `PLATFORM_POSTGRES_PORT`
- `PLATFORM_POSTGRES_DATABASE`
- `PLATFORM_POSTGRES_SSLMODE`
- `PLATFORM_POSTGRES_URL` as an optional compatibility fallback only

Current infrastructure rule:

- the query/runtime Lambda is VPC-attached when PostgreSQL is enabled so later repository phases can connect to RDS without another network bootstrap phase

## First Domains to Wire Through the Bootstrap

1. portal identity and customer accounts
2. organization settings
3. control-plane and billing

## Cutover Status

- customer-account identity runtime is PostgreSQL-backed end to end
- invitations, usage, feature flags, and organization settings are now
  PostgreSQL-backed as well
- control-plane and billing runtime storage is PostgreSQL-backed
- nonprofit materialized DynamoDB profile serving has been retired from the
  runtime path
- historical migration wrappers still exist for operators who need to inspect
  or backfill old DynamoDB data
- the operational runbook lives in
  `docs/implementation/postgresql-cutover-runbook.md`

## Non-Goals

- no route-contract changes
- no frontend payload changes
- no migration of Athena/S3 nonprofit and filing datasets in the initial pivot
