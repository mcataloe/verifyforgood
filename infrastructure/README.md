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
2. run `python -m charity_status_platform.runtime.customer_accounts_backfill --identity-table-name identity`
3. deploy with `platform_identity_store_backend = "postgres"`
4. if rollback is needed, redeploy with `platform_identity_store_backend = "dynamodb"`
