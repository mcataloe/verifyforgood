# Backend Shared Runtime Concerns

Target ownership for `backend/shared/`:

- runtime-only config loading and secret/env wiring
- logging/bootstrap helpers
- dependency assembly helpers reused across backend runtimes
- request/response compatibility helpers that do not belong in deployment-only paths
- health/readiness helpers and other shared runtime concerns

Python package root:

- `backend/shared/src/verification/backend/shared/`
- current scaffold helpers should stay intentionally small and runtime-focused

Current local-dev helpers:

- `local_dev.py`
  - loads `backend/.env.local` without overriding already-exported shell vars
  - provides `python -m verification.backend.shared.local_dev db-upgrade`
  - provides `python -m verification.backend.shared.local_dev db-current`

Current cutover posture:

- shared runtime, platform, billing, query, identity, and nonprofit domain code now lives under `verification.backend.shared.*`
- local-dev bootstrap adds backend-owned source roots only; it no longer injects retired infrastructure package trees
- runtime contracts should remain backend-owned and avoid reintroducing retired package roots

