# ECS Runtime Migration Blueprint

## Summary

This blueprint defines the staged migration from the current API Gateway +
Lambda HTTP runtime to an ALB-fronted ECS Fargate API service.

The current repo reality is:

- one monolithic request Lambda in `infrastructure/lambda_query.py`
- broad route coupling in `infrastructure/aws_api_gateway.tf`
- API custom-domain coupling in `infrastructure/aws_route53.tf`
- ZIP packaging and Lambda-specific deployment assumptions in
  `infrastructure/aws_lambda.tf`
- strong test coupling to `module.handler(event, None)` patterns

The target runtime is:

- Route53 -> ALB -> ECS Fargate -> containerized Python API app
- CloudWatch logs and metrics
- Secrets Manager-backed sensitive config
- private-subnet task execution with existing PostgreSQL network posture reused

## Phase 25C/25D implementation status

The repo now includes the additive Terraform needed to stand up the parallel
ECS API runtime:

- managed ECS cluster
- managed API ECR repository
- ECS Fargate task definition and service for the API
- CloudWatch log group for API tasks
- public ALB, HTTPS listener, and API target group
- dedicated ALB and task security groups
- PostgreSQL ingress support for ECS API tasks
- outputs and tfvars examples for the new deployment contract
- Route53 cutover from API Gateway custom-domain ingress to the ALB

Current cutover posture:

- Route53 now points the primary hostname at the ALB
- ECS + ALB is the primary runtime for the backend API
- Lambda + API Gateway remain deployable only as a deprecated rollback path
- API Gateway custom-domain resources are no longer the production ingress
  mechanism

## Current Coupling Inventory

### Request runtime coupling

`lambda_query.py` currently owns:

- API Gateway event parsing
- route normalization and version stripping
- CORS/preflight response behavior
- module-global lazy initialization for cold-start mitigation
- auth, nonprofit, billing, portal, admin, and ops service composition

This means the runtime pivot is not just an infrastructure change. It requires
an application-boundary extraction phase before containerization.

### Terraform and ingress coupling

Current API-serving infrastructure assumptions:

- REST API Gateway resources and methods are explicitly declared in
  `aws_api_gateway.tf`
- most methods integrate to the single `query` Lambda
- custom-domain mapping is API Gateway specific in `aws_route53.tf`
- ZIP packaging and Lambda env wiring live in `aws_lambda.tf`

### Test coupling

The current suite depends heavily on direct Lambda handler invocation:

- many tests import `infrastructure.lambda_query`
- many tests call `handler(event, None)` with API Gateway-shaped fixtures

This is a migration concern, not just a test detail. Follow-on phases should
preserve contract-level behavior while reducing direct dependency on API Gateway
event shapes.

### Existing ECS patterns to reuse

The repo already has ECS/Fargate conventions through the monthly ingest worker:

- ECR repository pattern
- ECS task definition pattern
- CloudWatch log-group pattern
- task execution/task role split

The API ECS implementation should extend those conventions rather than invent a
separate container stack style.

## Target ECS Architecture

### API service shape

- one ECS Fargate service for the initial API migration
- one ALB target group for the API service
- ACM certificate terminated at the ALB listener
- Route53 alias updated from API Gateway to ALB during cutover
- containerized Python app exposing HTTP directly

### Networking and security

- ALB in public subnets
- ECS tasks in private subnets
- awsvpc networking
- dedicated API task security group
- dedicated ALB security group
- task egress scoped to:
  - PostgreSQL / RDS
  - AWS service endpoints needed by the app
  - other explicitly required integrations

### Config and secrets

- keep the current env-var contract as the primary runtime surface during
  migration
- inject secrets through ECS task definition secrets integration
- reuse existing PostgreSQL and other secret-backed config shapes rather than
  introducing a second config model

### Health, startup, and observability

Follow-on implementation should add:

- `/health` for process liveness
- `/ready` for ALB readiness checks
- CloudWatch task logs
- ALB target-group health checks
- baseline alarms for task health and load balancer failures

Readiness should remain lightweight. It should confirm the app can serve
traffic without turning every health probe into a full dependency sweep.

### Scaling defaults

- start with one ECS service and pragmatic autoscaling
- do not split the API into multiple services in the first runtime migration
- use CPU, memory, and request-driven scaling only where clearly justified

## Phased Migration Sequence

### Phase 25B: Container compatibility app

- add a real FastAPI/ASGI app boundary
- keep it as a compatibility wrapper over `lambda_query` rather than a full
  route rewrite
- add `/health` and `/ready` endpoints for container runtime checks
- add Docker packaging for local and ECS-style execution
- keep Lambda as a supported transport temporarily

### Phase 25C: Continue extracting the application boundary

- carve routing and service composition out of `lambda_query.py`
- introduce a real ASGI-capable app factory and entrypoint
- keep Lambda as a compatibility adapter over the same core app
- begin shifting tests toward request-contract coverage

### Phase 25C: Containerize the API

- add an API Dockerfile
- add container startup and local run instructions
- preserve the current runtime env-var contract

### Phase 25D: Controlled cutover

- validate response parity between Lambda and ECS
- move public ingress from API Gateway custom domain to ALB
- keep rollback ready by preserving Lambda/API Gateway until parity is proven

### Phase 25F: Cleanup

- remove obsolete API Gateway and API-serving Lambda resources only after
  production validation
- keep serverless/event-driven runtimes that still fit their workloads

## Runtime Split and Non-Goals

This pivot does not force every compute path into ECS immediately.

Keep these paths separate for now:

- scheduled ingestion triggers
- Step Functions orchestration
- monthly ingest ECS worker workflow
- background or batch handlers that are not synchronous HTTP ingress

Webhook routes are different: because they are part of the HTTP ingress surface,
they should move with the API service even if other event-driven compute remains
serverless.

## Cutover and Rollback Guidance

Recommended cutover order:

1. extract and validate the shared application boundary
2. containerize and run locally
3. deploy ECS service behind ALB in parallel
4. validate route, auth, CORS, and webhook parity
5. move Route53/custom-domain ingress to ALB
6. keep Lambda/API Gateway as a deprecated rollback target until ECS stability
   is proven

Rollback rule:

- ingress cutover should be reversible without changing application contracts
- the API Gateway + Lambda path should remain deployable until ECS parity and
  monitoring confidence are established

## Testing Expectations for Follow-On Phases

Follow-on implementation should explicitly cover:

- response-contract parity between Lambda and ECS/ASGI for core routes
- auth and CORS parity
- webhook parity
- health/readiness behavior under ALB
- Terraform validation for ALB/ECS/Route53 changes
- a smaller retained Lambda adapter suite during the transition
- longer-term shift toward HTTP/ASGI client tests as the primary runtime tests
