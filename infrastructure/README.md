# Infrastructure Directory Boundary

Current role:

- this directory still contains both deployment assets and active Python runtime code
- Terraform, env files, Lambda entrypoints, and the current `verification` implementation all still live here today
- Terraform resource names are centralized in `main.tf` locals and can opt into the standardized `<namespace>-<platform>-<purpose>-<environment>-<region>` pattern without forcing immediate renames of deployed infrastructure

Target role:

- deployment/config/wiring only
- future long-term contents should converge on:
  - `terraform/`
  - `env/`
  - `scripts/`
  - `lambda_shims/`

Allowed contents in the target state:

- Terraform modules and environment configuration
- packaging scripts
- thin deployment-time handler shims when needed for compatibility

Forbidden contents in the target state:

- reusable domain/business logic
- long-lived platform service implementations
- proprietary platform adapters outside temporary compatibility shims

Dependency direction:

- `infrastructure/` may package and deploy runtime entrypoints
- application/domain code must not depend on deployment-only modules from `infrastructure/`

Migration note:

- this boundary is documented now so later refactors can move code out incrementally without breaking current deployment assumptions
- `backend/` now provides the first-class Python runtime workspace layer; `infrastructure/` should keep packaging or deploy-time references pointed there as extraction phases proceed
- naming is decoupled from product branding so infrastructure identity does not have to change when customer-facing names do
- the monthly private-ingest architecture and operations docs live in `docs/monthly-ingest-architecture.md` and `docs/monthly-ingest-runbook.md`

## PostgreSQL Foundation

Terraform now supports additive Amazon RDS for PostgreSQL provisioning for the
platform/application relational pivot.

Current assumptions:

- RDS is provisioned only when `platform_postgres_enabled=true`
- the initial target instance class is `db.t4g.micro`
- RDS is placed into existing private subnets supplied through Terraform vars
- the query Lambda is VPC-attached when PostgreSQL is enabled so later
  repository phases can connect without another network bootstrap
- PostgreSQL is the only supported runtime backend for customer accounts,
  organization settings, and control-plane/billing storage
- the materialized nonprofit DynamoDB profile cache has been retired from the
  runtime and Terraform no longer provisions those tables or env vars

Minimum Terraform inputs when enabling PostgreSQL:

- `platform_postgres_vpc_id`
- `platform_postgres_private_subnet_ids`
- `platform_postgres_database_name`
- either:
  - let Terraform manage the secret with `platform_postgres_username`, or
  - supply `platform_postgres_existing_secret_arn`

Runtime env wiring added for the query Lambda:

- `PLATFORM_POSTGRES_ENABLED`
- `PLATFORM_POSTGRES_SECRET_ARN`
- `PLATFORM_POSTGRES_HOST`
- `PLATFORM_POSTGRES_PORT`
- `PLATFORM_POSTGRES_DATABASE`
- `PLATFORM_POSTGRES_SSLMODE`
- `PLATFORM_NONPROFIT_STORE_BACKEND` for nonprofit ingest and Form 990 writes
- optional dedicated nonprofit data-plane overrides:
  - `PLATFORM_NONPROFIT_POSTGRES_ENABLED`
  - `PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN`
  - `PLATFORM_NONPROFIT_POSTGRES_HOST`
  - `PLATFORM_NONPROFIT_POSTGRES_PORT`
  - `PLATFORM_NONPROFIT_POSTGRES_DATABASE`
  - `PLATFORM_NONPROFIT_POSTGRES_SSLMODE`
- `PLATFORM_NONPROFIT_QUERY_BACKEND` for nonprofit lookup/search/filings reads

For local backend development, prefer the backend-owned workflow instead of the
deployed secret-backed wiring:

- copy `backend/.env.local.example` to `backend/.env.local`
- set `PLATFORM_POSTGRES_URL` to a direct local PostgreSQL endpoint
- set `PLATFORM_NONPROFIT_POSTGRES_URL` only when nonprofit and Form 990 data should live on a separate database
- run `python -m verification_backend.shared.local_dev db-upgrade`
- run `python -m verification_backend.shared.local_dev db-upgrade-nonprofit` when a separate nonprofit database is configured
- use `python -m verification_backend.shared.local_dev db-reset-nonprofit` for a destructive nonprofit-only dev reset
- use `python -m verification_backend.shared.local_dev db-cutover-nonprofit` to destructively copy nonprofit/Form 990 rows out of the shared platform database during cutover
- run `python -m verification_backend.api.entrypoint`

PostgreSQL-only rollout order:

1. run `alembic upgrade head`
2. run `python -m verification_platform.runtime.customer_accounts_migration --identity-table-name identity --dry-run`
3. run `python -m verification_platform.runtime.customer_accounts_migration --identity-table-name identity`
4. deploy with PostgreSQL runtime env wiring only
5. recreate or reseed any dev-only data that previously lived in DynamoDB

## ECS Runtime Mapping

The Terraform stack now maps the backend runtime directories onto explicit ECS
deployment roles:

- `backend/api`
  - live ALB-backed ECS Fargate service
- `backend/worker`
  - provisionable ECS Fargate service slot for the future general worker
    runtime; disabled by default until runtime extraction lands
- `backend/ingest-task`
  - ECS task-style runtime used by scheduled and one-off ingest execution

Phase 25C/25D added the live API service cutover. Phase 27C extends that
mapping so the worker service boundary is provisionable and the shared ECS
cluster is explicitly treated as the backend service cluster rather than an
API-only concern.

Current deployment posture:

- Route53 now points the primary API hostname at the public ALB
- the ECS API tasks run in private subnets behind that ALB and are the primary
  HTTP runtime
- the API and worker services now share one backend ECS cluster
- the worker service has no ALB and stays in private subnets only
- the worker service defaults to a placeholder, zero-scale deployment contract
- API Gateway and the query Lambda remain deployable only as a deprecated
  rollback stack
- the Terraform stack now manages the ECS cluster, API task definition, ECS
  service, API ECR repository, ALB target group, and API task log group
- the Terraform stack can also manage a worker ECR repository, task
  definition, service, task role, and task log group when
  `worker_ecs_enabled=true`
- PostgreSQL ingress includes the ECS API task security group when
  `platform_postgres_enabled=true`; the worker task security group is also
  allowed when the worker service is enabled
- container ownership now lives under `backend/api/Dockerfile` and
  `backend/ingest-task/Dockerfile`; infrastructure consumes image URIs and ECS
  task definitions rather than owning the runtime Dockerfiles

Required environment inputs when `api_ecs_enabled=true`:

- `api_ecs_vpc_id`
- `api_ecs_public_subnet_ids`
- `api_ecs_private_subnet_ids`
- either:
  - `api_ecs_image_uri`, or
  - the managed API ECR repository plus `api_ecs_image_tag`
- either:
  - `api_alb_certificate_arn`, or
  - `enable_custom_domain=true` with the managed ACM certificate flow

Sensitive API runtime values can stay out of plaintext Terraform by mapping env
var names to secret references with `api_ecs_secret_arns`. This is the intended
path for values such as `PORTAL_AUTH_TOKEN_SECRET` and any other container-only
secrets that are not yet first-class Terraform variables.

Worker service inputs when `worker_ecs_enabled=true`:

- `worker_ecs_vpc_id`
- `worker_ecs_private_subnet_ids`
- either:
  - `worker_ecs_image_uri`, or
  - the managed worker ECR repository plus `worker_ecs_image_tag`
- optional sizing and rollout controls:
  - `worker_ecs_task_cpu`
  - `worker_ecs_task_memory`
  - `worker_ecs_desired_count`
- optional secret wiring:
  - `worker_ecs_secret_arns`
  - `worker_ecs_secret_kms_key_arns`

Worker placeholder note:

- the worker ECS service is intentionally provisionable before the runtime is
  assigned to a future non-refresh background workload
- defaulting `worker_ecs_desired_count` to `0` keeps the deployment slot
  explicit without pretending the service is production-ready

GitLab CI/CD rollout baseline:

- `.gitlab-ci.yml` builds `backend/api`, `backend/worker`, and
  `backend/ingest-task`
- the old `infra-deployment/` scaffold boundary has been absorbed into this
  infrastructure layer
- runtime images publish to the managed ECR repositories exposed by Terraform
  outputs
- image versioning should use immutable commit-SHA tags, not `latest`
- Terraform deploy jobs remain the source of truth for ECS rollout by passing:
  - `api_ecs_image_tag=$CI_COMMIT_SHA`
  - `worker_ecs_image_tag=$CI_COMMIT_SHA`
  - `monthly_ingest_worker_image_tag=$CI_COMMIT_SHA`
- dev deploy jobs use:
  - `backend-dev.hcl`
  - `terraform.shared.tfvars`
  - `terraform-dev.tfvars`
  - CI-provided `terraform-dev.secrets.tfvars` content
- prod deploy jobs use:
  - `backend-prod.hcl`
  - `terraform.shared.tfvars`
  - `terraform-prod.tfvars`
  - CI-provided `terraform-prod.secrets.tfvars` content
- `monthly_ingest_worker_image_tag` remains the current deploy-time Terraform
  variable for the `backend/ingest-task` image so the existing task definition
  contract stays backward compatible

Required CI variables:

- AWS authentication variables understood by the AWS CLI and Terraform provider
- `TERRAFORM_DEV_SECRETS_TFVARS`
- `TERRAFORM_PROD_SECRETS_TFVARS`

Bootstrap note:

- the managed ECR repositories must exist in Terraform state before CI publish
  jobs can push images
- this phase keeps repository creation in Terraform instead of creating ECR
  repositories ad hoc from CI

Rollback note:

- the deprecated API Gateway custom-domain and query Lambda packaging remain in
  Terraform only so the Route53 alias can be restored quickly if the ECS cutover
  fails
- later cleanup should remove those API-serving resources once ECS stability is
  confirmed

Container build guidance:

- `backend/api/Dockerfile` is the canonical API image contract
- `backend/worker/Dockerfile` is the canonical worker-service image contract,
  even while the runtime remains scaffold-only
- `backend/ingest-task/Dockerfile` is the canonical ECS task image contract for
  monthly and Form 990 task execution
- scheduled and one-off ingest execution should keep using ECS tasks, not the
  general worker service

