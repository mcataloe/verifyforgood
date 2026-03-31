# PostgreSQL Cutover Runbook

This runbook captures the current migration utilities and the intended
cutover sequence for the PostgreSQL transition.

## Identity Domain

Use the validation wrapper before switching the runtime selector:

```bash
python -m charity_status_platform.runtime.customer_accounts_migration --identity-table-name identity --dry-run
```

Apply the migrated identity rows:

```bash
python -m charity_status_platform.runtime.customer_accounts_migration --identity-table-name identity
```

Expected report behavior:

- `source_counts` shows the DynamoDB source entities discovered
- `target_counts` shows the PostgreSQL rows present for those same keys
- `validation.*.missing` must be `0` before final cutover
- `invalid_items` and `sample_invalid_items` call out rows that need manual
  review instead of silently dropping them

Identity cutover order:

1. run `alembic upgrade head`
2. run the identity migration wrapper in `--dry-run`
3. review any missing or invalid records
4. run the identity migration wrapper without `--dry-run`
5. confirm `validation.*.missing == 0`
6. deploy with `PLATFORM_IDENTITY_STORE_BACKEND=postgres`

Identity rollback:

1. redeploy with `PLATFORM_IDENTITY_STORE_BACKEND=dynamodb`
2. leave PostgreSQL data in place for investigation
3. rerun the migration wrapper in `--dry-run` after fixing the mismatch cause

## Nonprofit Domain

The nonprofit migration utility is intentionally mixed-source:

- canonical nonprofit rows and filing lists come from the existing Athena
  nonprofit client
- source provenance and compliance snapshots can be lifted from the DynamoDB
  materialized profile cache when `PROFILE_TABLE_NAME` is available

Dry-run example:

```bash
python -m charity_status_platform.runtime.nonprofit_migration --dry-run --page-size 250 --profile-table-name profiles
```

Apply example:

```bash
python -m charity_status_platform.runtime.nonprofit_migration --page-size 250 --profile-table-name profiles
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
2. run the nonprofit migration utility in `--dry-run` on a bounded window
3. run a real bounded window and verify the report
4. run the full migration
5. deploy `PLATFORM_NONPROFIT_QUERY_BACKEND=postgres` only after lookup,
   search, and filings validation is clean

Nonprofit rollback:

1. redeploy with `PLATFORM_NONPROFIT_QUERY_BACKEND=athena`
2. keep PostgreSQL nonprofit rows for investigation and rerun
3. do not delete the DynamoDB materialized profile cache in this phase

## Current Exclusions

The current utilities do not attempt to migrate:

- DynamoDB invitations, usage, feature flags, or organization settings
- control-plane billing and OAuth records
- live source/compliance/federal-awards route assembly beyond what is already
  represented in the materialized nonprofit profile cache
