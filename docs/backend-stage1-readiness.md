# Backend Stage-1 Readiness

This document finalizes the first-stage backend split so frontend scaffolding and later vertical-slice backend work can proceed against clearer boundaries without forcing a disruptive handler migration yet.

## Primary Modules Assessed

Entrypoints and workers:

- `infrastructure/lambda_query.py`
- `infrastructure/lambda_refresh.py`
- `infrastructure/eo_bmf_ingest_worker.py`
- `infrastructure/monthly_ingest_worker.py`
- `infrastructure/nonprofit_ingest_persistence.py`

Shared backend contracts and interfaces:

- `infrastructure/charity_status/api/routes.py`
- `infrastructure/charity_status/api/responses.py`
- `infrastructure/charity_status/core/interfaces.py`

Split-scaffolding and transition roots:

- `backend/`
- `public-core/src/charity_status/`
- `private-platform/src/charity_status_platform/`
- `infrastructure/`

## Entrypoint Ownership Map

The repo still retains `infrastructure/lambda_*.py` entrypoints, but the
primary public API ingress has now moved to ECS/ALB. Those Lambda entrypoints
should be treated as deploy-time shims and composition roots rather than the
long-term home of backend application logic.

Canonical internal map:

- `charity_status_platform.runtime.entrypoints`

Current live entrypoints:

- `infrastructure.lambda_query.handler`
  - deprecated rollback HTTP API handler
  - owns routing, response-envelope application, and composition of customer/admin/private-platform services
- `infrastructure.lambda_refresh.handler`
  - profile refresh job entrypoint
- `infrastructure.eo_bmf_ingest_worker.handler`
  - EO/BMF ingest job entrypoint
- `infrastructure.monthly_ingest_worker.main`
  - workspace-plus-PostgreSQL Form 990 monthly runtime
- `infrastructure.nonprofit_ingest_persistence.build_form990_nonprofit_persistence_service`
  - backend-owned nonprofit persistence compatibility entrypoint

## Runtime Extraction Targets

Current misplaced runtime ownership still stranded in `infrastructure/`:

- `infrastructure/lambda_query.py`
  - still the main HTTP API composition root for auth, billing, admin, webhook, routing, and response shaping
- `infrastructure/lambda_refresh.py`
  - still the profile refresh runtime host
- `infrastructure/eo_bmf_ingest_worker.py`
  - still the EO/BMF ingest runtime host
- `infrastructure/monthly_ingest_worker.py`
  - compatibility shim over the backend-owned monthly ingest runtime
- `infrastructure/nonprofit_ingest_persistence.py`
  - compatibility shim over the backend-owned nonprofit persistence service
- `infrastructure/charity_status/api/routes.py`, `infrastructure/charity_status/api/responses.py`, and `infrastructure/charity_status/core/interfaces.py`
  - still hold transport/runtime-facing contracts under the legacy runtime path
- `infrastructure/charity_status/platform/`
  - still owns env-driven runtime assembly and bootstrap concerns

Target backend ownership map:

- `backend/api/`
  - target home for the primary API server runtime host
  - now owns the extracted successor to `infrastructure.lambda_query` for ASGI app assembly and shared API runtime dispatch
- `backend/worker/`
  - target home for profile refresh and future generic worker runtime hosts
- `backend/ingest-task/`
  - current home for Form 990 ingest/orchestration/worker runtime ownership and monthly ingest runtime entrypoints
  - now also owns the local-first Form 990 workspace architecture contract:
    archive-at-a-time processing, deterministic workspace directories, and
    ECS-compatible ephemeral-disk expectations
- `backend/shared/`
  - target home for runtime-only shared bootstrap, transport helpers, logging/config wiring, and compatibility helpers

Backend Python workspace posture:

- `backend/` now has a first-class setuptools workspace in `backend/pyproject.toml`
- runtime-owned source roots now live under:
  - `backend/api/src/`
  - `backend/worker/src/`
  - `backend/ingest-task/src/`
  - `backend/shared/src/`
- the installed runtime import root is `charity_status_backend`
- local scaffold entrypoints exist for API, worker, and ingest-task runtime homes
- backend local development now centers on `backend/.env.local` plus the
  backend-owned `charity_status_backend.shared.local_dev` migration wrapper
- the canonical local database path is a direct PostgreSQL endpoint via
  `PLATFORM_POSTGRES_URL`, not AWS secret-backed wiring
- backend-owned Dockerfiles now live under `backend/api/`, `backend/worker/`,
  and `backend/ingest-task/` as the canonical runtime image contracts
- `backend/ingest-task` now defines a local-first Form 990 workspace model
  rooted at `FORM990_WORKSPACE_DIR`, with deterministic `archives/`,
  `extracted/`, `logs/`, and `state/` subdirectories. The canonical
  local-first workspace contract explicitly uses `archives/`, `extracted/`, `logs/`, and `state/`. In short: `archives/`, `extracted/`, `logs/`, and `state/` are the required workspace directories so local runs can match future ECS ephemeral-storage layout more closely
- Terraform now maps those runtime boundaries explicitly:
  - `backend/api` -> ALB-backed ECS service
  - `backend/worker` -> private ECS service placeholder, disabled by default
  - `backend/ingest-task` -> ECS task-style runtime for scheduled and one-off ingest execution
- live runtime behavior still remains under `infrastructure/lambda_*.py` until later extraction phases move execution over deliberately

Compatibility posture for the transition:

- `charity_status_platform.runtime.entrypoints` remains the canonical map of current live handler imports until extraction phases move the real entrypoints
- `charity_status_platform.runtime.backend_contracts` remains the compatibility re-export root while shared transport/runtime contracts still live under legacy paths
- `charity_status_platform.runtime.api_compat` remains a compatibility import root and no longer owns FastAPI assembly directly
- `infrastructure.lambda_query` remains a thin rollback/import shim over the backend-owned API runtime
- `infrastructure.monthly_ingest_worker` remains the thin compatibility/import shim over the backend-owned monthly ingest runtime
- `infrastructure.nonprofit_ingest_persistence` remains the thin compatibility/import shim over backend-owned nonprofit persistence wiring
- `infrastructure/` remains allowed to host temporary deployment shims, but should stop being the long-term owner of executable runtime logic

## Shared Contract Guidance

The backend now distinguishes three kinds of shared contracts:

1. Transport contracts
- canonical compatibility root: `charity_status_platform.runtime.backend_contracts`
- current implementation source:
  - `infrastructure/charity_status/api/routes.py`
  - `infrastructure/charity_status/api/responses.py`

2. Application adapter interfaces
- canonical home today:
  - `infrastructure/charity_status/core/interfaces.py`
- examples:
  - `QueryRepository`
  - `ProfileStoreAdapter`
  - `EnrichmentProviderGateway`
  - `AuthContextProvider`
  - `QuotaMeteringHook`

3. Public-core deterministic schemas and models
- canonical home for extracted open-safe modules:
  - `public-core/src/charity_status/`

Rules:

- API response envelopes and route-version helpers are private-platform/runtime contracts, not public-core contracts.
- Provider adapter protocols belong with application/domain seams, not in deployment wiring.
- New frontend-facing backend work should consume stable HTTP contracts from the runtime contract layer rather than redefining response-envelope behavior ad hoc in handlers.

## Test Strategy For Continued Development

The test layout is now intentionally three-tiered:

1. Public-core unit tests
- future home: `public-core/tests/`
- use for deterministic open-safe modules

2. Private-platform unit and boundary tests
- future home: `private-platform/tests/`
- use for auth, customer accounts, billing/usage, runtime boundaries, and compatibility maps

3. Root integration and compatibility tests
- current home: `tests/`
- keep using for:
  - live handler behavior
  - end-to-end API coverage
  - runtime compatibility shims
  - deployment-adjacent checks
  - Lambda-first rollback coverage while ECS is the primary runtime

This keeps the repo safe while imports still point at `infrastructure/`.

## How Future Vertical Slices Should Land

Until a later migration phase moves live code:

- put reusable deterministic logic in `public-core/` only when it is clearly open-safe
- put customer/account/auth/billing/admin/backend orchestration in `private-platform/`
- put executable runtime hosts and transport/runtime bootstrap into `backend/`
- keep `infrastructure/` limited to deploy-time entrypoints, Terraform, and environment wiring
- if a new slice needs HTTP handlers, add the service logic under `private-platform`, place runtime ownership under `backend/`, and keep the `infrastructure/lambda_*.py` layer thin

## Remaining Blockers Before Frontend Scaffolding

The repo is ready for frontend scaffolding at the architecture-boundary level, but a few backend follow-ups still remain:

- `infrastructure/lambda_query.py` is still a large composition root and should keep shrinking over time
- ECS-hosted HTTP runtime tests and docs still need to replace more of the
  Lambda-first assumptions over time
- `infrastructure/charity_status/api/` contracts still live under the legacy runtime path and are only mirrored through compatibility exports today
- root `tests/` still carries most of the live suite, so near-package tests are scaffolded but not yet widely migrated
- some mixed infrastructure-heavy modules, especially in `form990/`, `serving/`, and `control_plane/`, still need later seam-fix passes

These are not blockers for starting frontend scaffolding, but they are the highest-value backend cleanup items to continue in parallel.
