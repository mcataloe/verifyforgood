# Repository Target Architecture Assessment

This document records the current repository assessment and the recommended target-state split between:

1. `public-core/`
2. `private-platform/`
3. `infrastructure/`

It is intentionally grounded in the code that exists today under `infrastructure/charity_status/` and the current Lambda/Terraform layout. This phase does not move code; it defines the target map and the migration order.

## What Was Analyzed

Primary runtime and entrypoint files:

- `infrastructure/lambda_query.py`
- `infrastructure/lambda_refresh.py`
- `infrastructure/lambda_ingest.py`
- `infrastructure/lambda_form990.py`
- `infrastructure/lambda_form990_orchestrator.py`
- `infrastructure/lambda_form990_worker.py`

Primary package groups:

- `infrastructure/charity_status/api/`
- `infrastructure/charity_status/auth/`
- `infrastructure/charity_status/billing/`
- `infrastructure/charity_status/control_plane/`
- `infrastructure/charity_status/core/`
- `infrastructure/charity_status/decision/`
- `infrastructure/charity_status/enrichments/`
- `infrastructure/charity_status/evidence/`
- `infrastructure/charity_status/form990/`
- `infrastructure/charity_status/ingest/`
- `infrastructure/charity_status/normalization/`
- `infrastructure/charity_status/ops/`
- `infrastructure/charity_status/platform/`
- `infrastructure/charity_status/policy/`
- `infrastructure/charity_status/query/`
- `infrastructure/charity_status/scoring/`
- `infrastructure/charity_status/serving/`
- `infrastructure/charity_status/sources/`
- `infrastructure/charity_status/state_registry/`

Split scaffolding and packaging files:

- `public-core/pyproject.toml`
- `public-core/README.md`
- `private-platform/README.md`
- `infra-deployment/README.md`
- `docs/repo-split-guide.md`
- `split-plan.json`
- `tests/test_repo_split_scaffolding.py`

## Current-State Classification

### Public-core candidates

These areas are primarily deterministic, reusable, and open-safe, though some still need adapter extraction around them:

- `infrastructure/charity_status/decision/`
- `infrastructure/charity_status/evidence/`
- `infrastructure/charity_status/normalization/`
- `infrastructure/charity_status/policy/`
- `infrastructure/charity_status/scoring/`
- `infrastructure/charity_status/sources/`
- `infrastructure/charity_status/query/verification.py`
- `infrastructure/charity_status/query/nonprofit_lookup.py`
- `infrastructure/charity_status/query/source_views.py`
- `infrastructure/charity_status/enrichments/service.py`
- `infrastructure/charity_status/serving/materializer.py`
- `infrastructure/charity_status/serving/refresh.py`
- `infrastructure/charity_status/serving/change_detection.py`
- `infrastructure/charity_status/serving/models.py`
- `infrastructure/charity_status/state_registry/`
- parser/metrics/governance/relationships/discovery logic under `infrastructure/charity_status/form990/`

### Private-platform candidates

These areas are platform-specific, account/customer-specific, operator-focused, or runtime/integration specific:

- `infrastructure/charity_status/auth/`
- `infrastructure/charity_status/billing/`
- `infrastructure/charity_status/control_plane/`
- `infrastructure/charity_status/ingest/`
- `infrastructure/charity_status/ops/`
- `infrastructure/charity_status/platform/`
- all `infrastructure/lambda_*.py` entrypoints

### Infrastructure/deployment

These assets should converge on deployment-only responsibilities:

- `infrastructure/*.tf`
- `infrastructure/backend-*.hcl`
- `infrastructure/*.tfvars`
- deploy/package scripts and environment wiring
- `infra-deployment/`

### Entrypoint/interface layer

These files define transport behavior rather than reusable business logic:

- `infrastructure/charity_status/api/routes.py`
- `infrastructure/charity_status/api/responses.py`
- all `infrastructure/lambda_*.py`

### Mixed concern / refactor required first

These are the highest-priority seam fixes before extraction:

- `infrastructure/charity_status/core/models.py`
  - currently imports billing models
- `infrastructure/charity_status/query/athena.py`
  - AWS adapter embedded in query layer
- `infrastructure/charity_status/serving/dynamodb_store.py`
  - storage adapter embedded beside serving logic
- `infrastructure/charity_status/enrichments/organization_store.py`
  - domain/service and Dynamo adapter in one module
- `infrastructure/charity_status/form990/`
  - parser/domain logic and S3-backed manifest/raw-sync logic are interleaved
- `infrastructure/lambda_query.py`
  - routing, env/config, auth, billing, control-plane, response shaping, and runtime wiring all meet here

## Target Architecture

Recommended target tree:

```text
public-core/
  src/charity_status/
    core/
    decision/
    evidence/
    normalization/
    policy/
    scoring/
    sources/
    query/
    enrichments/
    serving/
    state_registry/
    form990/
  tests/

private-platform/
  src/charity_status_platform/
    auth/
    billing/
    control_plane/
    ops/
    runtime/
    adapters/
    jobs/
    entrypoints/
  tests/

infrastructure/
  terraform/
  env/
  scripts/
  lambda_shims/
```

Key design decisions:

- `public-core` remains the canonical home for reusable deterministic domain logic.
- `private-platform` owns all platform billing. Nothing billing-related should live in public-core.
- All billing stays private-platform.
- `private-platform` uses a distinct package root, `charity_status_platform`, to avoid namespace confusion with `charity_status`.
- `infrastructure/` should end in a deployment-only role. It should package and wire entrypoints, not own business logic.

Private-platform service areas now defined in the repo:

- `charity_status_platform.identity_access`
- `charity_status_platform.customer_accounts`
- `charity_status_platform.billing_usage`
- `charity_status_platform.admin_operations`
- `charity_status_platform.runtime`
- `charity_status_platform.notifications`

Private runtime transition helpers now defined:

- `charity_status_platform.runtime.entrypoints`
  - canonical map of the currently deployed backend entrypoints
- `charity_status_platform.runtime.backend_contracts`
  - canonical private-platform compatibility root for API response-envelope and route-version helpers while those contracts still live under `charity_status.api`

## Dependency Rules

Required dependency direction:

- `charity_status_platform` may depend on `charity_status`
- `charity_status` must not depend on `charity_status_platform`
- `infrastructure/` may depend on packaged entrypoints, but not the reverse

Billing rule:

- No subscription, plan, quota, entitlement, Stripe, billing status, or customer billing workflow logic belongs in `public-core`.
- Public-core should accept a billing-agnostic access or capability input when plan-derived behavior is needed.

What makes logic private-platform rather than public-core:

- it is tenant/customer/account specific
- it owns credentials or authz policy
- it enforces usage, billing, or budget controls
- it coordinates admin/operator workflows
- it depends on proprietary platform integrations or support flows
- it is runtime-composition or handler orchestration logic rather than reusable domain logic

Additional guardrails:

- AWS SDK usage belongs in platform adapters, not public-core services.
- Env/config parsing belongs in runtime wiring, not deep service logic.
- Response envelope shaping belongs in entrypoint or API layers, not domain services.
- Operator workflows and customer-account lifecycle logic stay private.

## Adapter Pattern In Practice

The current repository now uses a practical service/adapter split in the highest-value mixed modules:

- application/service modules own validation, merge rules, and domain orchestration
- adapter modules own AWS SDK creation and cloud-specific persistence/query execution
- entrypoints and runtime builders assemble the concrete adapters

Current examples:

- `enrichments/organization_settings_service.py`
  - service and validation logic
- `enrichments/organization_settings_stores.py`
  - in-memory and Dynamo-backed store adapters
- `query/athena_service.py`
  - Athena-backed query behavior with an injected client dependency
- `query/athena_adapter.py`
  - boto3 Athena client creation and concrete adapter construction
- `serving/storage_serialization.py`
  - reusable profile item serialization for Dynamo persistence
- `serving/dynamodb_adapter.py`
  - Dynamo profile store adapter

Compatibility shim rule:

- existing import paths may remain as thin re-export modules while the live runtime transitions
- new work should prefer the explicit `*_service.py`, `*_stores.py`, or `*_adapter.py` modules where they exist

## Current Coupling Points

Concrete infrastructure/platform leakage found during assessment:

- `infrastructure/charity_status/query/athena.py`
  - direct Athena client construction and AWS assumptions
- `infrastructure/charity_status/serving/dynamodb_store.py`
  - direct DynamoDB access
- `infrastructure/charity_status/control_plane/dynamodb_store.py`
  - direct DynamoDB access
- `infrastructure/charity_status/enrichments/organization_store.py`
  - direct DynamoDB access mixed with organization settings domain logic
- `infrastructure/charity_status/ops/run_store.py`
  - operational persistence and run-tracking logic
- multiple `form990` modules
  - S3-backed manifest/raw sync concerns mixed with parser and batch-processing concerns
- `infrastructure/charity_status/platform/runtime.py`
  - env/runtime composition of adapters
- `infrastructure/charity_status/platform/auth.py`
  - auth/quota/runtime composition and static store wiring
- `infrastructure/lambda_query.py`
  - the highest-density composition root in the repo

## Staged Migration Sequence

### Stage 1: planning and boundary scaffolding

- keep all runtime imports intact
- document the current-state assessment and target tree
- tighten `split-plan.json` to reflect actual boundaries
- update scaffold READMEs so future extraction has a consistent direction

### Stage 2: seam fixes before extraction

- remove `core -> billing` imports by introducing a billing-agnostic access/capability context
- split domain/service logic from concrete adapters in:
  - `enrichments/organization_store.py`
  - `serving/`
  - `form990/`
  - `query/athena.py`

### Stage 3: extract low-risk public-core logic

- first extract deterministic packages:
  - `decision`, `evidence`, `normalization`, `policy`, `scoring`, `sources`
- then extract pure use-case logic:
  - query use cases
  - enrichment service logic
  - serving domain logic
  - state registry domain logic
  - Form 990 parser/domain modules

### Stage 4: extract private-platform

- move auth, billing, control-plane, ops, runtime builders, adapters, and entrypoint orchestration into `private-platform`
- keep temporary compatibility shims in current runtime locations until packaging and deploy wiring are switched

### Stage 5: reduce infrastructure

- move Terraform/environment files toward `infrastructure/terraform/` and `infrastructure/env/`
- leave only deployment assets, scripts, and temporary Lambda shims in `infrastructure/`

## Highest-Risk Refactors

These should be treated as separate, explicit implementation phases:

- `infrastructure/lambda_query.py`
- `infrastructure/charity_status/core/models.py`
- `infrastructure/charity_status/billing/`
- `infrastructure/charity_status/query/athena.py`
- `infrastructure/charity_status/enrichments/organization_store.py`
- `infrastructure/charity_status/form990/`
- `infrastructure/charity_status/serving/`

## What Should Be Done First

The safest first implementation work is:

1. remove the `core -> billing` dependency
2. separate adapter code from domain/service code in the mixed modules
3. only then begin extracting low-risk public-core packages

That order minimizes churn, avoids broken imports, and preserves current runtime behavior while the split is still happening inside one repo.

## First Official Public-Core Extractions

The first low-risk modules suitable for extraction are:

- `normalization/`
- `sources/`
- schema-only `evidence/models.py`
- schema-only `policy/models.py`

Why these qualify:

- they are deterministic
- they do not require auth, billing, tenant/customer, or deployment wiring
- they do not require AWS/Stripe SDKs
- they provide reusable validators, schemas, and domain-relevant canonical structures
