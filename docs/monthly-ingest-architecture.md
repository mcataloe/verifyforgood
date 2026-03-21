# Monthly Ingest Workflow Architecture

## Scope

This phase introduces shared contracts, configuration, and documentation for a monthly ingest workflow that keeps heavy ZIP digestion off Lambda while avoiding persistent NAT gateway cost.

Current phase boundaries:

- define and wire the Step Functions state machine for endpoint lifecycle, optional staging, ECS execution, and cleanup
- centralize workflow naming, retry, timeout, and log-group conventions
- reuse existing S3 key patterns for downloaded source artifacts
- leave staging-Lambda business logic and ECS worker implementation details for later phases

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
- optionally invoke a staging Lambda
- run the ECS worker with `ecs:runTask.sync`
- always walk a reverse-order cleanup chain for created endpoints
- fail the Step Functions execution with structured JSON cause data when processing or cleanup fails

## Why ECS RunTask Owns Heavy Processing

The ZIP digestion step is a poor fit for Lambda because it can require larger ephemeral storage, longer-running CPU-heavy work, and isolated private-subnet execution. ECS Fargate `RunTask` is the right boundary because it provides:

- ephemeral compute with no standing worker fleet
- configurable CPU, memory, and ephemeral disk for large ZIP extraction
- direct execution in private subnets without public ingress
- a clean future path for additional ingest workloads that need the same runtime envelope

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
- ECS runtime contract:
  - required environment variables derived from the Step Functions payload
  - a stable JSON payload handoff contract
  - expected task output artifacts (`manifest.json`, `artifacts.json`, `summary.json`)
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

- TODO: implement the staging Lambda input/output behavior for monthly ZIP placement in S3
- TODO: provision or connect the target ECS task definition, cluster, subnet, and security-group references per environment
- TODO: connect task output artifacts to downstream dataset-specific manifests
