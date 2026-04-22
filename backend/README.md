# Backend Runtime Layer

This directory is the executable backend runtime host layer for the repository.

Current role:

- define where long-lived backend runtimes live
- provide a first-class Python workspace for backend runtime development
- document ownership boundaries for API, worker, ingest-task, and shared runtime concerns

Target subdirectories:

- `backend/api/`
  - API server runtime host, ASGI bootstrap, request composition, health/readiness ownership
- `backend/worker/`
  - non-HTTP worker runtimes such as refresh jobs and future background workers
- `backend/ingest-task/`
  - EO/BMF and Form 990 task runtimes, including the monthly ECS worker and local workspace processing hosts
- `backend/shared/`
  - runtime-only shared bootstrap/config/logging/request helpers and compatibility exports

Python workspace layout:

- `backend/pyproject.toml`
  - single setuptools project for backend runtime scaffolding
- `backend/api/src/verification_backend/api/`
- `backend/worker/src/verification_backend/worker/`
- `backend/ingest-task/src/verification_backend/ingest_task/`
- `backend/shared/src/verification_backend/shared/`

Dependency direction:

- `backend/` may depend on `frontend/` contracts, `infrastructure/` runtime packages, and other backend subpackages where appropriate
- `infrastructure/` may deploy/package backend entrypoints, but backend logic should not depend on deployment-only modules
- `frontend/` must not import backend runtime code directly

Migration note:

- runtime bootstrap continues to live under `infrastructure/`
- backend runtime logic should continue to concentrate in `backend/`

Local development:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\infrastructure\requirements.txt -r .\infrastructure\requirements-dev.txt
python -m pip install -e .\backend
```

Local PostgreSQL workflow:

- use PostgreSQL 16 locally until infrastructure pins a deployed engine version
- use `backend/.env.local` as the canonical backend local env file
- start from `backend/.env.local.example` and keep `PLATFORM_POSTGRES_URL` as the primary local database setting
- set `PLATFORM_NONPROFIT_POSTGRES_URL` only when you want nonprofit/entity data and Form 990 ingest state on a separate database from customer accounts, billing, and organization settings

```powershell
Copy-Item .\backend\.env.local.example .\backend\.env.local
createdb verification_platform
createdb verification_nonprofit
python -m verification_backend.shared.local_dev db-upgrade
python -m verification_backend.shared.local_dev db-upgrade-nonprofit
python -m verification_backend.shared.local_dev db-current-nonprofit
python -m verification_backend.shared.local_dev db-current
```

The documented local database name is `verification_platform`. For a full local
reset, use `dropdb verification_platform`, `createdb verification_platform`,
then rerun `python -m verification_backend.shared.local_dev db-upgrade`.

If you enable a dedicated nonprofit database, provision that database
separately and run `python -m verification_backend.shared.local_dev
db-upgrade-nonprofit` after the platform migration step. The dedicated
nonprofit flow now has its own Alembic history plus destructive dev helpers:

- `python -m verification_backend.shared.local_dev db-reset-nonprofit`
- `python -m verification_backend.shared.local_dev db-cutover-nonprofit`

Those commands intentionally refuse to run unless
`PLATFORM_NONPROFIT_POSTGRES_*` is configured, so destructive nonprofit resets
or cutovers cannot accidentally target the shared platform database.

Scaffold runtime commands:

```powershell
python -m verification_backend.worker.entrypoint
python -m verification_backend.ingest_task.entrypoint
```

API local run:

```powershell
python -m verification_backend.api.entrypoint
```

VS Code fallback debug path:

```powershell
python -m debugpy --listen 5678 -m verification_backend.api.entrypoint
```

If the VS Code `Backend API` launch configuration exits immediately after
startup on Windows, start the API with the command above and use the
`Backend API (Attach)` launch configuration. The backend runtime itself should
stay up and continue serving the frontend while the debugger attaches over port
`5678`.

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
  - ECS-aligned long-lived worker service image
  - provisionable ECS service slot retained as a neutral future worker host
- `backend/ingest-task/Dockerfile`
  - ECS-aligned task image with command-based ingest runtime selection
  - ECS task-style runtime for scheduled and one-off ingest execution, distinct
    from the general worker service

Worker and ingest commands still intentionally exit with scaffold-only
messages. The API command now starts the backend-owned ASGI runtime directly.

The shared local env file is loaded automatically by backend entrypoints before
their env-driven runtime modules initialize. Future worker and ingest runtimes
should reuse that same `backend/.env.local` contract for local execution.

Ingest-task local run examples:

```powershell
python -m ingest_task.cli run
python -m ingest_task.cli run --archive-url https://example.org/2026_TEOS_XML_02A.zip --strict --keep-temp
python -m verification_backend.ingest_task.cli run --limit 1
python -m verification_backend.ingest_task.cli ecs-run
python -m verification_backend.ingest_task.cli monthly-worker
```

The local `run` command uses the monthly ECS worker archive-processing core and
the `FORM990_WORKSPACE_DIR` workspace contract. By default it cleans up the ZIP
and extracted XML after each archive unless `--keep-temp` is supplied.

The local `run` and ECS `ecs-run` paths now keep downloaded IRS ZIP/XML
artifacts in the ephemeral workspace only. Normalized persistence remains in
PostgreSQL, while raw IRS artifacts are no longer uploaded to S3 on that path.

The ECS parity path now uses `ecs-run`, which reuses the same orchestration
core as local `run` and accepts env aliases such as `WORKSPACE_PATH`,
`STRICT_MODE`, `MAX_ARCHIVES`, `LOG_LEVEL`, and `DATABASE_URL`.

Migration/source-of-truth note:

- `python -m verification_backend.shared.local_dev db-upgrade` is the
  backend-owned wrapper for local development
- `python -m verification_backend.shared.local_dev db-upgrade-nonprofit`
  applies the dedicated nonprofit Alembic history when
  `PLATFORM_NONPROFIT_POSTGRES_*` settings are used
- `python -m verification_backend.shared.local_dev db-reset-nonprofit`
  destructively recreates the dedicated nonprofit schema in dev
- `python -m verification_backend.shared.local_dev db-cutover-nonprofit`
  destructively reloads nonprofit/Form 990 rows from the platform database into
  the dedicated nonprofit database in dev
- `alembic upgrade head` remains the underlying schema source-of-truth command
- `alembic -c alembic_nonprofit.ini upgrade head` is the underlying dedicated
  nonprofit schema source-of-truth command
- local backfill/cutover utilities live under `verification_platform.runtime`:
  - `python -m verification_platform.runtime.customer_accounts_migration`
  - `python -m verification_platform.runtime.nonprofit_migration`

Container notes:

- use the repo root as the Docker build context
- keep image ownership in `backend/`, not `infrastructure/`
- GitLab CI now builds all three backend runtime images and publishes them to
  the Terraform-managed ECR repositories using commit-SHA tags
- the ingest-task image defaults to `monthly-worker`

