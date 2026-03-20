# Backend Stage-1 Readiness

This document finalizes the first-stage backend split so frontend scaffolding and later vertical-slice backend work can proceed against clearer boundaries without forcing a disruptive handler migration yet.

## Primary Modules Assessed

Entrypoints and workers:

- `infrastructure/lambda_query.py`
- `infrastructure/lambda_refresh.py`
- `infrastructure/lambda_ingest.py`
- `infrastructure/lambda_form990.py`
- `infrastructure/lambda_form990_orchestrator.py`
- `infrastructure/lambda_form990_worker.py`

Shared backend contracts and interfaces:

- `infrastructure/charity_status/api/routes.py`
- `infrastructure/charity_status/api/responses.py`
- `infrastructure/charity_status/core/interfaces.py`

Split-scaffolding and transition roots:

- `public-core/src/charity_status/`
- `private-platform/src/charity_status_platform/`
- `infrastructure/`

## Entrypoint Ownership Map

The live backend entrypoints still run from `infrastructure/lambda_*.py`. That is acceptable for the current phase, but they are now explicitly treated as deploy-time shims and composition roots rather than the long-term home of backend application logic.

Canonical internal map:

- `charity_status_platform.runtime.entrypoints`

Current live entrypoints:

- `infrastructure.lambda_query.handler`
  - HTTP API handler
  - owns routing, response-envelope application, and composition of customer/admin/private-platform services
- `infrastructure.lambda_refresh.handler`
  - profile refresh job entrypoint
- `infrastructure.lambda_ingest.handler`
  - EO/BMF ingest job entrypoint
- `infrastructure.lambda_form990.handler`
  - Form 990 ingest/discovery entrypoint
- `infrastructure.lambda_form990_orchestrator.handler`
  - current Form 990 orchestration shim
- `infrastructure.lambda_form990_worker.handler`
  - queued Form 990 worker entrypoint

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

This keeps the repo safe while imports still point at `infrastructure/`.

## How Future Vertical Slices Should Land

Until a later migration phase moves live code:

- put reusable deterministic logic in `public-core/` only when it is clearly open-safe
- put customer/account/auth/billing/admin/backend orchestration in `private-platform/`
- keep `infrastructure/` limited to deploy-time entrypoints, Terraform, and environment wiring
- if a new slice needs HTTP handlers, add the service logic under `private-platform` first and keep the `infrastructure/lambda_*.py` layer thin

## Remaining Blockers Before Frontend Scaffolding

The repo is ready for frontend scaffolding at the architecture-boundary level, but a few backend follow-ups still remain:

- `infrastructure/lambda_query.py` is still a large composition root and should keep shrinking over time
- `infrastructure/charity_status/api/` contracts still live under the legacy runtime path and are only mirrored through compatibility exports today
- root `tests/` still carries most of the live suite, so near-package tests are scaffolded but not yet widely migrated
- some mixed infrastructure-heavy modules, especially in `form990/`, `serving/`, and `control_plane/`, still need later seam-fix passes

These are not blockers for starting frontend scaffolding, but they are the highest-value backend cleanup items to continue in parallel.
