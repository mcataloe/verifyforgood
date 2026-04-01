# ECS Runtime Pivot

## Status

accepted

## Decision

Adopt an ECS Fargate-based container runtime as the target architecture for the
primary HTTP API and migrate away from API Gateway + Lambda as the default
application-serving model in staged phases.

The target ingress model is:

- Route53-managed domain
- ACM certificate at the load-balancer layer
- Application Load Balancer
- ECS Fargate service running a containerized Python API application

This pivot applies first to the synchronous API surface currently served by
`infrastructure/lambda_query.py`. It does not require all event-driven or batch
workloads to leave Lambda immediately.

## Context

The checked-in repo is still primarily Lambda/API Gateway based:

- `infrastructure/lambda_query.py` is the main request runtime for:
  - nonprofit lookup and search
  - auth and portal identity
  - organization routes
  - billing and Stripe webhook routes
  - admin and ops routes
- `infrastructure/aws_api_gateway.tf` models a large REST API Gateway route tree
  and maps most routes to the single `query` Lambda
- `infrastructure/aws_route53.tf` binds the public domain to API Gateway
- `infrastructure/aws_lambda.tf` packages and deploys the API as a ZIP-based
  Lambda function

The repo already contains ECS/Fargate patterns, but only for worker-style
processing:

- `infrastructure/aws_ecs.tf`
- `infrastructure/Dockerfile.monthly-ingest`
- Step Functions + ECS workflow documentation for monthly ingest

There is currently no actual FastAPI or general ASGI application entrypoint
checked into the repo, despite the broader platform direction toward a
containerized backend. The first prerequisite for ECS API migration is
extracting an application boundary out of `lambda_query.py`.

## Decision Details

### First runtime target

Move the HTTP API served by `lambda_query.py` to ECS first.

This includes the current ingress-facing routes under `/v1/...`, including:

- nonprofit lookup/search routes
- portal/auth routes
- organization and billing routes
- webhook routes currently handled by the API runtime
- admin and ops HTTP routes

### Workloads intentionally not moved first

Keep these on their current event-driven or worker-oriented runtime paths until
later phases justify a change:

- `lambda_ingest.py`
- `lambda_refresh.py`
- `lambda_form990.py`
- `lambda_form990_worker.py`
- `lambda_monthly_ingest_staging.py`
- existing Step Functions + ECS monthly-ingest workflow

### Target runtime defaults

- ECS launch type: Fargate
- ingress: ALB, not API Gateway in front of ECS
- ALB in public subnets
- ECS tasks in private subnets
- security groups scoped for:
  - client -> ALB
  - ALB -> ECS
  - ECS -> PostgreSQL and other private dependencies
- config remains environment-variable driven
- secrets remain Secrets Manager backed
- CloudWatch remains the default logs/metrics destination

### Compatibility expectations

- preserve existing `/v1/...` route contracts
- preserve existing auth header and CORS behavior
- preserve existing webhook contracts
- keep the initial ECS API logically monolithic so it can match the current
  `lambda_query.py` surface without introducing service decomposition risk
- keep Lambda/API Gateway available as a rollback path until ECS parity is
  validated

## Consequences

- The next implementation phase must extract a reusable request/application
  boundary from `lambda_query.py` before containerization can happen cleanly.
- Tests must gradually pivot from direct Lambda event fixtures toward
  backend-agnostic HTTP contract coverage, while keeping a smaller Lambda
  adapter suite during transition.
- Terraform and deployment work will need to add ALB, ECS service/task
  definitions, security groups, health checks, and Route53 cutover handling.
- WAF is not currently provisioned in Terraform, so WAF support should be
  designed as a future-compatible ingress option rather than assumed as an
  existing platform feature.
