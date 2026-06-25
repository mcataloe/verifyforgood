# Backend Platform API Runtime

Target ownership for `backend/platform-api/`:

- platform/control-plane HTTP runtime host
- admin, ops, webhook, and machine-auth API surface
- ASGI app/bootstrap and startup wiring for the platform-facing API

Python package root:

- `backend/platform-api/src/verification/backend/platform/api/`
- canonical ASGI app import: `verification.backend.platform.api.app:app`
- local runtime entrypoint: `python -m verification.backend.platform.api.entrypoint`

Runtime ownership:

- public HTTP entrypoint: `verification.backend.platform.api.app:app`
- shared backend dispatch/runtime: `verification.backend.customer.api.runtime.handle_api_event`
- platform route transport seam: `verification.backend.platform.api.transport`

Current phase posture:

- `backend/platform-api` is the runtime host for control-plane and operational routes
- route ownership is intentionally split from `backend/customer-api`
- shared request handling still dispatches through the current backend runtime module while the codebase converges on cleaner service boundaries

Local run:

```powershell
python -m verification.backend.platform.api.entrypoint
```

Container build/run:

```powershell
docker build -f backend/platform-api/Dockerfile .
docker run -p 5622:8000 --env-file backend/.env.local <platform-api-image>
```

Container contract:

- long-lived HTTP service
- compose and local examples expose it on host port `5622`
- starts with `uvicorn verification.backend.platform.api.app:app`

Not owned here:

- Terraform, DNS, ALB, ECS, and other deployment wiring from `infrastructure/`
