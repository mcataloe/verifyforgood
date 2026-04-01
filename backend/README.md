# Backend Runtime Layer

This directory is the future executable runtime host layer for the repository.

Current role:

- define where long-lived backend runtimes will live as code moves out of `infrastructure/`
- document ownership boundaries for API, worker, ingest-task, and shared runtime concerns
- keep the runtime topology explicit without forcing a full handler migration yet

Target subdirectories:

- `backend/api/`
  - API server runtime host, ASGI bootstrap, request composition, health/readiness ownership
- `backend/worker/`
  - non-HTTP worker runtimes such as refresh jobs and future background workers
- `backend/ingest-task/`
  - EO/BMF and Form 990 task runtimes, including ECS task and queue/chunk-processing hosts
- `backend/shared/`
  - runtime-only shared bootstrap/config/logging/request helpers and compatibility exports

Dependency direction:

- `backend/` may depend on `public-core/` and `private-platform/`
- `backend/` must not become a replacement for `public-core/` or `private-platform/`
- `infrastructure/` may deploy/package backend entrypoints, but backend logic should not depend on deployment-only modules
- `frontend/` must not import backend runtime code directly

Migration note:

- live runtime entrypoints still remain under `infrastructure/lambda_*.py` in this phase
- those modules should shrink into compatibility shims as backend runtime hosts are introduced in later phases
