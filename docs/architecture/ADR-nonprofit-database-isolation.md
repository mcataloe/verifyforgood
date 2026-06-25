# Nonprofit Database Isolation

## Status

accepted

## Decision

Run nonprofit entity data, nonprofit filings, Form 990 raw filing content, and
Form 990 archive/extracted-file ingest state on a dedicated PostgreSQL database
when deployment wiring provides one, while keeping customer-account,
organization-settings, and control-plane/billing data on the existing platform
PostgreSQL database.

The runtime remains backward compatible:

- if `PLATFORM_NONPROFIT_POSTGRES_*` settings are absent, nonprofit runtime code
  falls back to `PLATFORM_POSTGRES_*`
- service and repository contracts stay unchanged
- customer and nonprofit data can continue to share one database temporarily
  during migration

## Context

The current codebase already separates domains at the service/repository level
but still assumes one PostgreSQL connection path for:

- portal users, organizations, memberships, subscriptions, usage, feature flags,
  audit records, and organization settings
- control-plane accounts, billing customers, subscriptions, billing events,
  trials, API keys, and OAuth clients
- nonprofit identity, filing rows, source lineage, compliance snapshots, raw
  filing payloads, and Form 990 archive/extracted-file ingest metadata

That coupling creates an avoidable operational blast radius:

- large nonprofit ingest jobs share database availability with customer-facing
  identity and billing data
- nonprofit data maintenance and backfill work compete with customer workloads
- incident response and backup/restore boundaries are less clear than the
  domain model suggests

## Decision Details

### Data-plane split

Move these records behind the nonprofit database bootstrap path:

- `nonprofits`
- `nonprofit_filings`
- `nonprofit_raw_filings`
- `nonprofit_sources`
- `compliance_checks`
- `form990_archives`
- `form990_extracted_files`

Keep these on the platform/control-plane database:

- users, organizations, memberships, invitations
- organization subscriptions, usage, feature flags, audit logs, API keys
- organization settings
- control-plane accounts, billing customers, billing events, trials, API keys,
  and OAuth clients

### Bootstrap and compatibility

- nonprofit repository and query-client builders resolve
  `PLATFORM_NONPROFIT_POSTGRES_*` first and fall back to `PLATFORM_POSTGRES_*`
- federal-ingest ECS/local env alias handling maps `DATABASE_URL` onto both the
  platform and nonprofit URL slots when dedicated nonprofit wiring is absent
- local developer tooling adds a dedicated nonprofit schema bootstrap command
  without changing the existing platform migration command

### Migration boundary

This phase isolates runtime connection paths first. It does not yet provide a
fully independent nonprofit Alembic history. The current nonprofit bootstrap
creates only nonprofit/Form 990 tables on the dedicated nonprofit database and
leaves the existing platform Alembic flow as the source of truth for the
customer/control-plane schema.

## Consequences

- nonprofit ingest and nonprofit query storage can be deployed independently
  from customer/billing data
- scheduled-job failures on the nonprofit data plane no longer require sharing
  a database with customer account or payment history records
- infrastructure and operations need a follow-on phase for dedicated nonprofit
  schema migration history, deployment secrets, backup policy, and cutover
  runbooks
