# Repository Target Architecture Assessment

This document records the current repository assessment and the recommended target-state split between:

1. `frontend/`
2. `backend/`
3. `infrastructure/`

while preserving the code/package boundaries:

1. `public-core/`
2. `private-platform/`

It is intentionally grounded in the code that exists today under `infrastructure/verification/` and the current Lambda/Terraform layout. This phase does not move code; it defines the target map and the migration order.

## What Was Analyzed

Primary runtime and entrypoint files:

- `infrastructure/lambda_query.py`
- `infrastructure/lambda_refresh.py`
- `infrastructure/eo_bmf_ingest_worker.py`
- `infrastructure/lambda_form990.py`
- `infrastructure/lambda_form990_orchestrator.py`
- `infrastructure/lambda_form990_worker.py`

Primary package groups:

- `infrastructure/verification/api/`
- `infrastructure/verification/auth/`
- `infrastructure/verification/billing/`
- `infrastructure/verification/control_plane/`
- `infrastructure/verification/core/`
- `infrastructure/verification/decision/`
- `infrastructure/verification/enrichments/`
- `infrastructure/verification/evidence/`
- `infrastructure/verification/form990/`
- `infrastructure/verification/ingest/`
- `infrastructure/verification/normalization/`
- `infrastructure/verification/ops/`
- `infrastructure/verification/platform/`
- `infrastructure/verification/policy/`
- `infrastructure/verification/query/`
- `infrastructure/verification/scoring/`
- `infrastructure/verification/serving/`
- `infrastructure/verification/sources/`
- `infrastructure/verification/state_registry/`

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

- `infrastructure/verification/decision/`
- `infrastructure/verification/evidence/`
- `infrastructure/verification/normalization/`
- `infrastructure/verification/policy/`
- `infrastructure/verification/scoring/`
- `infrastructure/verification/sources/`
- `infrastructure/verification/query/verification.py`
- `infrastructure/verification/query/nonprofit_lookup.py`
- `infrastructure/verification/query/source_views.py`
- `infrastructure/verification/enrichments/service.py`
- `infrastructure/verification/serving/materializer.py`
- `infrastructure/verification/serving/refresh.py`
- `infrastructure/verification/serving/change_detection.py`
- `infrastructure/verification/serving/models.py`
- `infrastructure/verification/state_registry/`
- parser/metrics/governance/relationships/discovery logic under `infrastructure/verification/form990/`

### Private-platform candidates

These areas are platform-specific, account/customer-specific, operator-focused, or runtime/integration specific:

- `infrastructure/verification/auth/`
- `infrastructure/verification/billing/`
- `infrastructure/verification/control_plane/`
- `infrastructure/verification/ingest/`
- `infrastructure/verification/ops/`
- `infrastructure/verification/platform/`
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

- `infrastructure/verification/api/routes.py`
- `infrastructure/verification/api/responses.py`
- all `infrastructure/lambda_*.py`

### Mixed concern / refactor required first

These are the highest-priority seam fixes before extraction:

- `infrastructure/verification/core/models.py`
  - currently imports billing models
- `infrastructure/verification/query/athena.py`
  - AWS adapter embedded in query layer
- `infrastructure/verification/serving/dynamodb_store.py`
  - storage adapter embedded beside serving logic
- `infrastructure/verification/enrichments/organization_store.py`
  - domain/service and Dynamo adapter in one module
- `infrastructure/verification/form990/`
  - parser/domain logic and S3-backed manifest/raw-sync logic are interleaved
- `infrastructure/lambda_query.py`
  - routing, env/config, auth, billing, control-plane, response shaping, and runtime wiring all meet here

## Target Architecture

Recommended target tree:

```text
frontend/
  marketing/
  portal/
  shared/
  docs/

backend/
  api/
  worker/
  ingest-task/
  shared/

public-core/
  src/verification/
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
  src/verification_platform/
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

- `frontend/` remains the browser/runtime UI layer and should stay separate from Python runtime tooling.
- `backend/` becomes the executable runtime host layer for the API server, worker runtimes, ingest tasks, and runtime-shared bootstrap concerns.
- `backend/` should use a pragmatic Python workspace layout so local runtime development can happen without introducing a repo-wide Python monorepo toolchain.
- `public-core` remains the canonical home for reusable deterministic domain logic.
- `private-platform` owns all platform billing. Nothing billing-related should live in public-core.
- All billing stays private-platform.
- `private-platform` uses a distinct package root, `verification_platform`, to avoid namespace confusion with `verification`.
- a neutral capability-oriented namespace, `verification_platform`, may be used as a compatibility abstraction layer while legacy `verification` imports remain in place
- `infrastructure/` should end in a deployment-only role. It should package and wire entrypoints, not own business logic.
- `backend/` is not a replacement for `public-core` or `private-platform`; it is the runtime host layer above them.

## Backend Runtime Ownership Targets

Current runtime ownership still stranded in `infrastructure/`:

- `infrastructure/lambda_query.py`
  - current HTTP API composition root
- `infrastructure/lambda_refresh.py`
  - current profile refresh job runtime host
- `infrastructure/eo_bmf_ingest_worker.py`
  - current EO/BMF ingest runtime host
- `infrastructure/lambda_form990.py`
  - current Form 990 ingest/discovery/orchestration runtime host
- `infrastructure/lambda_form990_orchestrator.py`
  - current Form 990 orchestration shim
- `infrastructure/lambda_form990_worker.py`
  - current Form 990 worker runtime host
- `infrastructure/verification/api/routes.py`
- `infrastructure/verification/api/responses.py`
- `infrastructure/verification/core/interfaces.py`
- `infrastructure/verification/platform/`

Target runtime placement:

- `backend/api/`
  - successor to `infrastructure.lambda_query`
  - owns ASGI/bootstrap, request composition, and health/readiness ownership
- `backend/worker/`
  - successor to `infrastructure.lambda_refresh` and future general worker hosts
  - intended long-term deployment target: private ECS service, separate from
    ingest-task execution
- `backend/ingest-task/`
  - successor to `infrastructure.eo_bmf_ingest_worker`, `infrastructure.lambda_form990`, `infrastructure.lambda_form990_orchestrator`, and `infrastructure.lambda_form990_worker`
  - intended long-term deployment target: ECS task-style execution for
    scheduled and one-off ingest runs
  - current home for Form 990 and monthly ingest-task runtime ownership, while infrastructure retains thin deployment adapters
  - should converge on a local-first workspace execution model so one archive
    runs at a time inside a deterministic workspace that can map equally well
    to developer disk or ECS ephemeral storage
- `backend/shared/`
  - future home for runtime bootstrap helpers, shared transport/runtime compatibility helpers, logging/config assembly, and other runtime-only concerns

Transition rule:

- `private-platform/src/verification_platform/runtime/backend_contracts.py` remains the compatibility re-export root until shared runtime contracts move out of the legacy infrastructure path
- `infrastructure/` may keep temporary deployment shims while packaging and deploy wiring catch up, but it should stop accumulating runtime ownership

Current workspace posture:

- `backend/` now carries a single setuptools project rooted at `backend/pyproject.toml`
- runtime-owned source roots remain explicit under `backend/api/src/`, `backend/worker/src/`, `backend/ingest-task/src/`, and `backend/shared/src/`
- this keeps runtime ownership visible while still allowing one editable backend install for local development

Private-platform service areas now defined in the repo:

- `verification_platform.identity_access`
- `verification_platform.customer_accounts`
- `verification_platform.billing_usage`
- `verification_platform.admin_operations`
- `verification_platform.runtime`
- `verification_platform.notifications`

Private runtime transition helpers now defined:

- `verification_platform.runtime.entrypoints`
  - canonical map of the currently deployed backend entrypoints
- `verification_platform.runtime.backend_contracts`
  - canonical private-platform compatibility root for API response-envelope and route-version helpers while those contracts still live under `verification.api`

## Dependency Rules

Required dependency direction:

- `frontend/` depends on HTTP contracts and frontend shared packages only
- `frontend/` must not import Python runtime code from `backend/`, `private-platform/`, or `infrastructure/`
- `backend/` may depend on `verification` and `verification_platform`
- `private-platform/` must not depend on `backend/` or `infrastructure/`
- `verification_platform` may depend on `verification`
- `verification` must not depend on `verification_platform`
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

- `infrastructure/verification/query/athena.py`
  - direct Athena client construction and AWS assumptions
- `infrastructure/verification/serving/dynamodb_store.py`
  - direct DynamoDB access
- `infrastructure/verification/control_plane/dynamodb_store.py`
  - direct DynamoDB access
- `infrastructure/verification/enrichments/organization_store.py`
  - direct DynamoDB access mixed with organization settings domain logic
- `infrastructure/verification/ops/run_store.py`
  - operational persistence and run-tracking logic
- multiple `form990` modules
  - S3-backed manifest/raw sync concerns mixed with parser and batch-processing concerns
- `infrastructure/verification/platform/runtime.py`
  - env/runtime composition of adapters
- `infrastructure/verification/platform/auth.py`
  - auth/quota/runtime composition and static store wiring
- `infrastructure/lambda_query.py`
  - the highest-density composition root in the repo

## Staged Migration Sequence

### Stage 1: planning and boundary scaffolding

- keep all runtime imports intact
- document the current-state assessment and target tree
- tighten `split-plan.json` to reflect actual boundaries
- add `backend/` scaffold READMEs so future extraction has a consistent direction

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

### Stage 4: extract backend runtime hosts

- move API runtime hosting and request composition from `infrastructure/lambda_query.py` into `backend/api`
- move refresh and general non-HTTP runtime hosts into `backend/worker`
- move EO/BMF and Form 990 task hosts into `backend/ingest-task`
- move runtime-shared bootstrap/config/logging helpers into `backend/shared`
- keep temporary compatibility shims in current runtime locations until packaging and deploy wiring are switched

### Stage 5: extract private-platform

- move auth, billing, control-plane, ops, runtime builders, adapters, and entrypoint orchestration into `private-platform`
- keep temporary compatibility shims in current runtime locations until packaging and deploy wiring are switched

### Stage 6: reduce infrastructure

- move Terraform/environment files toward `infrastructure/terraform/` and `infrastructure/env/`
- leave only deployment assets, scripts, and temporary Lambda shims in `infrastructure/`

## Highest-Risk Refactors

These should be treated as separate, explicit implementation phases:

- `infrastructure/lambda_query.py`
- `infrastructure/verification/core/models.py`
- `infrastructure/verification/billing/`
- `infrastructure/verification/query/athena.py`
- `infrastructure/verification/enrichments/organization_store.py`
- `infrastructure/verification/form990/`
- `infrastructure/verification/serving/`

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

