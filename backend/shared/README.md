# Backend Shared Runtime Concerns

Target ownership for `backend/shared/`:

- runtime-only config loading and secret/env wiring
- logging/bootstrap helpers
- dependency assembly helpers reused across backend runtimes
- request/response compatibility helpers that do not belong in deployment-only paths
- health/readiness helpers and other shared runtime concerns

Python package root:

- `backend/shared/src/charity_status_backend/shared/`
- current scaffold helpers should stay intentionally small and runtime-focused

Planned inbound migration:

- runtime bootstrap helpers currently assembled under `infrastructure/charity_status/platform/`
- shared transport/runtime-facing helpers currently rooted under `infrastructure/charity_status/api/`
- compatibility exports that may temporarily remain mirrored through `charity_status_platform.runtime.backend_contracts`

Compatibility rule:

- `private-platform/src/charity_status_platform/runtime/backend_contracts.py` remains the compatibility re-export root until live imports are moved
- this directory should host runtime-sharing concerns only, not reusable domain logic that belongs in `public-core/`
