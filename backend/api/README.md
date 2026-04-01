# Backend API Runtime

Target ownership for `backend/api/`:

- primary API server runtime host
- ASGI app/bootstrap and startup wiring
- request composition and HTTP transport integration
- health and readiness endpoint ownership
- the eventual source of truth for the public API runtime once legacy Lambda rollback shims are retired

Python package root:

- `backend/api/src/charity_status_backend/api/`
- local scaffold entrypoint: `python -m charity_status_backend.api.entrypoint`

Planned inbound migration:

- `infrastructure.lambda_query`
- HTTP runtime-specific bootstrap currently assembled under `infrastructure/charity_status/platform/`
- shared transport helpers that should move into `backend/shared/`

Not owned here:

- deterministic nonprofit/domain logic from `public-core/`
- proprietary service implementations that belong in `private-platform/`
- Terraform, DNS, ALB, ECS, and other deployment wiring from `infrastructure/`
