# Backend Shared Runtime Concerns

Target ownership for `backend/shared/`:

- runtime-only config loading and secret/env wiring
- logging/bootstrap helpers
- dependency assembly helpers reused across backend runtimes
- request/response compatibility helpers that do not belong in deployment-only paths
- health/readiness helpers and other shared runtime concerns

Python package root:

- `backend/shared/src/verification_backend/shared/`
- current scaffold helpers should stay intentionally small and runtime-focused

Current local-dev helpers:

- `local_dev.py`
  - loads `backend/.env.local` without overriding already-exported shell vars
  - provides `python -m verification_backend.shared.local_dev db-upgrade`
  - provides `python -m verification_backend.shared.local_dev db-current`

Planned inbound migration:

- runtime bootstrap helpers currently assembled under `infrastructure/verification/platform/`
- shared transport/runtime-facing helpers currently rooted under `infrastructure/verification/api/`
- runtime contracts should remain backend-owned and avoid reintroducing retired package roots

