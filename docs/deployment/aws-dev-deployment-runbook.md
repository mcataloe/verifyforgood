<!--
LEAP_DOC_METADATA:
  audience: maintainer, operator, agent, contributor
  doc_type: operational-runbook
  authority: supporting
  applies_to: verifyforgood-dev-aws
END_LEAP_DOC_METADATA
-->

# VerifyForGood AWS Dev Deployment Runbook

Status: Draft / target-state operational runbook  
Owner / approver: Project owner  
Environment: `dev` only  
Primary hostname: `dev.verifyforgood.com`  
AWS region: `us-east-1` under the current Terraform/backend configuration

## Purpose

This runbook defines the intended step-by-step procedure for deploying VerifyForGood to the AWS Dev environment.

It covers:

- one-time AWS/Terraform bootstrap checks
- Terraform remote state
- Route53 and TLS prerequisites
- Dev configuration and secrets
- container image build and publication to ECR
- ECS Fargate deployment
- PostgreSQL migration sequencing
- GitHub Actions/OIDC deployment expectations
- post-deployment verification
- rollback and troubleshooting

This runbook is deliberately limited to Dev. Do not use it to create `test`, `stage`, or production resources.

Production naming is also explicitly out of scope here except for one invariant: the future production hostname is `www.verifyforgood.com`, **not** `prod.verifyforgood.com`.

## Read This Before Deploying

The current repository does **not yet implement every target-state prerequisite described by this runbook**. The infrastructure Delivery Unit must reconcile the items in the next section before this document can be treated as fully executable.

Do not silently improvise around a blocked step. If a required resource, migration path, credential path, or network dependency is missing, stop and resolve the infrastructure gap first.

## Current Repository Gaps That Must Be Reconciled

As of the current `main` branch inspected when this runbook was created:

| Area | Current repository state | Required Dev state |
|---|---|---|
| Dev DNS | `terraform.shared.tfvars` still sets `root_domain_name = "charitystatusapi.com"` and `route53_zone_name = "charitystatusapi.com."` | `verifyforgood.com` hosted zone and `dev.verifyforgood.com` Dev hostname |
| Dev CORS | `terraform-dev.tfvars` still includes `https://dev.charitystatusapi.com` | include `https://dev.verifyforgood.com` |
| Production DNS logic | `aws_route53.tf` currently maps `prod` to the base/root domain | future production must map to `www.verifyforgood.com`; do not create production from the current logic |
| GitHub Actions | no `.github/workflows/` directory is currently present | GitHub Actions validation/security/deploy workflows using AWS OIDC |
| Historical GitLab CI | `.gitlab-ci.yml` is commented out | reference only; it is not an active deployment path |
| Terraform version | `providers.tf` requires Terraform `>= 1.14.6` | deployment tooling must meet that requirement |
| Historical CI Terraform version | commented GitLab scaffold references Terraform `1.9.8` | do not copy that version into the GitHub Actions implementation |
| VPC/networking | current ECS/RDS variables expect VPC/subnet IDs to be supplied | infrastructure DU must establish the approved Dev network design and wire those values/resources |
| API runtime | shared tfvars currently set `api_ecs_enabled = false` | Dev runtime must explicitly enable the ECS API when ready |
| PostgreSQL | shared tfvars currently set `platform_postgres_enabled = false` | enable only after the Dev RDS and migration path are ready |
| DB migration execution | repository documents Alembic migration order but no verified private-RDS deployment migration task was found | provide an approved migration execution path from inside the Dev network before starting the API against RDS |
| Load testing | not active | workflow may be scaffolded, but must remain disabled/manual until explicitly approved |

## Target Dev Architecture

The Dev deployment target is:

```text
Internet
  |
Route53: dev.verifyforgood.com
  |
ACM TLS certificate
  |
Public Application Load Balancer
  |
Private ECS Fargate API tasks
  |
Private application/data services
  |-- Amazon RDS for PostgreSQL
  |-- S3
  |-- Athena / Glue where applicable
  |-- AWS Bedrock integration when implemented
```

Infrastructure should remain flat Terraform unless the project owner explicitly approves a module-based exception.

The Dev design should keep application compute and databases private. S3 and DynamoDB should use Gateway VPC endpoints where applicable. Interface endpoints should be added selectively when the isolation or NAT-avoidance benefit justifies their hourly/data-processing cost.

Customer-upload S3 storage may be provisioned as part of the infrastructure DU, but document-to-tenant/user partitioning semantics are not defined by this runbook and must not be invented here.

## 1. Operator Prerequisites

Before running Terraform or changing AWS, verify the workstation or CI runner has:

- Git
- Docker
- AWS CLI v2
- Terraform `>= 1.14.6`
- Python/backend tooling required for repository migration commands when migrations are executed from an approved runtime

Check versions:

```bash
aws --version
terraform version
docker --version
git --version
```

The Terraform version requirement comes from `infrastructure/providers.tf` and must not be lowered merely to match the historical GitLab scaffold.

## 2. Confirm the AWS Account and Region

Authenticate using the approved operator identity or, in GitHub Actions, the approved OIDC-assumed role.

Run:

```bash
aws sts get-caller-identity
aws configure get region
```

Confirm all of the following before continuing:

- the AWS account is the intended VerifyForGood Dev account
- the operator is authorized to deploy Dev
- the region is `us-east-1` unless the infrastructure DU has deliberately changed and reconciled the repository configuration
- no production account/session is active

**STOP** if the account or region is not the intended Dev target.

## 3. Verify the Route53 Hosted Zone

The target public hosted zone is `verifyforgood.com`.

Verify it is visible to the deployment identity:

```bash
aws route53 list-hosted-zones-by-name \
  --dns-name verifyforgood.com \
  --max-items 1
```

Confirm the returned zone is the correct public hosted zone.

The current Terraform custom-domain implementation computes non-production hostnames as:

```text
<environment>.<base-domain>
```

Therefore, after the base-domain variables are reconciled to `verifyforgood.com`, the Dev hostname becomes:

```text
dev.verifyforgood.com
```

Do not continue with `charitystatusapi.com` values for the new VerifyForGood Dev deployment unless the project owner explicitly authorizes a temporary compatibility deployment.

## 4. Verify Terraform Remote State

The current Dev backend remains intentionally pinned to legacy resource names:

```text
S3 bucket:      charitystatusapi-dev
State key:      terraform/terraform.tfstate
Region:         us-east-1
DynamoDB table: charitystatusapi-dev
```

These names are deployment-state identifiers and must not be renamed casually as part of product branding.

Verify the backend resources exist:

```bash
aws s3api head-bucket \
  --bucket charitystatusapi-dev

aws dynamodb describe-table \
  --table-name charitystatusapi-dev \
  --region us-east-1
```

If either backend resource is missing, **STOP**. The repository currently does not provide a verified backend-bootstrap script. Do not create a differently named state backend or rewrite `backend-dev.hcl` ad hoc.

If a backend bootstrap is implemented later, it must at minimum preserve private S3 access, state versioning, encryption, and the locking contract expected by the configured Terraform backend.

## 5. Check Out the Exact Revision to Deploy

From the repository root:

```bash
git status
git rev-parse --show-toplevel
git rev-parse HEAD
```

The working tree should be clean for a normal deployment.

Capture the immutable image tag:

```bash
export RUNTIME_IMAGE_TAG="$(git rev-parse HEAD)"
echo "$RUNTIME_IMAGE_TAG"
```

Do not use `latest` for an intentional Dev release. Container images should be tagged with the exact Git commit SHA so the deployment is reproducible and rollback is possible.

## 6. Prepare Dev Terraform Configuration

The deployment uses:

```text
infrastructure/backend-dev.hcl
infrastructure/terraform.shared.tfvars
infrastructure/terraform-dev.tfvars
infrastructure/terraform-dev.secrets.tfvars
```

`terraform-dev.secrets.tfvars` is local/CI-generated and must not be committed. The repository `.gitignore` ignores ordinary `*.tfvars` files while explicitly allowing the committed shared/dev/prod tfvars files.

Before the first VerifyForGood Dev deployment, verify the committed configuration has been reconciled to at least these DNS expectations:

```hcl
# terraform.shared.tfvars
root_domain_name  = "verifyforgood.com"
route53_zone_name = "verifyforgood.com."
domain            = "verifyforgood.com"
```

And Dev CORS must include:

```hcl
# terraform-dev.tfvars
cors_allowed_origins = [
  # local development origins as approved
  "https://dev.verifyforgood.com",
]
```

Do not put credentials, API keys, tokens, passwords, or private key material into the committed tfvars files.

Use Secrets Manager/approved secret references for ECS runtime secrets where Terraform supports `api_ecs_secret_arns` and related secret mappings.

## 7. Initialize and Validate Terraform

From the repository root:

```bash
terraform -chdir=infrastructure init \
  -reconfigure \
  -backend-config=backend-dev.hcl

terraform -chdir=infrastructure fmt -check
terraform -chdir=infrastructure validate
```

If initialization points at a different backend than `backend-dev.hcl`, stop.

If validation fails, fix the configuration before planning or applying.

## 8. Review the First Dev Infrastructure Plan

The first infrastructure plan must establish the Dev infrastructure required to host the API while avoiding an attempt to run an image that has not yet been published.

The infrastructure DU should support a bootstrap sequence in which the ECS service can remain at zero desired tasks until the first immutable image has been pushed.

Target bootstrap behavior:

- create/reconcile the Dev VPC and approved public/private subnet topology
- create approved VPC endpoints
- create/reconcile ECR repositories
- create/reconcile private RDS PostgreSQL if it is enabled for this DU
- create ECS cluster/task/service wiring
- keep API desired count at `0` until image publication and migrations are complete
- create ALB/ACM/Route53 only when the DNS values are `verifyforgood.com` / `dev.verifyforgood.com`
- do not create test/stage/prod resources

Generate a plan using the Dev files:

```bash
terraform -chdir=infrastructure plan \
  -out=tfplan-dev-bootstrap \
  -var-file=terraform.shared.tfvars \
  -var-file=terraform-dev.tfvars \
  -var-file=terraform-dev.secrets.tfvars \
  -var="api_ecs_image_tag=$RUNTIME_IMAGE_TAG" \
  -var="worker_ecs_image_tag=$RUNTIME_IMAGE_TAG" \
  -var="monthly_ingest_worker_image_tag=$RUNTIME_IMAGE_TAG"
```

Review the plan before applying it.

**STOP** if the plan proposes any unexpected deletion/replacement of stateful resources, production resources, IAM trust broadening, public database exposure, or a domain outside the approved Dev target.

Apply only the reviewed plan:

```bash
terraform -chdir=infrastructure apply tfplan-dev-bootstrap
```

## 9. Read the Managed ECR Repository URLs

After the ECR repositories exist in Terraform state:

```bash
export API_ECR_REPOSITORY_URL="$(terraform -chdir=infrastructure output -raw api_ecr_repository_url)"
export WORKER_ECR_REPOSITORY_URL="$(terraform -chdir=infrastructure output -raw worker_ecr_repository_url)"
export INGEST_TASK_ECR_REPOSITORY_URL="$(terraform -chdir=infrastructure output -raw monthly_ingest_worker_ecr_repository_url)"

printf '%s\n' "$API_ECR_REPOSITORY_URL"
printf '%s\n' "$WORKER_ECR_REPOSITORY_URL"
printf '%s\n' "$INGEST_TASK_ECR_REPOSITORY_URL"
```

The worker image is only operationally required when `worker_ecs_enabled=true`. The API and federal-ingest image contracts remain separate.

## 10. Build the Runtime Images

Run Docker builds from the repository root because the historical pipeline and Dockerfiles expect the repository root as build context.

API:

```bash
docker build \
  -f backend/customer-api/Dockerfile \
  -t "backend-api:$RUNTIME_IMAGE_TAG" \
  .
```

Federal ingest task:

```bash
docker build \
  -f backend/ingest/federal/Dockerfile \
  -t "backend-ingest-task:$RUNTIME_IMAGE_TAG" \
  .
```

Build the general worker only if the Dev deployment enables that service:

```bash
docker build \
  -f backend/worker/Dockerfile \
  -t "backend-worker:$RUNTIME_IMAGE_TAG" \
  .
```

## 11. Authenticate Docker to ECR

Derive the ECR registry host from the API repository URL:

```bash
export ECR_REGISTRY_HOST="$(echo "$API_ECR_REPOSITORY_URL" | cut -d/ -f1)"

aws ecr get-login-password \
  --region us-east-1 \
| docker login \
  --username AWS \
  --password-stdin "$ECR_REGISTRY_HOST"
```

Use AWS CLI v2 for deployment tooling.

## 12. Tag and Push Immutable Images

API:

```bash
docker tag \
  "backend-api:$RUNTIME_IMAGE_TAG" \
  "$API_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"

docker push \
  "$API_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"
```

Federal ingest:

```bash
docker tag \
  "backend-ingest-task:$RUNTIME_IMAGE_TAG" \
  "$INGEST_TASK_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"

docker push \
  "$INGEST_TASK_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"
```

Worker, when enabled:

```bash
docker tag \
  "backend-worker:$RUNTIME_IMAGE_TAG" \
  "$WORKER_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"

docker push \
  "$WORKER_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"
```

Verify the expected SHA tag exists in each required repository before continuing.

## 13. Run PostgreSQL Migrations Before Starting the API

When `platform_postgres_enabled=true`, schema migration must complete before the API is scaled above zero.

The repository identifies Alembic as the schema source of truth and documents this rollout order at a high level:

1. apply the schema migration (`alembic upgrade head`)
2. run the customer-account migration dry run when that migration is applicable
3. run the real customer-account migration when approved
4. deploy PostgreSQL runtime wiring
5. recreate/reseed Dev-only data when needed

However, RDS is intended to remain private. A workstation on the public Internet should not be given direct database ingress merely to run migrations.

**BLOCKED UNTIL INFRASTRUCTURE DU PROVIDES AN APPROVED EXECUTION PATH:** use a one-off ECS migration task, SSM-connected operator path, or another approved private-network mechanism. Do not open RDS publicly as a shortcut.

For detailed PostgreSQL cutover behavior, use `docs/implementation/postgresql-cutover-runbook.md` and the backend migration documentation. Do not automatically downgrade a database as part of an application rollback unless the migration has been explicitly designed and approved as reversible.

## 14. Create the Final Runtime Plan

After:

- the approved infrastructure exists
- the immutable images are present in ECR
- required database migrations have succeeded
- runtime secrets are available

create the final Dev plan with the exact SHA tag:

```bash
terraform -chdir=infrastructure plan \
  -out=tfplan-dev-runtime \
  -var-file=terraform.shared.tfvars \
  -var-file=terraform-dev.tfvars \
  -var-file=terraform-dev.secrets.tfvars \
  -var="api_ecs_image_tag=$RUNTIME_IMAGE_TAG" \
  -var="worker_ecs_image_tag=$RUNTIME_IMAGE_TAG" \
  -var="monthly_ingest_worker_image_tag=$RUNTIME_IMAGE_TAG"
```

Review the plan.

For the API service, the final desired count should be the approved Dev value (currently expected to be `1` unless the infrastructure DU deliberately changes it).

Apply the reviewed plan:

```bash
terraform -chdir=infrastructure apply tfplan-dev-runtime
```

## 15. Verify ECS Deployment Health

Read the Terraform outputs:

```bash
terraform -chdir=infrastructure output api_ecs_cluster_name
terraform -chdir=infrastructure output api_ecs_service_name
terraform -chdir=infrastructure output api_alb_dns_name
terraform -chdir=infrastructure output api_ecs_task_log_group_name
```

Wait for ECS service stability using the resolved cluster/service names:

```bash
aws ecs wait services-stable \
  --cluster "$(terraform -chdir=infrastructure output -raw api_ecs_cluster_name)" \
  --services "$(terraform -chdir=infrastructure output -raw api_ecs_service_name)" \
  --region us-east-1
```

Inspect target health:

```bash
aws elbv2 describe-target-health \
  --target-group-arn "$(terraform -chdir=infrastructure output -raw api_alb_target_group_arn)" \
  --region us-east-1
```

All active Dev API targets should become healthy.

## 16. Verify DNS, TLS, and API Readiness

Confirm the DNS name resolves:

```bash
nslookup dev.verifyforgood.com
```

Check the API readiness endpoint:

```bash
curl --fail --show-error --silent \
  https://dev.verifyforgood.com/ready
```

Expected result:

- DNS resolves to the ALB path managed by Route53
- HTTPS certificate is valid for `dev.verifyforgood.com`
- `/ready` returns an HTTP success response matching the configured ALB health-check matcher
- ECS service has the expected running task count

Do not declare the deployment successful based only on `terraform apply` succeeding.

## 17. Review CloudWatch Logs

Tail the API task log group:

```bash
aws logs tail \
  "$(terraform -chdir=infrastructure output -raw api_ecs_task_log_group_name)" \
  --since 15m \
  --region us-east-1
```

Look for:

- startup failures
- missing secrets/configuration
- database connectivity failures
- migration/schema mismatch
- outbound-network failures
- Bedrock/S3 permission failures when those integrations are enabled

## 18. Dev Deployment Acceptance Checklist

A Dev deployment is successful only when all applicable checks pass:

- Terraform initialized against `backend-dev.hcl`
- plan contains only intended Dev changes
- no test/stage/prod resources were created
- Dev resources are in the intended AWS account and `us-east-1`
- `dev.verifyforgood.com` resolves correctly
- ACM certificate is valid
- ALB target health is healthy
- API `/ready` returns success
- ECS API tasks run in private subnets without public IP assignment
- RDS is not publicly accessible
- secrets are not stored in committed tfvars or workflow source
- deployed image tag is the exact Git commit SHA, not `latest`
- required ECR/container/security scans pass once the GitHub security pipeline is implemented
- database migration completed successfully when PostgreSQL changes are involved
- CloudWatch logs do not show deployment-blocking errors
- load testing remains disabled/manual until separately approved

## 19. Normal GitHub Actions Deployment Target

The target steady-state deployment path is GitHub Actions, not the commented GitLab pipeline.

AWS authentication should use GitHub OIDC and short-lived AWS credentials. Do not store long-lived AWS access keys in GitHub when OIDC is available.

The AWS IAM trust policy must restrict the GitHub OIDC subject to the intended repository and deployment context rather than trusting arbitrary repositories/branches.

Target Dev workflow behavior:

### Pull request

Run without deploying:

- backend/frontend lint and tests as applicable
- Terraform `fmt -check`
- Terraform `init -backend=false`
- Terraform `validate`
- SAST / CodeQL where applicable
- dependency/SCA checks
- secret scanning / push protection at repository level where configured
- IaC security scan
- container build verification and container scanning
- Terraform plan only when the credential and environment design permits it safely

### Merge to `main`

Target sequence:

1. authenticate to AWS using OIDC
2. capture the merge commit SHA as the immutable runtime image tag
3. initialize Terraform against `backend-dev.hcl`
4. build required runtime images
5. publish the SHA-tagged images to Terraform-managed ECR repositories
6. create/review the Dev Terraform plan
7. apply the Dev plan according to the approved Dev deployment-approval policy
8. run the approved database migration task when required
9. wait for ECS service stability
10. run Dev readiness/smoke checks
11. surface deployment result and relevant Terraform/ECS outputs

Until the project owner explicitly chooses automatic Dev apply-on-merge, treat the Terraform apply as requiring a manual GitHub Environment approval or equivalent manual deployment action.

### Load testing

A load-test workflow may be committed as scaffolding, but it must remain `workflow_dispatch`/manual or otherwise disabled from ordinary CI. Do not activate automated load generation until the project owner explicitly approves it closer to production readiness.

## 20. Rollback

### Application-image rollback

Preferred Dev application rollback is to redeploy a previously known-good immutable Git SHA tag through Terraform.

1. identify the previous known-good image SHA
2. create a Terraform plan with the previous `api_ecs_image_tag` (and other image tags if required)
3. review the plan
4. apply the plan
5. wait for ECS service stability
6. rerun `/ready` and smoke checks

Do not retag `latest` to simulate rollback.

### Infrastructure rollback

Do not automatically reverse Terraform changes that affect:

- RDS/data durability
- S3 data
- Route53 ownership
- IAM trust/policies
- encryption
- secrets
- Terraform state

Review the prior plan/state and obtain explicit approval before any destructive infrastructure rollback.

### Database rollback

Application rollback and schema rollback are separate decisions. Do not run an Alembic downgrade automatically. Use the PostgreSQL cutover/migration documentation and only downgrade when the specific migration is known to be reversible and the project owner has approved the action.

## 21. Troubleshooting

### Terraform backend initialization fails

Check:

```bash
cat infrastructure/backend-dev.hcl
aws s3api head-bucket --bucket charitystatusapi-dev
aws dynamodb describe-table --table-name charitystatusapi-dev --region us-east-1
```

Do not switch to local state as a workaround for a shared Dev deployment.

### ECR push fails

Re-authenticate:

```bash
aws ecr get-login-password \
  --region us-east-1 \
| docker login \
  --username AWS \
  --password-stdin "$ECR_REGISTRY_HOST"
```

Then verify the deployment identity has the intended ECR permissions.

### ECS service does not stabilize

Inspect:

```bash
aws ecs describe-services \
  --cluster "$(terraform -chdir=infrastructure output -raw api_ecs_cluster_name)" \
  --services "$(terraform -chdir=infrastructure output -raw api_ecs_service_name)" \
  --region us-east-1
```

Then inspect target health and CloudWatch logs.

### `dev.verifyforgood.com` does not resolve

Verify:

- Terraform is using `verifyforgood.com`, not `charitystatusapi.com`
- `enable_custom_domain=true`
- the correct public Route53 zone was selected
- ACM DNS validation succeeded
- the Route53 alias points to the Dev ALB

### API cannot reach PostgreSQL

Verify:

- RDS is private
- API task and RDS security groups permit only the required path/port
- secret ARN/database configuration is correct
- migrations completed
- the task is in the intended private subnets

Do not make RDS public to solve a connectivity problem.

### API cannot reach external services

The final Dev egress design must be explicit. Check whether the required dependency is reachable through a VPC endpoint or requires controlled Internet egress. Do not assume that adding more interface endpoints always reduces cost.

## 22. Stop Conditions

Stop the deployment and escalate/reconcile before applying when any of these occur:

- AWS identity points at the wrong account or environment
- Terraform backend differs from the approved Dev backend
- plan proposes deletion/replacement of stateful resources unexpectedly
- plan contains production/test/stage resources
- Route53 zone or certificate is for the wrong domain
- Terraform would make RDS publicly accessible unexpectedly
- a required secret would be committed or printed into logs
- GitHub OIDC trust is broader than the intended repository/environment
- image tag is mutable or ambiguous (`latest`)
- private-RDS migration execution is not available for a schema-dependent release
- deployment requires a security shortcut or unapproved paid service
- a database/data migration is destructive and has not been explicitly authorized

## 23. Open Infrastructure Decisions Before This Runbook Becomes Fully Executable

The infrastructure DU should resolve and then reconcile this document for:

1. exact AWS account separation strategy for Dev versus future environments
2. final Dev VPC CIDR/AZ/subnet allocation and outbound Internet-egress design
3. exact cost-aware set of permanent versus ephemeral VPC interface endpoints
4. approved private-network database migration execution mechanism
5. final Bedrock/RAG infrastructure boundary for this DU
6. exact GitHub OIDC deploy-role permissions and trust conditions
7. whether Dev Terraform apply is automatic on merge or requires manual approval; until decided, default to manual approval
8. frontend hosting/entry-point routing if `dev.verifyforgood.com` is intended to front more than the API
9. customer-upload S3 partitioning/tenancy semantics; do not implement these semantics until defined

## Related Repository Sources

- `AGENTS.md`
- `docs/00_start_here.md`
- `docs/implementation/postgresql-cutover-runbook.md`
- `infrastructure/README.md`
- `infrastructure/backend-dev.hcl`
- `infrastructure/providers.tf`
- `infrastructure/terraform.shared.tfvars`
- `infrastructure/terraform-dev.tfvars`
- `infrastructure/terraform.shared.tfvars.example`
- `infrastructure/terraform-dev.tfvars.example`
- `infrastructure/aws_api_ecs.tf`
- `infrastructure/aws_route53.tf`
- `infrastructure/outputs.tf`
- `.gitlab-ci.yml` — historical/commented reference only

## External Operational References

Use the current official documentation when implementing the corresponding workflow:

- GitHub Docs: Configuring OpenID Connect in Amazon Web Services
- AWS IAM: GitHub Actions OIDC role/trust configuration
- AWS CLI / Amazon ECR: `get-login-password` and pushing images to ECR

This runbook should be reconciled again when the AWS Dev infrastructure and GitHub Actions implementation are merged. At that point, remove resolved `BLOCKED` notes, replace target-state language with verified commands, and record the last verified deployment revision/date.
