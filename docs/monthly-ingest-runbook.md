# Monthly Ingest Runbook

## Purpose

The monthly private-ingest workflow is a Step Functions Standard state machine that orchestrates temporary private-network access, optional staging, ECS processing, and endpoint cleanup for low-frequency bulk ingest jobs.

Use the same terminology throughout operations and code review:

- conductor: Step Functions
- staging component: staging Lambda
- worker: ECS Fargate worker
- permanent endpoint: S3 gateway endpoint
- ephemeral endpoints: `ecr.api`, `ecr.dkr`, and `logs`

## Execution Phases

1. Validate the workflow input contract.
2. Create the `ecr.api` interface endpoint.
3. Poll until `ecr.api` becomes `available`.
4. Create the `ecr.dkr` interface endpoint.
5. Poll until `ecr.dkr` becomes `available`.
6. Create the `logs` interface endpoint.
7. Poll until `logs` becomes `available`.
8. Invoke the staging Lambda when `skip_staging=false`.
9. Run the ECS Fargate worker with `ecs:runTask.sync`.
10. Delete `logs`, `ecr.dkr`, and `ecr.api` in reverse order.
11. Return success output or fail the execution with a structured JSON cause.

## Staging Responsibility

The staging Lambda is responsible only for:

- downloading the vendor ZIP from the upstream source URL
- writing the ZIP unchanged to S3 under the raw-source key contract
- returning staged object metadata (`bucket`, `key`, `size`, `checksum`, `source_timestamp`, `job_id`, `correlation_id`)

Ownership note:

- the staging runtime implementation now lives under `backend/ingest-task`
- the infrastructure Lambda handler path is a compatibility wrapper only

The staging Lambda does not:

- extract ZIP members
- parse filings
- run the heavy monthly processing job
- manage endpoint lifecycle

Ownership note:

- executable staging and task runtime ownership now lives under `backend/ingest-task/src/verification_backend/ingest_task/`
- `infrastructure/lambda_monthly_ingest_staging.py` and `infrastructure/monthly_ingest_worker.py` remain temporary compatibility adapters for deployment wiring

## ECS Worker Runtime Contract

The ECS worker reads the shared monthly-ingest contract from environment variables:

- `MONTHLY_INGEST_WORKFLOW_NAME`
- `MONTHLY_INGEST_WORKFLOW_VERSION`
- `MONTHLY_INGEST_JOB_ID`
- `MONTHLY_INGEST_CORRELATION_ID`
- `MONTHLY_INGEST_SOURCE_BUCKET`
- `MONTHLY_INGEST_SOURCE_KEY`
- `MONTHLY_INGEST_DESTINATION_BUCKET`
- `MONTHLY_INGEST_DESTINATION_PREFIX`
- `MONTHLY_INGEST_INPUT_JSON`

It also uses:

- `FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES`

Ownership note:

- the ECS worker implementation now lives under `backend/ingest-task`
- the `infrastructure/monthly_ingest_worker.py` file remains only as a compatibility entrypoint for deployment wiring
- the managed ECS task now uses the backend-owned `ecs-run` parity command so
  task execution shares the same archive-at-a-time orchestration path as local
  `python -m ingest_task.cli run`
- on the parity path, IRS ZIP downloads and extracted XML stay inside the
  task workspace and are not uploaded to S3 as runtime artifacts

ECS parity env aliases supported by the runtime:

- `WORKSPACE_PATH` -> `FORM990_WORKSPACE_DIR`
- `STRICT_MODE` -> strict stop-on-first-failure behavior
- `MAX_ARCHIVES` -> archive-processing limit
- `LOG_LEVEL` -> runtime logging level
- `DATABASE_URL` -> `PLATFORM_POSTGRES_URL` when a direct URL-style Postgres
  configuration is provided externally
- `DATABASE_URL` -> `PLATFORM_NONPROFIT_POSTGRES_URL` when a dedicated
  nonprofit database is used and the native nonprofit URL is absent

Expected source object:

- the current worker expects a staged raw-source ZIP using the existing Form 990 key contract:
  - `form990/raw-sources/{source_year}/zip_archive/{source_archive_key}/{source_signature}/{source_filename}`

Expected outputs:

- `{destination_prefix}/monthly-workflows/jobs/{job_id}/manifest.json`
- `{destination_prefix}/monthly-workflows/jobs/{job_id}/artifacts.json`
- `{destination_prefix}/monthly-workflows/jobs/{job_id}/summary.json`
- dataset and raw XML outputs under the same job-scoped prefix

Compatibility note:

- those S3 outputs still describe the legacy `monthly-worker` contract
- the local/ECS parity `run` and `ecs-run` path now keeps raw IRS ZIP/XML
  artifacts in ephemeral workspace storage and persists only normalized
  PostgreSQL data plus archive/file metadata

## Managed ECS Resources

When `monthly_ingest_task_definition_arn` is not supplied, Terraform manages:

- the worker ECR repository
- the worker CloudWatch log group
- the ECS task execution role
- the ECS task role
- the Fargate task definition

Key task-definition controls:

- `monthly_ingest_worker_image_uri`
- `monthly_ingest_worker_image_tag`
- `monthly_ingest_task_cpu`
- `monthly_ingest_task_memory`
- `monthly_ingest_task_ephemeral_storage_gib`
- `monthly_ingest_task_log_retention_days`
- `monthly_ingest_task_allowed_bucket_arns`

## Cleanup Behavior

- Cleanup is shared by both success and failure paths.
- If endpoint creation fails after one or more earlier endpoints were created, the workflow still walks the delete chain for the endpoints that already exist.
- Cleanup delete failures are recorded and can cause the overall execution to fail even if the ECS task finished successfully.

## Failure Handling

- AWS service tasks use retry/backoff before failing.
- Endpoint polling fails fast on terminal endpoint states such as `failed`, `rejected`, `deleted`, or `expired`.
- Endpoint polling also fails on timeout after the configured maximum number of checks.
- ECS task failures are detected from Step Functions task errors, ECS `failures[]`, or non-zero container exit codes.
- Failure results are serialized into the Step Functions execution cause so operators can inspect the exact stage, cleanup status, and resource identifiers from execution history.

## Required External References

This repository now defines the workflow, but the following deployment-specific references must still be supplied per environment:

- VPC id
- private subnet ids
- endpoint security group ids
- task security group ids
- ECS cluster ARN

Terraform now manages the ECS task definition, task roles, EventBridge target,
and worker log group directly when the external ARN overrides are left empty.
The ingest task downloads and stages source artifacts itself; there is no
separate staging Lambda.

## Schedule Notes

- The EventBridge schedule is optional and disabled unless `monthly_ingest_schedule_expression`, `monthly_ingest_schedule_source_bucket`, `monthly_ingest_schedule_destination_bucket`, and `monthly_ingest_schedule_destination_prefix` are set.
- Scheduled executions pass a static workflow input payload with an added `schedule_context.trigger = "eventbridge"` marker.
- `monthly_ingest_schedule_context_json` is the preferred place to supply upstream ZIP metadata such as `source_url`, `source_year`, `source_archive_key`, `source_filename`, and `source_timestamp`.
- Scheduled runs target ECS directly; there is no Step Functions or Lambda staging hop.
- The schedule does not create persistent interface endpoints; those remain per-execution only.

## Operator Guidance

- Use `skip_staging=true` only when the source object already exists in S3 at the provided `source_bucket` and `source_key`.
- If `skip_staging=false`, ensure `schedule_context` includes the upstream ZIP location expected by the staging Lambda. For the current Form 990 binding that means `source_url` plus optional source identity fields.
- For manual backfills or tests, start the Step Functions execution directly with:
  - `skip_staging=false` and a custom `schedule_context` payload to fetch and stage a historical ZIP
  - or `skip_staging=true` with a pre-staged S3 object already present
- Inspect Step Functions execution history first for endpoint lifecycle and cleanup state.
- Inspect ECS task stop reason and container exit code second for worker failures.
- Inspect the ECS task `summary.json` artifact third for job-scoped counts and source/archive metadata.

## IAM Notes

Managed task execution role:

- uses the standard `AmazonECSTaskExecutionRolePolicy`
- supports ECR image pull and CloudWatch Logs delivery

Managed task role:

- `s3:ListBucket` on the platform data bucket plus any configured additional allowed buckets
- `s3:GetObject`
- `s3:PutObject`
- `s3:DeleteObject`

If a workflow needs to read from or write to buckets outside the default platform data bucket, add those bucket ARNs to `monthly_ingest_task_allowed_bucket_arns` or provide an external task role ARN.

## Failure Modes And Troubleshooting

Common failure classes:

- invalid input contract
- missing staged source object
- malformed ZIP archive
- ZIP archive with no processable XML members
- downstream parsing or S3 write failures

Troubleshooting sequence:

1. Check Step Functions execution history for the failing stage and cleanup result.
2. Check ECS task logs in the monthly-ingest ECS log group.
3. Check the job-scoped `summary.json` or `manifest.json` artifact if they were written.
4. Confirm the worker image tag exists in ECR and the source ZIP object exists in S3.
5. Confirm ephemeral storage sizing is large enough for the ZIP and extracted XML volume.

## Remaining Follow-Up

- connect expected job artifacts (`manifest.json`, `artifacts.json`, `summary.json`) to downstream dataset-specific processing
- add image build/push automation for the backend-owned `backend/ingest-task/Dockerfile`
- decide whether later phases should emit a customer-safe summary record outside Step Functions execution history

