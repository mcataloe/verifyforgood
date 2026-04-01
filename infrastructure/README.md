# Infrastructure Directory Boundary

Current role:

- this directory still contains both deployment assets and active Python runtime code
- Terraform, env files, Lambda entrypoints, and the current `charity_status` implementation all still live here today
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
- naming is decoupled from product branding so infrastructure identity does not have to change when customer-facing names do
- use `docs/contributor-naming-rules.md` for the short naming rules shared across runtime and infrastructure work
- the current normalization rules, compatibility aliases, and legacy exceptions are documented in `docs/infrastructure-naming-normalization.md`
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
- PostgreSQL is now the intended backend for the customer-account identity
  domain when the relational foundation is enabled
- DynamoDB still remains active for invitations, usage, feature flags,
  organization settings, control-plane billing, and the serving cache until
  later cutover phases

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
- per-domain backend selectors for identity, organization settings, and
  control-plane storage
- `PLATFORM_NONPROFIT_QUERY_BACKEND` for nonprofit lookup/search/filings reads

Phase 24D rollout order for the identity domain:

1. run `alembic upgrade head`
2. run `python -m charity_status_platform.runtime.customer_accounts_migration --identity-table-name identity --dry-run`
3. run `python -m charity_status_platform.runtime.customer_accounts_migration --identity-table-name identity`
4. deploy with `platform_identity_store_backend = "postgres"`
5. if rollback is needed, redeploy with `platform_identity_store_backend = "dynamodb"`

Phase 24H also adds a nonprofit migration wrapper:

- `python -m charity_status_platform.runtime.nonprofit_migration --dry-run --page-size 250 --profile-table-name profiles`

Use that wrapper to validate PostgreSQL nonprofit backfill before switching
`platform_nonprofit_query_backend` to `postgres`.

## Parallel ECS API Runtime

Phase 25C/25D adds ECS Fargate and ALB infrastructure for the backend API and
cuts the primary custom-domain ingress over to that runtime.

Current deployment posture:

- Route53 now points the primary API hostname at the public ALB
- the ECS API tasks run in private subnets behind that ALB and are the primary
  HTTP runtime
- API Gateway and the query Lambda remain deployable only as a deprecated
  rollback stack
- the Terraform stack now manages the ECS cluster, API task definition, ECS
  service, API ECR repository, ALB target group, and API task log group
- PostgreSQL ingress includes the ECS API task security group when
  `platform_postgres_enabled=true`

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

Rollback note:

- the deprecated API Gateway custom-domain and query Lambda packaging remain in
  Terraform only so the Route53 alias can be restored quickly if the ECS cutover
  fails
- later cleanup should remove those API-serving resources once ECS stability is
  confirmed
