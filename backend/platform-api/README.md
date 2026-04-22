# Backend Platform API Runtime

Target ownership for `backend/platform-api/`:

- platform/control-plane HTTP runtime host
- admin, ops, webhook, and machine-auth API surface
- ASGI app/bootstrap and startup wiring for the platform-facing API

Python package root:

- `backend/platform-api/src/verification_backend/platform_api/`
- canonical ASGI app import: `verification_backend.platform_api.app:app`
- local runtime entrypoint: `python -m verification_backend.platform_api.entrypoint`

Runtime ownership:

- public HTTP entrypoint: `verification_backend.platform_api.app:app`
- shared backend dispatch/runtime: `verification_backend.api.runtime.handle_api_event`
- platform route transport seam: `verification_backend.platform_api.transport`

Current phase posture:

- `backend/platform-api` is the runtime host for control-plane and operational routes
- route ownership is intentionally split from `backend/api`
- shared request handling still dispatches through the current backend runtime module while the codebase converges on cleaner service boundaries

Local run:

```powershell
python -m verification_backend.platform_api.entrypoint
```

Container build/run:

```powershell
docker build -f backend/platform-api/Dockerfile .
docker run -p 5622:8000 --env-file backend/.env.local <platform-api-image>
```

Container contract:

- long-lived HTTP service
- compose and local examples expose it on host port `5622`
- starts with `uvicorn verification_backend.platform_api.app:app`

Not owned here:

- Terraform, DNS, ALB, ECS, and other deployment wiring from `infrastructure/`
