# Infrastructure Naming Normalization

## Purpose

Infrastructure naming should describe platform capability and deployment role, not historical product branding. This phase keeps deployed AWS resource identities stable while making the internal Terraform naming model easier to understand for contributors working under the `VerifyForGood` brand.

For the short cross-repo naming rules, see `docs/contributor-naming-rules.md`.

## Strategy

- canonical internal Terraform labels now prefer neutral capability names such as `organization_verification`, `regulatory_data_ingestion`, and `monthly_filing_ingestion`
- existing physical resource names still flow through the centralized `resource_names` map so environments can stay on `resource_name_strategy = "legacy"` without forced replacement
- legacy locals remain as aliases where downstream Terraform references may still depend on them
- backend bootstrap resources stay pinned to existing `charitystatusapi-*` names until an explicit state migration is planned
- public routes, customer-visible API contracts, environment variables, and existing deployed identifiers are out of scope for this phase

In practice:

- product / brand naming belongs in customer-visible configuration
- capability naming belongs in Terraform locals, task labels, workflow ids, and docs
- legacy naming remains only where compatibility or resource stability still requires it

## Canonical Internal Conventions

Use capability-oriented names going forward:

- Terraform locals:
  - `stable_resource_prefix`
  - `data_catalog_prefix`
  - `lambda_function_names`
  - `queue_names`
  - `scheduled_workflow_names`
  - `platform_common_tags`
- future workflow and compute labels:
  - Step Functions workflow: `verification_workflow` or `monthly_ingest`
  - ECS cluster reference: `verification_platform`
  - ECS task family: `platform_processing` or a workflow-specific capability label
  - EventBridge schedule labels: `regulatory_data_ingestion`, `platform_refresh`, `monthly_filing_ingestion`
- tags:
  - `PlatformNamespace = verification_platform`
  - `PlatformDomain = organization_verification`
  - `PlatformLayer = infrastructure`
  - `NamingStrategy = legacy|standardized`

## Legacy To Neutral Mapping

| Legacy infra term | Neutral term | Category | Notes |
| --- | --- | --- | --- |
| `legacy_name_prefix` | `stable_resource_prefix` | 1. Safe to rename now | Internal Terraform local only; legacy alias remains. |
| `db_prefix` | `data_catalog_prefix` | 1. Safe to rename now | Internal Terraform local only; legacy alias remains. |
| `ingest_lambda_name` | `lambda_function_names.regulatory_data_ingestion` | 2. Abstracted behind compatibility layer | Old local remains as alias for downstream references. |
| `query_lambda_name` | `lambda_function_names.organization_verification_api` | 2. Abstracted behind compatibility layer | Preserves current Lambda resource identity. |
| `refresh_lambda_name` | `lambda_function_names.platform_refresh` | 2. Abstracted behind compatibility layer | Preserves current Lambda resource identity. |
| monthly ingest staging Lambda | `lambda_function_names.monthly_private_ingest_staging` | 2. Abstracted behind compatibility layer | Neutral internal label for the ZIP staging worker; physical name still follows the centralized resource-name strategy. |
| monthly ingest worker repository | `monthly_ingest_worker_repository_name` | 2. Abstracted behind compatibility layer | Neutral internal identifier for the managed ECS worker image repository. |
| `form990_ingest_lambda_name` | `lambda_function_names.regulatory_filing_ingestion` | 2. Abstracted behind compatibility layer | Keeps existing physical name strategy. |
| `form990_orchestrator_lambda_name` | `lambda_function_names.regulatory_filing_orchestrator` | 2. Abstracted behind compatibility layer | Keeps existing physical name strategy. |
| `form990_worker_lambda_name` | `lambda_function_names.regulatory_filing_worker` | 2. Abstracted behind compatibility layer | Keeps existing physical name strategy. |
| `form990_work_dlq_name` | `queue_names.regulatory_filing_work_dead_letter` | 2. Abstracted behind compatibility layer | Queue resource address is unchanged. |
| `form990_work_queue_name` | `queue_names.regulatory_filing_work` | 2. Abstracted behind compatibility layer | Queue resource address is unchanged. |
| `daily_ingest_rule_name` | `scheduled_workflow_names.regulatory_data_ingestion` | 2. Abstracted behind compatibility layer | EventBridge rule identity is still centrally controlled. |
| `refresh_schedule_rule_name` | `scheduled_workflow_names.platform_refresh` | 2. Abstracted behind compatibility layer | EventBridge rule identity is still centrally controlled. |
| `form990_schedule_rule_name` | `scheduled_workflow_names.monthly_filing_ingestion` | 2. Abstracted behind compatibility layer | Leaves future workflow expansion room. |
| monthly ingest workflow state machine | `monthly_ingest_state_machine_name` | 2. Abstracted behind compatibility layer | Neutral internal identifier; physical name still follows the centralized resource-name strategy. |
| monthly ingest schedule rule | `monthly_ingest_schedule_rule_name` | 2. Abstracted behind compatibility layer | Neutral schedule label for Step Functions orchestration. |
| `Project = var.base_name` tag | `platform_common_tags` plus preserved `Project` | 2. Abstracted behind compatibility layer | Existing project tag is retained for continuity; neutral tags are added alongside it. |
| `base_name` Terraform variable | `base_name` retained | 3. Must remain temporarily | It still anchors legacy physical names and bootstrap assumptions. |
| `charitystatusapi-dev` backend bucket/table | preserved | 3. Must remain temporarily | Changing backend bootstrap names requires separate state migration planning. |
| `charitystatusapi-tfstate` / `charitystatusapi-tf-locks` | preserved | 3. Must remain temporarily | Same reason as above. |
| public API paths such as `/v1/nonprofit/...` | preserved | 4. Customer-facing/public contract | Out of scope for this phase. |
| environment variables such as `APP_NAME`, `PUBLIC_BRAND_NAME` | preserved | 4. Customer-facing/public contract | Runtime contract stability takes priority here. |

## What Was Renamed vs Preserved

Renamed internally:

- Terraform now treats grouped lambda, queue, and schedule names as capability maps instead of single-purpose legacy-first locals
- tag composition now starts from `platform_common_tags`
- data catalog naming now references `data_catalog_prefix`

Preserved intentionally:

- deployed physical resource names unless `resource_name_strategy` is explicitly changed
- backend bootstrap bucket and lock-table names
- resource block addresses in Terraform state
- customer-facing route names, env vars, and API contracts
- the optional external `monthly_ingest_staging_lambda_arn` override for environments that want a separately managed staging Lambda

## Contributor Guidance

- prefer capability-oriented labels for new locals, outputs, and logical identifiers
- keep physical AWS name changes behind explicit migration toggles or override maps
- if a rename would require Terraform replacement, default to an alias or wrapper local first
- document any intentionally retained legacy name in the mapping table above
- avoid introducing new `charitystatusapi`, `verification_api`, or `CharityStatusAPI` tokens in infrastructure code unless the value is a pinned compatibility exception

## Follow-Up Cleanup

- a later state-migration phase can decide whether to move backend bootstrap resources off `charitystatusapi-*`
- ECS cluster names, task families, Step Functions names, and CloudWatch log groups for the monthly ingest workflow should use the neutral conventions above when those resources are wired in
- later cleanup can decide whether any environment still needs the external staging-Lambda ARN override once the in-repo Lambda is fully standard
- once downstream Terraform references stop using the alias locals, the compatibility aliases can be removed in a later cleanup pass

