# Monthly Ingest Runbook

## Purpose

The monthly private-ingest workflow is a Step Functions Standard state machine that orchestrates temporary private-network access, optional staging, ECS processing, and endpoint cleanup for low-frequency bulk ingest jobs.

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

This repository now defines the orchestration, but the following deployment-specific references must still be supplied per environment:

- VPC id
- private subnet ids
- endpoint security group ids
- task security group ids
- ECS cluster ARN
- ECS task definition ARN
- ECS task execution role ARN
- ECS task role ARN
- staging Lambda ARN when staging is required

## Schedule Notes

- The EventBridge schedule is optional and disabled unless `monthly_ingest_schedule_expression` and the required schedule input values are set.
- Scheduled executions pass a static workflow input payload with an added `schedule_context.trigger = "eventbridge"` marker.
- The schedule does not create persistent interface endpoints; those remain per-execution only.

## Operator Guidance

- Use `skip_staging=true` only when the source object already exists in S3 at the provided `source_bucket` and `source_key`.
- If `skip_staging=false`, ensure `monthly_ingest_staging_lambda_arn` is configured and the Lambda returns a staged `source_bucket` and `source_key` when it needs to override the input values.
- Inspect Step Functions execution history first for endpoint lifecycle and cleanup state.
- Inspect ECS task stop reason and container exit code second for worker failures.

## Remaining Follow-Up

- implement the staging Lambda runtime behavior
- implement the ECS worker task definition and image
- connect expected job artifacts (`manifest.json`, `artifacts.json`, `summary.json`) to downstream dataset-specific processing
- decide whether later phases should emit a customer-safe summary record outside Step Functions execution history
