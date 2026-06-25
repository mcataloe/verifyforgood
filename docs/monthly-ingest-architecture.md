# Monthly Ingest Workflow Architecture

## Scope

This phase introduces the monthly schedule trigger plus the staging Lambda layer for a monthly ingest workflow that keeps heavy ZIP digestion off Lambda while avoiding persistent NAT gateway cost.

Terminology used in this document:

- workflow: the monthly private-ingest workflow
- conductor: Step Functions
- staging component: the staging Lambda
- worker: the ECS Fargate worker
- permanent network path: the S3 gateway endpoint
- ephemeral network paths: the `ecr.api`, `ecr.dkr`, and `logs` interface endpoints

Current phase boundaries:

- define and wire the Step Functions state machine for endpoint lifecycle, staging, ECS execution, and cleanup
- wire the monthly EventBridge schedule to start the workflow
- implement the staging Lambda that downloads the vendor ZIP and stores it under the existing raw-source S3 contract
- implement the ECS Fargate worker that downloads the staged ZIP from S3, digests it with ephemeral local storage, and writes job-scoped artifacts back to S3
- centralize workflow naming, retry, timeout, and log-group conventions
- reuse existing S3 key patterns for downloaded source artifacts
- leave only environment-specific image publishing and cluster attachment details for later phases

## Target Flow

`EventBridge Schedule -> Step Functions -> ephemeral interface endpoints -> staging Lambda -> S3 -> ECS RunTask in private subnets -> processed artifacts back to S3 -> endpoint cleanup`

Permanent infrastructure remains:

- VPC
- private subnet(s)
- ECS cluster
- S3 bucket
- S3 gateway endpoint

Ephemeral infrastructure per run remains:

- `ecr.api` interface endpoint
- `ecr.dkr` interface endpoint
- `logs` interface endpoint

## Why Step Functions Orchestrates Lifecycle

Step Functions is the lifecycle coordinator because the workflow has explicit setup, processing, and teardown stages that must remain ordered and observable:

- create interface endpoints before private-subnet compute starts
- invoke the staging Lambda for source placement into S3
- invoke ECS `RunTask` for the heavy ZIP digestion step
- capture success/failure state centrally
- ensure endpoint cleanup still has a defined place in the control flow

This keeps lifecycle concerns out of the processing container and makes retries explicit at the orchestration layer instead of embedding them in one large worker.

Implemented orchestration phases now are:

- validate required workflow input
- create `ecr.api`, `ecr.dkr`, and `logs` interface endpoints sequentially
- poll each endpoint until it becomes `available`
- invoke the staging Lambda unless `skip_staging=true`
- run the ECS worker with `ecs:runTask.sync`
- always walk a reverse-order cleanup chain for created endpoints
- fail the Step Functions execution with structured JSON cause data when processing or cleanup fails

The staging Lambda is intentionally narrow:

- read upstream ZIP source metadata from `schedule_context`
- download the ZIP from the vendor URL
- write the ZIP unchanged into S3
- return the resolved S3 bucket/key plus metadata for downstream processing
- avoid ZIP extraction or record-level digestion

Current runtime ownership:

- backend-owned runtime modules now live under `backend/ingest/federal`
- `infrastructure/lambda_monthly_ingest_staging.py` is now a deployment-compatible shim over the backend-owned staging runtime
- `infrastructure/monthly_ingest_worker.py` is now a deployment-compatible shim over the backend-owned ECS worker runtime

## Why ECS RunTask Owns Heavy Processing

The ZIP digestion step is a poor fit for Lambda because it can require larger ephemeral storage, longer-running CPU-heavy work, and isolated private-subnet execution. ECS Fargate `RunTask` is the right boundary because it provides:

- ephemeral compute with no standing worker fleet
- configurable CPU, memory, and ephemeral disk for large ZIP extraction
- direct execution in private subnets without public ingress
- a clean future path for additional ingest workloads that need the same runtime envelope

The ECS worker now:

- validates the shared monthly-ingest runtime contract from environment variables
- downloads the staged source ZIP from S3
- extracts XML members into a local temporary working directory
- builds filing records from those extracted members
- reuses the existing Form 990 ingest service to write normalized artifacts back to S3
- emits job-scoped `manifest.json`, `artifacts.json`, and `summary.json` control artifacts
- exits non-zero when the overall processing result is fully failed or the archive/input is invalid

Runtime ownership note:

- executable monthly ingest behavior now belongs to `backend/ingest/federal`
- Terraform and Step Functions may continue to invoke infrastructure wrapper files during the transition, but those wrappers should not accumulate runtime logic

## Why The S3 Gateway Endpoint Is Permanent

S3 is used on every ingest run and is also a foundational dependency for the broader platform. Keeping the gateway endpoint permanent is intentional because it:

- has no hourly interface-endpoint standing charge
- avoids recreating a baseline dependency on each run
- supports both the staging Lambda and ECS task path
- preserves private connectivity to the shared data lake without NAT

## Why ECR And CloudWatch Logs Interface Endpoints Are Ephemeral

The `ecr.api`, `ecr.dkr`, and `logs` endpoints exist only to support task image pulls and private logging during a run. Keeping them ephemeral is intentional because it avoids paying interface-endpoint hourly cost during idle periods while still allowing:

- image manifest resolution from ECR
- image layer download from ECR
- `awslogs` delivery from private Fargate tasks

Step Functions is responsible for their lifecycle so the cost-bearing resources exist only while the ingest workflow is active.

## Why NAT Gateway Is Excluded

NAT gateway is intentionally excluded because its standing monthly cost dominates the expected schedule cadence for a monthly batch workflow. The architecture instead uses:

- permanent private connectivity to S3 through the gateway endpoint
- on-demand interface endpoints only for services the ECS task needs during execution
- Lambda plus ECS tasks that remain ephemeral and event-driven

This keeps the private-subnet isolation model without paying for always-on egress infrastructure.

## Cost Posture

Monthly standing cost is minimized by keeping only the low-baseline shared primitives always present:

- VPC and private subnets
- ECS cluster metadata
- S3 bucket
- S3 gateway endpoint

The higher-cost, interface-based dependencies and the compute itself appear only during the scheduled run. That keeps idle-month footprint small while preserving operational isolation.

## Shared Contracts Introduced In This Phase

The shared contract layer now defines:

- Step Functions input contract:
  - `source_bucket`
  - `source_key`
  - `destination_bucket`
  - `destination_prefix`
  - `job_id`
  - `correlation_id`
  - `workflow_version`
  - optional `schedule_context`
  - optional `skip_staging`
- staging result contract:
  - `bucket`
  - `key`
  - alias fields `source_bucket` and `source_key` for Step Functions override compatibility
  - `size`
  - `checksum`
  - `checksum_algorithm`
  - optional `source_timestamp`
  - `job_id`
  - `correlation_id`
- ECS runtime contract:
  - required environment variables derived from the Step Functions payload
  - a stable JSON payload handoff contract
  - expected task output artifacts (`manifest.json`, `artifacts.json`, `summary.json`)
  - managed task defaults for image, CPU, memory, and ephemeral storage
- interface endpoint contract:
  - service identifiers
  - lifecycle expectation (`ephemeral`)
  - environment-aware service-name resolution
  - tagging for workflow, environment, and job correlation
- workflow config contract:
  - workflow name
  - workflow version
  - ECS cluster name reference
  - log-group naming conventions
  - default retry parameters
  - endpoint polling interval and max attempts
  - staging Lambda timeout
  - ECS task timeout
  - overall state-machine timeout

## Schedule And Staging Contract

The EventBridge schedule starts the Step Functions workflow with:

- `source_bucket`
- `destination_bucket`
- `destination_prefix`
- `job_id`
- `correlation_id`
- `workflow_version`
- `skip_staging`
- `schedule_context`

When `skip_staging=false`, the schedule can omit a real `source_key`. Terraform now supplies a non-persistent placeholder key and the staging Lambda replaces it with the actual staged object location before ECS runs.

For the current Form 990 monthly staging path, `schedule_context` should provide staging metadata either at the top level or under `schedule_context.staging`:

- `source_url`
- optional `source_year`
- optional `source_kind`
- optional `source_archive_key`
- optional `source_filename`
- optional `source_signature`
- optional `source_timestamp`

If some fields are omitted, the staging helper infers them from the upstream ZIP URL when practical.

## S3 Staging Contract

The staging Lambda reuses the existing raw-source key strategy:

- `form990/raw-sources/{source_year}/{source_kind}/{source_archive_key}/{source_signature}/{source_filename}`

It also writes object metadata for:

- `job_id`
- `correlation_id`
- `workflow_version`
- `source_url`
- `source_kind`
- `source_year`
- `source_archive_key`
- `source_filename`
- `source_timestamp` when supplied
- `checksum_sha256`
- `downloaded_at`

That keeps the staged ZIP immutable, traceable, and reusable by later ECS processing or manual backfills.

## ECS Runtime Output Contract

For a job-scoped destination such as:

- `{destination_prefix}/monthly-workflows/jobs/{job_id}/`

the ECS worker writes:

- `manifest.json`
  - high-level job manifest with source object identity, extraction summary, and ingest result
- `artifacts.json`
  - concrete downstream artifact locations such as:
    - `raw_xml_prefix`
    - `filing_records_s3_key`
    - `metrics_s3_key`
    - `governance_s3_key`
    - `quality_s3_key`
    - `relationships_s3_key`
    - `processing_manifest_s3_key`
- `summary.json`
  - compact operator-oriented status summary with counts and key identifiers

The worker also writes dataset artifacts under the same job-scoped prefix:

- `raw-xml/`
- `datasets/metadata/`
- `datasets/metrics/`
- `datasets/governance/`
- `datasets/quality/`
- `datasets/relationships/`
- `processing/`

This keeps the ECS task focused on processing while preserving a stable output contract for orchestration and future downstream wiring.

## Managed ECS Task Definition

When `monthly_ingest_task_definition_arn` is empty, Terraform now manages:

- an ECR repository for the worker image
- a CloudWatch log group for ECS task logs
- an ECS task execution role
- an ECS task role with S3 read/write access to the platform data bucket plus any configured additional allowed buckets
- a Fargate task definition with:
  - container image URI resolution
  - `awsvpc` network mode
  - `FARGATE` compatibility
  - configurable CPU and memory
  - configurable ephemeral storage
  - `awslogs` configuration
  - the shared monthly-ingest environment-variable contract

If an environment already has a managed image, task definition, or roles, the existing ARN overrides still work.

## Cleanup And Failure Model

The state machine uses a shared cleanup chain instead of trying to embed teardown in the ECS worker:

- any task-level failure stores structured failure metadata in workflow state
- cleanup then checks each endpoint id and deletes only the endpoints that were actually created
- cleanup delete failures are also captured and can fail the execution
- failure output is serialized into the Step Functions execution cause so operators can inspect:
  - stage of failure
  - created endpoint ids
  - cleanup status per endpoint
  - staging status
  - ECS response payload

## Future Workflow Expansion

The contract layer lives in the generic ingest package so future monthly ingest workflows can reuse the same orchestration shape without inheriting Form 990-specific naming. Form 990 keeps only a thin binding that maps the shared workflow contract to the existing raw-source and manifest prefixes.

That separation supports future additions such as:

- other bulk monthly source ingests
- source-specific ECS task images sharing the same Step Functions skeleton
- renamed customer-facing products without renaming the core orchestration contract

## TODO

- TODO: provision or connect the target ECS task definition, cluster, subnet, and security-group references per environment
- TODO: connect task output artifacts to downstream dataset-specific manifests
- TODO: add workflow-specific schedule builders if future monthly sources need stronger typed schedule_context helpers
- TODO: add CI or release automation to build and push `backend/ingest/federal/Dockerfile` images into the managed ECR repository
