# `verification_platform` Private-Platform Package Root

Purpose:

- future canonical package root for platform-specific runtime and proprietary logic
- home for billing, auth, control-plane, ops workflows, AWS/Stripe adapters, and entrypoint orchestration

Allowed contents:

- platform billing and subscription workflows
- auth and credential integration
- control-plane and tenant/account orchestration
- AWS, Stripe, and other platform adapters
- job and handler entrypoints
- operator and customer workflow coordination

Forbidden contents:

- deterministic public-core domain logic that can live in `verification`
- deployment-only Terraform and environment files

Dependency direction:

- `verification_platform` may depend on `verification`
- `verification_platform` must not be imported by `verification`
- deployment-only code should package or invoke this layer, not live inside it

Current monorepo note:

- this directory is scaffolding only in the current phase
- the live implementation still exists primarily under `infrastructure/lambda_*.py` and `infrastructure/verification/`

Internal service-area package roots:

- `identity_access/`
- `customer_accounts/`
- `nonprofits/`
- `billing_usage/`
- `admin_operations/`
- `runtime/`
- `notifications/`

Each package is intentionally a compatibility boundary first. The current implementation still lives under the existing `verification` modules, but future portal/admin/backend work should be added under these service-area roots rather than expanding ad hoc private logic elsewhere.

