# Backend API Runtime

Target ownership for `backend/api/`:

- primary API server runtime host
- ASGI app/bootstrap and startup wiring
- request composition and HTTP transport integration
- health and readiness endpoint ownership
- the eventual source of truth for the public API runtime once legacy Lambda rollback shims are retired

Python package root:

- `backend/api/src/charity_status_backend/api/`
- canonical ASGI app import: `charity_status_backend.api.app:app`
- local runtime entrypoint: `python -m charity_status_backend.api.entrypoint`

Planned inbound migration:

- `infrastructure.lambda_query`
- HTTP runtime-specific bootstrap currently assembled under `infrastructure/charity_status/platform/`
- shared transport helpers that should move into `backend/shared/`

Current phase posture:

- `charity_status_backend.api.runtime` now owns the primary API runtime implementation
- `charity_status_backend.api.app` now owns FastAPI app assembly, route registration, and health/readiness endpoints
- `infrastructure.lambda_query` remains only as a thin rollback and compatibility import path
- `charity_status_platform.runtime.api_compat` remains only as a compatibility import root for the backend-owned app

Local run:

```powershell
python -m charity_status_backend.api.entrypoint
```

Local backend API development should use the shared backend-local env contract:

- copy `backend/.env.local.example` to `backend/.env.local`
- point `PLATFORM_POSTGRES_URL` at a direct local PostgreSQL 16 endpoint
- run `python -m charity_status_backend.shared.local_dev db-upgrade`
- then run `python -m charity_status_backend.api.entrypoint`

The API entrypoint loads `backend/.env.local` automatically before importing
env-driven runtime modules, so local PostgreSQL-backed API execution does not
require AWS secret resolution just to start the runtime.

Not owned here:

- deterministic nonprofit/domain logic from `public-core/`
- proprietary service implementations that belong in `private-platform/`
- Terraform, DNS, ALB, ECS, and other deployment wiring from `infrastructure/`
