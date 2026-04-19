# Contributor Naming Rules

## Purpose

Use naming that describes platform capability and responsibility without tying core internals to a product brand or repository history.

## Three Naming Layers

### Product / Brand Naming

Use product-facing names only where customers or external systems see them.

Examples:

- `VerifyForGood`
- `PUBLIC_BRAND_NAME`
- `SUPPORT_EMAIL`
- `DOMAIN`
- customer docs, billing metadata, support copy, public UI labels

Do not use product branding as the default name for internal modules, Terraform locals, workflow ids, or service labels.

### Capability / Domain Naming

Use capability-oriented names for new internal code, documentation, and infrastructure identifiers.

Examples:

- `verification_platform`
- `organization_verification`
- `nonprofit_registry`
- `filing_ingestion`
- `monthly_ingest`
- `platform_processing`
- `verification_workflow`

This is the preferred naming layer for new internal work.

### Legacy Compatibility Naming

Some historical names remain for compatibility with deployed infrastructure, existing imports, or repository history.

Examples:

- repository name `CharityStatusAPI`
- package root `verification`
- compatibility roots `charitystatusapi.*` and `CharityStatusAPI.*`
- Terraform backend/bootstrap names like `charitystatusapi-*`
- physical AWS names when `resource_name_strategy = "legacy"`

Do not add new implementation code under these legacy compatibility roots unless the file is a thin shim or alias layer.

## Rules For New Modules

- Name modules after capability and responsibility, not brand or repo identity.
- Prefer neutral terms such as `organization`, `verification`, `ingestion`, `connector`, `contract`, and `workflow`.
- Keep customer-facing/public contract terms unchanged unless the contract itself is being intentionally revised.
- If a rename would break imports or force infrastructure replacement, add a wrapper or alias first.
- Keep source-specific naming out of shared contracts unless the module is intentionally source-specific.

## Good / Avoid

Prefer:

- `verification_platform.organization_verification`
- `verification_platform.filing_ingestion`
- `monthly_ingest`
- `platform_processing`

Avoid for new internals:

- `charitystatusapi.organizations`
- `CharityStatusAPI.workflow`
- `verifyforgood_processing`
- `charity_lookup_service`

## When You Encounter Legacy Names

- `verification.*` is still a supported runtime path. Do not break it casually.
- `verification_platform.*` is the preferred neutral wrapper namespace for new internal capability-oriented seams.
- `charitystatusapi.*` and `CharityStatusAPI.*` are compatibility shims only.
- Legacy Terraform physical names remain acceptable when changing them would cause replacement or state churn.
- Document any intentionally preserved legacy name instead of silently normalizing it.

## Monthly Private-Ingest Naming Guidance

Use these terms consistently:

- workflow: `monthly private-ingest workflow`
- scheduler: `EventBridge monthly schedule`
- conductor: `Step Functions`
- staging component: `staging Lambda`
- worker: `ECS Fargate worker`
- permanent network dependency: `S3 gateway endpoint`
- ephemeral network dependencies: `ECR and CloudWatch Logs interface endpoints`

Avoid reintroducing brand-coupled internal names such as:

- `verifyforgood-monthly-job`
- `charitystatusapi-ingest-worker`

Prefer capability-oriented labels such as:

- `monthly_ingest`
- `monthly_private_ingest_staging`
- `platform_processing`

## Reference Docs

- [Capability Naming Abstraction](/c:/Repos/charity-status-api/docs/capability-naming-abstraction.md)
- [Infrastructure Naming Normalization](/c:/Repos/charity-status-api/docs/infrastructure-naming-normalization.md)
- [Monthly Ingest Workflow Architecture](/c:/Repos/charity-status-api/docs/monthly-ingest-architecture.md)
- [Monthly Ingest Runbook](/c:/Repos/charity-status-api/docs/monthly-ingest-runbook.md)

