# Backend API Runtime

Target ownership for `backend/api/`:

- primary API server runtime host
- ASGI app/bootstrap and startup wiring
- request composition and HTTP transport integration
- health and readiness endpoint ownership
- the source of truth for the public API runtime

Python package root:

- `backend/api/src/verification_backend/api/`
- canonical ASGI app import: `verification_backend.api.app:app`
- local runtime entrypoint: `python -m verification_backend.api.entrypoint`

Runtime ownership:

- public HTTP entrypoint: `verification_backend.api.app:app`
- backend-local dispatch/runtime: `verification_backend.api.runtime.handle_api_event`
- shared compatibility transport seam: `verification_backend.api.transport`

Current phase posture:

- `verification_backend.api.runtime` now owns the primary API runtime implementation
- `verification_backend.api.app` now owns FastAPI app assembly, route registration, and health/readiness endpoints
- `verification_platform.runtime.api_compat` remains only as a compatibility import root for the backend-owned app
- `infrastructure/` is now deployment-only for API runtime concerns

Local run:

```powershell
python -m verification_backend.api.entrypoint
```

Container build/run:

```powershell
docker build -f backend/api/Dockerfile .
docker run -p 5621:5621 --env-file backend/.env.local <api-image>
```

Container contract:

- long-lived HTTP service
- listens on port `5621` with the checked-in local env contract
- starts with `uvicorn verification_backend.api.app:app`

Local backend API development should use the shared backend-local env contract:

- copy `backend/.env.local.example` to `backend/.env.local`
- point `PLATFORM_POSTGRES_URL` at a direct local PostgreSQL 16 endpoint
- optionally point `PLATFORM_NONPROFIT_POSTGRES_URL` at a separate PostgreSQL endpoint when nonprofit/query data should be isolated from customer and billing data
- run `python -m verification_backend.shared.local_dev db-upgrade`
- run `python -m verification_backend.shared.local_dev db-upgrade-nonprofit` when a separate nonprofit database is configured
- then run `python -m verification_backend.api.entrypoint`

The API entrypoint loads `backend/.env.local` automatically before importing
env-driven runtime modules, so local PostgreSQL-backed API execution does not
require AWS secret resolution just to start the runtime.

Container ownership lives here now rather than under `infrastructure/`, even
though Terraform still consumes only image URIs rather than Dockerfile paths.

Not owned here:

- deterministic nonprofit/domain logic from `public-core/`
- proprietary service implementations that belong in `private-platform/`
- Terraform, DNS, ALB, ECS, and other deployment wiring from `infrastructure/`

