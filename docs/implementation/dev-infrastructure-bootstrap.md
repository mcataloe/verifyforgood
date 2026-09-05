# VerifyForGood Dev Infrastructure Bootstrap

Status: implementation bootstrap for the `dev` environment only.

## Scope

This delivery unit establishes the AWS and GitHub Actions foundation for `dev` while preserving the existing ECS Fargate + ALB and PostgreSQL runtime architecture.

It intentionally does **not** create `test`, `staging`, or production infrastructure.

Future account placement remains:

- non-production AWS account: `dev`, later `test`
- production AWS account: later `staging`, production
- one VPC per environment

Production DNS is reserved as `www.verifyforgood.com`. `prod.verifyforgood.com` is not part of the naming model.

## Dev topology

`dev` uses a cost-conscious production-shaped network:

- Region: `us-east-1`
- one Terraform-managed VPC (`10.10.0.0/16`)
- two public subnets across two Availability Zones
- two private subnets across two Availability Zones
- public Application Load Balancer
- private ECS Fargate API tasks with no public IPs
- private RDS PostgreSQL
- private scheduled IRS ingest tasks
- one NAT Gateway, intentionally single-AZ for dev cost control
- one S3 Gateway VPC endpoint
- no paid interface VPC endpoints

The single NAT Gateway is a deliberate dev availability/cost tradeoff. Staging/production must re-evaluate NAT-per-AZ, interface endpoints, WAF, autoscaling, Multi-AZ database behavior, backup retention, and log retention before launch.

The S3 Gateway endpoint keeps S3 traffic off the NAT path without adding an endpoint-hour charge. Bedrock, ECR, CloudWatch, Secrets Manager, and external IRS/state traffic use normal private-subnet egress through the NAT Gateway for now.

## DNS model

The application entry point is:

- `https://dev.verifyforgood.com/`
- API traffic: `https://dev.verifyforgood.com/api/*`

The ALB listener has an explicit `/api/*` rule that rewrites `/api/<path>` to `/<path>` before forwarding to the existing ECS API target group. The listener default continues to forward to the API for backward compatibility until frontend hosting is connected.

Terraform manages a dedicated `dev.verifyforgood.com` public hosted zone. The parent `verifyforgood.com` hosted zone is deliberately **not** owned by this application stack.

### DNS bootstrap dependency

The `verifyforgood.com` domain is registered, but this implementation assumes the parent public hosted zone is created outside this stack. The dev stack references that parent zone as a data source and creates the `dev.verifyforgood.com` NS delegation record in it.

Before a full dev apply can succeed:

1. Create the public `verifyforgood.com` hosted zone in the current domain-owning AWS account.
2. Ensure the registered domain delegates to that parent hosted zone's name servers.
3. Keep `parent_route53_zone_name = "verifyforgood.com."` in dev configuration.
4. Run the dev plan/apply. Terraform will create `dev.verifyforgood.com`, publish its NS delegation into the parent zone, and validate the ACM certificate.

Moving domain/DNS ownership into a separate account is explicitly deferred. When that happens, the parent-zone delegation mechanism will need a cross-account DNS/bootstrap design rather than assuming the parent zone is writable by the environment deployment role.

## Customer document storage and Bedrock boundary

The dev stack provisions a private versioned S3 bucket for future customer uploads with:

- S3 Block Public Access
- bucket-owner-enforced ownership
- SSE-S3 encryption
- versioning
- incomplete multipart upload cleanup after seven days
- no object expiration policy yet

The application task role receives object access only when the bucket is enabled.

The following are deliberately **not** implemented yet:

- tenant-wide versus individual-user document ownership rules
- S3 key/partition contract for those ownership models
- document retention/deletion product policy
- Bedrock Knowledge Bases
- vector database/storage
- ingestion/synchronization pipelines
- retrieval authorization rules
- Bedrock PrivateLink/interface endpoints

A Bedrock runtime IAM scaffold exists but remains disabled until explicit model ARNs are selected.

## GitHub Actions delivery model

Long-lived environment branches are not used.

The source workflow is:

`feature branch -> pull request -> main`

`main` represents production-ready source. Deployment state is represented by GitHub Environments and immutable image SHAs rather than environment branches.

### Pull request / main CI

`.github/workflows/ci-security.yml` runs:

- Terraform format/init-without-backend/validate
- Python backend tests
- frontend format/lint/typecheck/test/build
- GitHub CodeQL for Python and JavaScript/TypeScript
- dependency review on pull requests
- Gitleaks secret scanning as CI defense in depth
- Trivy container scanning for HIGH/CRITICAL findings
- Trivy Terraform/IaC scanning for HIGH/CRITICAL findings

GitHub repository-native secret scanning and push protection are repository security settings, not workflow jobs. They should be enabled in addition to the CI secret-scan job.

Dependabot is configured for GitHub Actions, infrastructure Python dependencies, backend Python dependencies, and frontend npm/pnpm dependencies.

### Automatic dev deployment

`.github/workflows/deploy-dev.yml` runs only after the `CI and Security` workflow completes successfully on `main`.

The deployment:

1. uses the exact successful CI commit SHA
2. assumes the `dev` AWS role through GitHub OIDC
3. confirms the allowed AWS account ID
4. initializes the existing dev Terraform remote state
5. ensures the API and ingest ECR repositories exist
6. builds API and federal-ingest images once
7. pushes immutable `${GITHUB_SHA}` image tags
8. plans and applies dev Terraform with those SHA tags
9. waits for the ECS API service to become stable
10. smoke-tests `https://dev.verifyforgood.com/api/ready`

No static AWS access key or secret key is required by the workflow.

## One-time GitHub OIDC bootstrap

OIDC has a bootstrap dependency: GitHub cannot assume a role until that role and the account-level GitHub OIDC provider exist.

Use an already-authenticated AWS operator session once from the repository root:

```bash
terraform -chdir=infrastructure init -backend-config=backend-dev.hcl
terraform -chdir=infrastructure apply \
  -target=aws_iam_role_policy.github_dev_deploy \
  -var-file=terraform.shared.tfvars \
  -var-file=terraform-dev.tfvars
```

That targeted bootstrap creates the OIDC provider, deploy role, and inline policy through their dependency chain without requiring the full DNS/application stack to be ready.

Then configure the GitHub Environment named `dev` with these repository environment variables:

- `AWS_DEV_ACCOUNT_ID`: the non-production AWS account ID
- `AWS_DEV_DEPLOY_ROLE_ARN`: Terraform output `github_dev_deploy_role_arn`
- `DEV_DNS_BOOTSTRAPPED`: set to `true` only after the parent `verifyforgood.com` hosted zone exists and registration delegates to it

The deploy workflow intentionally fails closed when any of those values are absent or DNS is not declared bootstrapped.

If the non-production account already has a GitHub Actions OIDC provider for `token.actions.githubusercontent.com`, set `github_oidc_manage_provider = false` and provide `github_oidc_provider_arn` rather than attempting to create a duplicate provider.

## Terraform state

This delivery unit does not migrate the existing dev backend. It continues to use `backend-dev.hcl` and the legacy state bucket/lock-table names.

Backend/state migration is a separate high-risk change because it can affect infrastructure ownership and data durability.

## Load testing

`.github/workflows/load-test.yml.disabled` is intentionally not a runnable GitHub Actions workflow. GitHub will not register the file because it does not end in `.yml` or `.yaml`.

Before enabling it, explicitly approve:

- load-test tool/runtime
- target environment
- workload shape and concurrency
- duration
- pass/fail thresholds
- test data and privacy rules
- rate-limit implications
- expected AWS cost

Only then should the file be renamed to `load-test.yml` and its placeholder failure step replaced with the approved implementation.

## Known transitional compatibility

The repository previously expected VPC and subnet IDs to be supplied externally. The new network layer exposes effective managed-network locals while keeping the old variables as fallback compatibility inputs.

The existing scheduled ingest EventBridge targets are reconciled through `aws_ecs_network_override.tf` so they use the Terraform-managed private subnets and ingest security group. This is intentionally transitional because Terraform override files are harder to discover than direct resource configuration. A future cleanup should move those effective locals into `aws_ecs.tf` directly and delete the override file.

The API task's legacy `FORM990_RUN_TASK_SUBNET_IDS` environment value still originates from the legacy variable path. Scheduled ingest is wired correctly by this delivery unit; API-triggered `RunTask` networking should be reconciled with the effective-network local when the ingest trigger contract is next changed.

## Deferred environment work

Not created in this delivery unit:

- `test.verifyforgood.com` and test VPC in non-prod
- `staging.verifyforgood.com` and staging VPC in the production account
- `www.verifyforgood.com` production infrastructure
- promotion workflows for test/staging/production
- production approvals/release-tag rules
- domain/DNS account separation
- production HA/cost/security hardening
