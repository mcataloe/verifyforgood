# Form 990 Athena/S3 Hard Cutover Plan

## Objective

Remove every Form 990 dependency on AWS Athena and S3 from the repo and from
the deployed runtime model.

This is a hard cutover plan, not a staged compatibility plan. The target state
is:

- no Athena-backed Form 990 query path
- no Glue-backed Form 990 dataset catalog
- no S3-backed Form 990 source staging, manifests, artifacts, or run metadata
- no backend selector that allows choosing Athena/S3-era Form 990 behavior
- no Form 990 deployment wiring that grants Athena/Glue/S3 access just in case

The only supported Form 990 posture after this cutover is:

- PostgreSQL as the durable data store for normalized Form 990 data and runtime
  metadata
- workspace-local ZIP/XML handling during ingest execution
- direct HTTP acquisition from the upstream IRS source URL during processing

## Non-Negotiable Cutover Rules

1. Remove selectors instead of changing defaults.
   `PLATFORM_NONPROFIT_QUERY_BACKEND=athena|postgres` is not compatible with a
   hard cutover. Form 990 runtime behavior must become PostgreSQL-only.

2. Remove S3-shaped workflow contracts, not just S3 I/O.
   Fields such as `source_bucket`, `destination_bucket`, `source_key`,
   `skip_staging`, and `destination_prefix` encode the legacy model and should
   be replaced with a workspace/direct-download contract.

3. Delete deployment scaffolding once the PostgreSQL path is complete.
   Athena workgroups, Glue tables, Form 990 S3 prefixes, and S3/Athena/Glue IAM
   grants must be removed from Terraform rather than left dormant.

4. Treat cutover as one-way at the application layer.
   Rollback, if ever needed, would require reverting code and reprovisioning
   removed AWS resources. The application itself should not keep a rollback
   branch in the runtime surface.

## Current Repo Coupling Inventory

### Runtime Query Coupling

- [backend/api/src/verification_backend/api/runtime.py](/abs/path/C:/Repos/Verification/backend/api/src/verification_backend/api/runtime.py)
  still defines `DATABASE`, `TABLE`, `WORKGROUP`,
  `FORM990_*_TABLE`, `_get_athena_client()`, and Athena-specific exception
  handling.
- [infrastructure/verification/platform/runtime.py](/abs/path/C:/Repos/Verification/infrastructure/verification/platform/runtime.py)
  still exports `QueryRuntimeConfig` and `build_athena_client()`.
- [infrastructure/verification/platform/persistence.py](/abs/path/C:/Repos/Verification/infrastructure/verification/platform/persistence.py)
  still allows `PLATFORM_NONPROFIT_QUERY_BACKEND=athena`.
- [private-platform/src/verification_platform/runtime/persistence.py](/abs/path/C:/Repos/Verification/private-platform/src/verification_platform/runtime/persistence.py)
  still takes an `athena_client` and returns it when the selector is not
  `postgres`.
- [infrastructure/verification/query/athena_service.py](/abs/path/C:/Repos/Verification/infrastructure/verification/query/athena_service.py),
  [infrastructure/verification/query/athena_adapter.py](/abs/path/C:/Repos/Verification/infrastructure/verification/query/athena_adapter.py),
  and
  [infrastructure/verification/query/athena.py](/abs/path/C:/Repos/Verification/infrastructure/verification/query/athena.py)
  still implement the legacy Form 990/Athena query stack.
- [private-platform/src/verification_platform/runtime/nonprofit_migration.py](/abs/path/C:/Repos/Verification/private-platform/src/verification_platform/runtime/nonprofit_migration.py)
  still backfills nonprofit/Form 990 rows from Athena and the old materialized
  cache posture.

### Active Form 990 Ingest And Ops S3 Coupling

- [backend/ingest-task/src/verification_backend/ingest_task/local_runner.py](/abs/path/C:/Repos/Verification/backend/ingest-task/src/verification_backend/ingest_task/local_runner.py)
  still publishes Form 990 ingest run metadata through `S3RunStore` when
  `OPS_METADATA_BUCKET` is present.
- [backend/api/src/verification_backend/api/runtime.py](/abs/path/C:/Repos/Verification/backend/api/src/verification_backend/api/runtime.py)
  still builds `S3RunStore` for Form 990/ops views through
  `OPS_METADATA_BUCKET`.
- [infrastructure/verification/ops/run_store.py](/abs/path/C:/Repos/Verification/infrastructure/verification/ops/run_store.py)
  remains the S3-backed implementation for ingest/refresh run metadata.
- [infrastructure/verification/ingest/workflow.py](/abs/path/C:/Repos/Verification/infrastructure/verification/ingest/workflow.py)
  and
  [infrastructure/verification/ingest/staging.py](/abs/path/C:/Repos/Verification/infrastructure/verification/ingest/staging.py)
  still define an S3-shaped monthly ingest contract.
- [infrastructure/verification/form990/monthly_processing.py](/abs/path/C:/Repos/Verification/infrastructure/verification/form990/monthly_processing.py)
  is already downloading ZIPs directly from IRS URLs, but its surrounding
  contract still treats the source identity as an S3-style `source_key`.

### Infrastructure Coupling

- [infrastructure/aws_api_ecs.tf](/abs/path/C:/Repos/Verification/infrastructure/aws_api_ecs.tf)
  still injects `DATABASE`, `TABLE`, `WORKGROUP`, and `FORM990_*_TABLE`
  env vars into the API task and grants `s3:*`, `athena:*`, and `glue:*`.
- [infrastructure/main.tf](/abs/path/C:/Repos/Verification/infrastructure/main.tf)
  still provisions:
  - `aws_s3_bucket.athena_results`
  - `aws_athena_workgroup.eo_bmf`
  - `aws_glue_catalog_database.eo_bmf`
  - Form 990 Glue tables for metadata, metrics, governance, and quality
  - Form 990 S3 prefix locals
- [infrastructure/aws_s3.tf](/abs/path/C:/Repos/Verification/infrastructure/aws_s3.tf)
  still provisions the IRS/source-data bucket used by the legacy Form 990 S3
  posture.
- [infrastructure/variables.tf](/abs/path/C:/Repos/Verification/infrastructure/variables.tf)
  still exposes Form 990 S3 prefix variables, monthly schedule bucket inputs,
  and `platform_nonprofit_query_backend=athena|postgres`.

### Documentation And Test Coupling

- [docs/monthly-ingest-architecture.md](/abs/path/C:/Repos/Verification/docs/monthly-ingest-architecture.md),
  [docs/monthly-ingest-runbook.md](/abs/path/C:/Repos/Verification/docs/monthly-ingest-runbook.md),
  and
  [docs/form990-ingest-plan.md](/abs/path/C:/Repos/Verification/docs/form990-ingest-plan.md)
  still describe S3-first Form 990 workflow behavior.
- [docs/implementation/postgresql-cutover-runbook.md](/abs/path/C:/Repos/Verification/docs/implementation/postgresql-cutover-runbook.md)
  still describes the nonprofit/Form 990 source path as Athena-backed.
- Athena-specific tests and stubs remain in files such as
  [tests/test_athena_query_service.py](/abs/path/C:/Repos/Verification/tests/test_athena_query_service.py)
  and multiple API/runtime tests that still patch `module.athena_client`.

## Target End State

### Data Plane

- PostgreSQL stores:
  - nonprofit identity rows
  - normalized filing rows
  - canonical raw filing JSON
  - archive metadata
  - extracted-file metadata
  - Form 990 ingest run metadata that currently lives in `S3RunStore`
- No Form 990-derived dataset is read from S3 or queried through Athena/Glue.

### Runtime Contract

- API runtime has no Athena client and no Athena exception path.
- Nonprofit/Form 990 query runtime is PostgreSQL-only.
- Monthly ingest runtime accepts a direct-source contract such as:
  - `archive_url`
  - `archive_id` or canonical archive identity
  - `job_id`
  - `correlation_id`
  - `workflow_version`
  - optional workspace/runtime tuning fields
- No `source_bucket`, `destination_bucket`, `source_key`, or staging result
  bucket/key aliases remain.

### Infrastructure

- No Athena workgroup for nonprofit/Form 990 data.
- No Glue database/table resources for Form 990 datasets.
- No Form 990 S3 source bucket/prefix contract.
- No Form 990-specific S3/Athena/Glue IAM grants on API or ingest roles.

## Required Preconditions Before Deletion

### 1. PostgreSQL Query Parity Must Be Complete

Before deleting Athena code, the PostgreSQL path must fully cover:

- nonprofit lookup
- nonprofit search
- filings list
- Form 990 enrichment
- peer benchmark aggregation

Current gap:

- PostgreSQL enrichment is now derived from persisted filing payloads
  directly, but peer benchmark aggregation still needs a PostgreSQL-native
  implementation.

### 2. Form 990 Run Metadata Needs A Non-S3 Home

The current operational views still assume `S3RunStore`. The hard cutover needs
either:

- PostgreSQL tables for ingest/refresh run summaries and filing-level run rows,
  or
- explicit retirement of those API/ops views if the product no longer needs
  them.

Do not keep S3 run metadata as a “temporary” side path.

### 3. Historical Migration/Backfill Must No Longer Need Athena

`nonprofit_migration.py` currently depends on Athena as the historical source.
Before deleting Athena resources, choose one:

- replace it with a PostgreSQL-to-PostgreSQL backfill/verification tool, or
- retire it entirely and declare the old Athena/S3 datasets out of scope.

### 4. Archive Retention Policy Must Be Explicit

The workspace runtime already processes ZIP/XML locally. The hard cutover needs
an explicit answer for historical replay:

- either canonical `raw_filing_json` plus archive metadata is sufficient, or
- PostgreSQL gains a durable archive/blob retention mechanism outside S3.

The plan should not assume replay remains available from S3 after cutover.

## Execution Plan

### Phase 1. Remove Athena From The Application Runtime

Scope:

- delete Athena client construction from the API runtime
- remove Athena query configuration from runtime env contracts
- make nonprofit query runtime PostgreSQL-only
- remove Athena exception handling paths from the API

Primary files:

- `backend/api/src/verification_backend/api/runtime.py`
- `infrastructure/verification/platform/runtime.py`
- `infrastructure/verification/platform/persistence.py`
- `private-platform/src/verification_platform/runtime/persistence.py`
- `infrastructure/verification/query/athena*.py`

Concrete changes:

1. Delete `_get_athena_client()` and all `DATABASE`, `TABLE`, `WORKGROUP`,
   `FORM990_*_TABLE` env handling from the API runtime.
2. Replace `build_nonprofit_query_client(athena_client=..., env=...)` with a
   PostgreSQL-only builder.
3. Remove `AthenaQueryError` and `AthenaQueryTimeout` handling from request and
   batch-verify paths.
4. Remove `build_athena_client()` and Athena runtime config objects from the
   platform layer.
5. Delete Athena query modules entirely once tests no longer import them.

Exit criterion:

- no active API route imports or constructs Athena query clients.

### Phase 2. Remove S3 From Form 990 Runtime And Ops Paths

Scope:

- replace `S3RunStore`
- remove S3-shaped workflow contracts
- remove Form 990 staging semantics

Primary files:

- `backend/ingest-task/src/verification_backend/ingest_task/local_runner.py`
- `backend/api/src/verification_backend/api/runtime.py`
- `infrastructure/verification/ops/run_store.py`
- `infrastructure/verification/ingest/workflow.py`
- `infrastructure/verification/ingest/staging.py`
- `infrastructure/verification/form990/monthly_processing.py`

Concrete changes:

1. Introduce a PostgreSQL-backed run store or remove the run views.
2. Replace `OPS_METADATA_BUCKET` / `OPS_METADATA_PREFIX` with a non-S3 runtime
   contract.
3. Replace `MonthlyIngestWorkflowInput` fields:
   - remove `source_key`
   - remove `destination_prefix`
   - remove `skip_staging`
   - remove any bucket/key alias behavior
4. Rename `source_key` concepts inside monthly processing to a neutral archive
   identity such as `archive_identity` or `archive_locator`.
5. Delete staging result helpers that only exist to shuttle S3 bucket/key
   outputs.

Exit criterion:

- the monthly Form 990 runtime can be executed end to end with direct source
  URLs plus PostgreSQL only.

### Phase 3. Retire Athena/S3-Based Migration And Historical Tooling

Scope:

- remove historical backfill paths that require Athena or S3-era datasets

Primary files:

- `private-platform/src/verification_platform/runtime/nonprofit_migration.py`
- docs/runbooks that instruct Athena-backed backfills

Concrete changes:

1. Retire the Athena-based nonprofit migration utility or replace it with a
   PostgreSQL validation tool.
2. Remove all references to Athena-backed nonprofit/Form 990 reads from
   cutover runbooks.
3. Drop migration-era env and CLI guidance that assumes Glue/Athena datasets
   still exist.

Exit criterion:

- no operational runbook in the repo instructs operators to use Athena or S3
  for Form 990 data movement.

### Phase 4. Delete Terraform Resources And Env Wiring

Scope:

- remove all Form 990 Athena/S3 infra and corresponding IAM/env surface

Primary files:

- `infrastructure/aws_api_ecs.tf`
- `infrastructure/main.tf`
- `infrastructure/aws_s3.tf`
- `infrastructure/variables.tf`
- Terraform outputs/examples/tfvars that mention Form 990 Athena/S3 inputs

Concrete changes:

1. Remove API task env vars:
   - `DATABASE`
   - `TABLE`
   - `WORKGROUP`
   - `FORM990_FILINGS_TABLE`
   - `FORM990_METRICS_TABLE`
   - `FORM990_GOVERNANCE_TABLE`
   - `FORM990_QUALITY_TABLE`
   - `OPS_METADATA_BUCKET`
2. Remove broad `s3:*`, `athena:*`, and `glue:*` grants that only exist for
   Form 990/nonprofit query support.
3. Delete:
   - Athena results bucket
   - Athena workgroup
   - Glue database and Form 990 Glue tables
   - Form 990 S3 prefix locals and variables
   - monthly ingest schedule/source bucket variables
4. Rework naming locals and outputs so they no longer promise Form 990 data
   lake resources.

Exit criterion:

- Terraform no longer provisions or references Athena/Glue/Form 990 S3
  resources.

### Phase 5. Rewrite Tests And Documentation To Match The Final Model

Scope:

- remove historical compatibility framing
- make docs consistent with workspace/PostgreSQL-only Form 990 behavior

Concrete changes:

1. Delete Athena-specific query tests.
2. Rewrite API/runtime tests so they no longer stub `athena_client`.
3. Rewrite monthly ingest docs around:
   - direct source URL acquisition
   - workspace-local extraction
   - PostgreSQL persistence
   - no staging bucket
4. Update `README.md` and cutover docs so they no longer describe Form 990 as
   S3/Glue/Athena-backed.

Exit criterion:

- a repo-wide search for Form 990 Athena/S3 behavior returns only historical
  references that are intentionally retained outside the active product/docs
  surface, or returns nothing.

## Validation Checklist

Before declaring the cutover complete:

1. `rg -n "athena|Athena|glue|Glue|FORM990_.*TABLE|WORKGROUP"` returns no
   matches in active Form 990 runtime paths.
2. `rg -n "source_bucket|destination_bucket|skip_staging|S3RunStore|OPS_METADATA_BUCKET"` returns no matches in active Form 990 runtime paths.
3. `GET /v1/nonprofit/{ein}` and related filings/search routes execute with no
   Athena client construction or Athena exception handling.
4. The monthly Form 990 worker runs successfully using direct IRS archive URLs
   and persists results only to PostgreSQL.
5. Terraform plan shows removal of Athena/Glue/Form 990 S3 resources and no
   remaining task-role dependency on them.
6. Docs and runbooks describe only the PostgreSQL/workspace model.

## Recommended Merge Strategy

Because this is explicitly a hard cutover, the safest implementation order is:

1. finish PostgreSQL parity and run-metadata replacement first
2. merge the runtime deletion changes
3. immediately merge Terraform/env cleanup
4. finish docs/test cleanup in the same change window or immediately after

Do not merge Phase 4 before Phase 1 and Phase 2 are ready, and do not keep
dead AWS resources “for a while” after the runtime stops using them.
