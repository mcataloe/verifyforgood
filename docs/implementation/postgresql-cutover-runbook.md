# PostgreSQL Cutover Runbook

This runbook captures the current PostgreSQL-only posture and the remaining
one-time migration helpers that still exist for historical DynamoDB data.

## Runtime Posture

- runtime persistence is PostgreSQL-only for customer accounts, organization
  settings, and control-plane/billing storage
- Terraform and deployment env wiring no longer carry DynamoDB table-name env
  vars or per-domain backend selectors
- the DynamoDB nonprofit profile cache is retired from the active runtime path

## Identity Domain

Use the migration wrapper only if you still need to inspect or copy legacy
DynamoDB identity data into PostgreSQL:

```bash
python -m verification.backend.shared.runtime.customer_accounts_migration --identity-table-name identity --dry-run
```

Apply the migrated identity rows:

```bash
python -m verification.backend.shared.runtime.customer_accounts_migration --identity-table-name identity
```

Expected report behavior:

- `source_counts` shows the DynamoDB source entities discovered
- `target_counts` shows the PostgreSQL rows present for those same keys
- `validation.*.missing` must be `0` before final cutover
- `invalid_items` and `sample_invalid_items` call out rows that need manual
  review instead of silently dropping them

Identity migration order:

1. run `alembic upgrade head`
2. run the identity migration wrapper in `--dry-run`
3. review any missing or invalid records
4. run the identity migration wrapper without `--dry-run`
5. confirm `validation.*.missing == 0`
6. recreate or reseed any remaining dev-only records directly in PostgreSQL

## Nonprofit Domain

The nonprofit migration utility remains available only for historical backfill
work. The active runtime no longer serves from the materialized DynamoDB
profile cache.

- canonical nonprofit rows and filing lists come from the existing Athena
  nonprofit client
- source provenance and compliance snapshots may be lifted from the legacy
  materialized profile cache when explicitly supplied to the migration utility

Dry-run example:

```bash
python -m verification.backend.shared.runtime.nonprofit_migration --dry-run --page-size 250 --profile-table-name profiles
```

Apply example:

```bash
python -m verification.backend.shared.runtime.nonprofit_migration --page-size 250 --profile-table-name profiles
```

Useful flags:

- `--max-eins` for bounded trial runs
- `--start-after-ein` for restartable segmented runs
- `--skip-profile-cache` to backfill only canonical nonprofit rows and filings
- `--dry-run` to validate PostgreSQL contents without writing

Expected report behavior:

- `processed_eins` shows the number of EINS scanned from the source query path
- `missing_lookup_records` identifies EINS that listed but did not resolve
- `source_counts` and `target_counts` reflect the nonprofit rows handled in the
  current run window
- `validation.*.missing` highlights missing PostgreSQL rows by entity type

Nonprofit cutover guidance:

1. run `alembic upgrade head`
2. if using a dedicated nonprofit database, run `alembic -c alembic_nonprofit.ini upgrade head`
3. for dev/shared-db cutover, run `python -m verification.backend.shared.local_dev db-cutover-nonprofit`
4. run the nonprofit migration utility in `--dry-run` on a bounded window
5. run a real bounded window and verify the report
6. run the full migration
7. deploy `PLATFORM_NONPROFIT_QUERY_BACKEND=postgres` only after lookup,
   search, and filings validation is clean

Dedicated nonprofit dev helpers:

- `python -m verification.backend.shared.local_dev db-current-nonprofit`
  shows the dedicated nonprofit Alembic revision
- `python -m verification.backend.shared.local_dev db-reset-nonprofit`
  drops and recreates the dedicated nonprofit schema and version table
- `python -m verification.backend.shared.local_dev db-cutover-nonprofit`
  destructively reloads nonprofit/Form 990 tables from the platform database
  into the dedicated nonprofit database

Safety rule:

- the destructive nonprofit helpers intentionally require explicit
  `PLATFORM_NONPROFIT_POSTGRES_*` settings and refuse to run against the shared
  platform database URL

## Current Exclusions

The current utilities do not attempt to migrate:

- already-cut-over PostgreSQL runtime domains such as invitations, usage,
  feature flags, organization settings, and control-plane billing/OAuth data
- live source/compliance/federal-awards route assembly beyond what is already
  represented in the materialized nonprofit profile cache

