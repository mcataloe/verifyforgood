# Backend Runtime Layer

This directory is the executable backend runtime host layer for the repository.
It remains the future executable runtime host layer for runtime code that still
needs to move out of `infrastructure/`.

Current role:

- define where long-lived backend runtimes live as code moves out of `infrastructure/`
- provide a first-class Python workspace for backend runtime scaffolding and local development
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

Python workspace layout:

- `backend/pyproject.toml`
  - single setuptools project for backend runtime scaffolding
- `backend/api/src/charity_status_backend/api/`
- `backend/worker/src/charity_status_backend/worker/`
- `backend/ingest-task/src/charity_status_backend/ingest_task/`
- `backend/shared/src/charity_status_backend/shared/`

Dependency direction:

- `backend/` may depend on `public-core/` and `private-platform/`
- `backend/` must not become a replacement for `public-core/` or `private-platform/`
- `infrastructure/` may deploy/package backend entrypoints, but backend logic should not depend on deployment-only modules
- `frontend/` must not import backend runtime code directly

Migration note:

- live runtime entrypoints still remain under `infrastructure/lambda_*.py` in this phase
- those modules should shrink into compatibility shims as backend runtime hosts are introduced in later phases

Local development:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\infrastructure\requirements.txt -r .\infrastructure\requirements-dev.txt
python -m pip install -e .\public-core -e .\private-platform -e .\backend
```

Local PostgreSQL workflow:

- use PostgreSQL 16 locally until infrastructure pins a deployed engine version
- use `backend/.env.local` as the canonical backend local env file
- start from `backend/.env.local.example` and keep `PLATFORM_POSTGRES_URL` as the primary local database setting

```powershell
Copy-Item .\backend\.env.local.example .\backend\.env.local
createdb verification_platform
python -m charity_status_backend.shared.local_dev db-upgrade
python -m charity_status_backend.shared.local_dev db-current
```

The documented local database name is `verification_platform`. For a full local
reset, use `dropdb verification_platform`, `createdb verification_platform`,
then rerun `python -m charity_status_backend.shared.local_dev db-upgrade`.

Scaffold runtime commands:

```powershell
python -m charity_status_backend.worker.entrypoint
python -m charity_status_backend.ingest_task.entrypoint
```

API local run:

```powershell
python -m charity_status_backend.api.entrypoint
```

Container build contracts:

```powershell
docker build -f backend/api/Dockerfile .
docker build -f backend/worker/Dockerfile .
docker build -f backend/ingest-task/Dockerfile .
```

Runtime mapping:

- `backend/api/Dockerfile`
  - ECS-aligned long-lived API service image
- `backend/worker/Dockerfile`
  - ECS-aligned long-lived worker service placeholder
- `backend/ingest-task/Dockerfile`
  - ECS-aligned task image with command-based ingest runtime selection

Worker and ingest commands still intentionally exit with scaffold-only
messages. The API command now starts the backend-owned ASGI runtime while
`infrastructure.lambda_query` remains a narrow rollback adapter.

The shared local env file is loaded automatically by backend entrypoints before
their env-driven runtime modules initialize. Future worker and ingest runtimes
should reuse that same `backend/.env.local` contract for local execution.

Ingest-task local run examples:

```powershell
python -m charity_status_backend.ingest_task.cli form990
python -m charity_status_backend.ingest_task.cli form990-worker
python -m charity_status_backend.ingest_task.cli monthly-staging
python -m charity_status_backend.ingest_task.cli monthly-worker
```

Migration/source-of-truth note:

- `python -m charity_status_backend.shared.local_dev db-upgrade` is the
  backend-owned wrapper for local development
- `alembic upgrade head` remains the underlying schema source-of-truth command
- local backfill/cutover utilities still run from `private-platform`:
  - `python -m charity_status_platform.runtime.customer_accounts_migration`
  - `python -m charity_status_platform.runtime.nonprofit_migration`

Container notes:

- use the repo root as the Docker build context
- keep image ownership in `backend/`, not `infrastructure/`
- the ingest-task image defaults to `monthly-worker` and supports later ECS
  command overrides such as `form990`, `form990-worker`, and
  `form990-orchestrator`
