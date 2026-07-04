# Backend Runtime Layer

This directory is the executable backend runtime host layer for the repository.

Current role:

- define where long-lived backend runtimes live
- provide a first-class Python workspace for backend runtime development
- document ownership boundaries for API, platform-api, worker, federal-ingest, and shared runtime concerns

Target subdirectories:

- `backend/customer-api/`
  - API server runtime host, ASGI bootstrap, request composition, health/readiness ownership
- `backend/platform-api/`
  - platform/control-plane API runtime host for admin, ops, webhook, and machine-auth routes
- `backend/worker/`
  - non-HTTP worker runtimes such as refresh jobs and future background workers
- `backend/ingest/federal/`
  - EO/BMF and Form 990 task runtimes, including the monthly ECS worker and local workspace processing hosts
- `backend/shared/`
  - runtime-only shared bootstrap/config/logging/request helpers and compatibility exports

Python workspace layout:

- `backend/pyproject.toml`
  - single setuptools project for backend runtime scaffolding
- `backend/customer-api/src/verification/backend/customer/api/`
- `backend/platform-api/src/verification/backend/platform/api/`
- `backend/worker/src/verification/backend/worker/`
- `backend/ingest/federal/src/verification/backend/ingest/federal/`
- `backend/shared/src/verification/backend/shared/`

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
python -m verification.backend.shared.local_dev db-upgrade
python -m verification.backend.shared.local_dev db-upgrade-nonprofit
python -m verification.backend.shared.local_dev db-current-nonprofit
python -m verification.backend.shared.local_dev db-current
```

The documented local database name is `verification_platform`. For a full local
reset, use `dropdb verification_platform`, `createdb verification_platform`,
then rerun `python -m verification.backend.shared.local_dev db-upgrade`.

If you enable a dedicated nonprofit database, provision that database
separately and run `python -m verification.backend.shared.local_dev
db-upgrade-nonprofit` after the platform migration step. The dedicated
nonprofit flow now has its own Alembic history plus destructive dev helpers:

- `python -m verification.backend.shared.local_dev db-reset-nonprofit`
- `python -m verification.backend.shared.local_dev db-cutover-nonprofit` (deprecated — see below)

Those commands intentionally refuse to run unless
`PLATFORM_NONPROFIT_POSTGRES_*` is configured, so destructive nonprofit resets
or cutovers cannot accidentally target the shared platform database.

`db-cutover-nonprofit` is no longer usable: it works by reflecting the legacy
nonprofit tables off of the platform database, but Phase 28D
(`alembic/versions/20260703_000019_phase28d_drop_legacy_platform_nonprofit_tables.py`)
dropped those tables from the platform chain now that
`alembic_nonprofit` is the sole source of truth for nonprofit data.

Scaffold runtime commands:

```powershell
python -m verification.backend.worker.entrypoint
python -m verification.backend.ingest.federal.cli monthly-worker
```

API local run:

```powershell
python -m verification.backend.customer.api.entrypoint
```

Platform API local run:

```powershell
python -m verification.backend.platform.api.entrypoint
```

VS Code fallback debug path:

```powershell
python -m debugpy --listen 5678 -m verification.backend.customer.api.entrypoint
```

If the VS Code `Backend API` launch configuration exits immediately after
startup on Windows, start the API with the command above and use the
`Backend API (Attach)` launch configuration. The backend runtime itself should
stay up and continue serving the frontend while the debugger attaches over port
`5678`.

Container build contracts:

```powershell
docker build -f backend/customer-api/Dockerfile .
docker build -f backend/platform-api/Dockerfile .
docker build -f backend/worker/Dockerfile .
docker build -f backend/ingest/federal/Dockerfile .
```

Local compose contract:

```powershell
docker compose up --build marketing platform api platformapi
```

Local service map:

- `marketing`
  - host `http://localhost:5174`
  - canonical hostname target `www.verifyforgood.com`
- `platform`
  - host `http://localhost:3953`
  - canonical hostname target `platform.verifyforgood.com`
- `api`
  - host `http://localhost:5621`
  - canonical hostname target `api.verifyforgood.com`
- `platformapi`
  - host `http://localhost:5622`
  - canonical hostname target `platformapi.verifyforgood.com`

Runtime mapping:

- `backend/customer-api/Dockerfile`
  - customer-facing API service image
- `backend/platform-api/Dockerfile`
  - platform/control-plane API service image
- `backend/worker/Dockerfile`
  - ECS-aligned long-lived worker service image
  - provisionable ECS service slot retained as a neutral future worker host
- `backend/ingest/federal/Dockerfile`
  - ECS-aligned task image with command-based ingest runtime selection
  - ECS task-style runtime for scheduled and one-off ingest execution, distinct
    from the general worker service

Worker and ingest commands still intentionally exit with scaffold-only
messages. The API command now starts the backend-owned ASGI runtime directly.

The shared local env file is loaded automatically by backend entrypoints before
their env-driven runtime modules initialize. Future worker and ingest runtimes
should reuse that same `backend/.env.local` contract for local execution.

Federal ingest local run examples:

```powershell
python -m verification.backend.ingest.federal.cli run
python -m verification.backend.ingest.federal.cli run --archive-url https://example.org/2026_TEOS_XML_02A.zip --strict --keep-temp
python -m verification.backend.ingest.federal.cli run --limit 1
python -m verification.backend.ingest.federal.cli ecs-run
python -m verification.backend.ingest.federal.cli monthly-worker
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

Manual federal-ingest Docker runs:

```powershell
docker build -f backend/ingest/federal/Dockerfile -t verification-federal-ingest .
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e FORM990_WORKSPACE_DIR=/tmp/charity-status/form990 `
  -v "${PWD}\\backend\\ingest\\federal\\.workspace\\form990:/tmp/charity-status/form990" `
  verification-federal-ingest `
  run --archive-url https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_01A.zip --strict
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e FORM990_SOURCE_MODE=irs_page `
  -e FORM990_IRS_DOWNLOADS_PAGE_URL=https://www.irs.gov/charities-non-profits/form-990-series-downloads `
  -e FORM990_WORKSPACE_DIR=/tmp/charity-status/form990 `
  -v "${PWD}\\backend\\ingest\\federal\\.workspace\\form990:/tmp/charity-status/form990" `
  verification-federal-ingest `
  run --strict
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e FORM990_WORKSPACE_DIR=/tmp/charity-status/form990 `
  -v "${PWD}\\backend\\ingest\\federal\\.workspace\\form990:/tmp/charity-status/form990" `
  verification-federal-ingest `
  run --limit 1 --strict
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e EOBMF_WORKSPACE_DIR=/tmp/charity-status/eo_bmf `
  -v "${PWD}\\backend\\ingest\\federal\\.workspace\\eo_bmf:/tmp/charity-status/eo_bmf" `
  verification-federal-ingest `
  run-eo-bmf --strict
```

Containerized backend task runs must not use `localhost` database URLs. Inside
the container, override PostgreSQL hosts to `host.docker.internal`.

Migration/source-of-truth note:

- `python -m verification.backend.shared.local_dev db-upgrade` is the
  backend-owned wrapper for local development
- `python -m verification.backend.shared.local_dev db-upgrade-nonprofit`
  applies the dedicated nonprofit Alembic history when
  `PLATFORM_NONPROFIT_POSTGRES_*` settings are used
- `python -m verification.backend.shared.local_dev db-reset-nonprofit`
  destructively recreates the dedicated nonprofit schema in dev
- `python -m verification.backend.shared.local_dev db-cutover-nonprofit`
  (deprecated) previously reloaded nonprofit/Form 990 rows from the platform
  database into the dedicated nonprofit database in dev; the platform database
  no longer has those tables to reflect from (see Phase 28D above), so this
  command can no longer run
- `alembic upgrade head` remains the underlying schema source-of-truth command
- `alembic -c alembic_nonprofit.ini upgrade head` is the underlying dedicated
  nonprofit schema source-of-truth command
- local backfill/cutover utilities live under `verification.backend.shared.runtime`:
  - `python -m verification.backend.shared.runtime.customer_accounts_migration`
  - `python -m verification.backend.shared.runtime.nonprofit_migration`

Container notes:

- use the repo root as the Docker build context
- keep image ownership in `backend/`, not `infrastructure/`
- GitLab CI now builds the three existing backend runtime images and publishes them to
  the Terraform-managed ECR repositories using commit-SHA tags
- the federal-ingest image defaults to `monthly-worker`

