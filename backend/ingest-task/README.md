# Backend Ingest Task Runtime

Target ownership for `backend/ingest-task/`:

- EO/BMF ingest runtime host
- Form 990 monthly workspace runtime host
- ECS task entrypoints and local workspace runtime assembly for ingest workloads

Python package root:

- `backend/ingest-task/src/verification_backend/ingest_task/`
- local entrypoint module: `python -m verification_backend.ingest_task.entrypoint`
- local CLI:
  - `python -m ingest_task.cli run`
  - `python -m ingest_task.cli run-eo-bmf`
  - `python -m ingest_task.cli run --archive-url <url>`
  - `python -m verification_backend.ingest_task.cli run`
  - `python -m verification_backend.ingest_task.cli run-eo-bmf`
  - `python -m verification_backend.ingest_task.cli ecs-run`
  - `python -m verification_backend.ingest_task.cli ecs-run-eo-bmf`
  - `python -m verification_backend.ingest_task.cli monthly-worker`

Local Form 990 debug runner:

- `run` executes the archive-at-a-time monthly worker processing path locally
- `ecs-run` executes the same archive-at-a-time orchestration path for ECS task entrypoints using env-driven options
- `--archive-url <url>` processes one ZIP archive directly without discovery
- `--single-archive` stops after the first selected ZIP archive
- `--limit <n>` caps the number of selected ZIP archives
- `--strict` stops on the first archive or XML failure and includes stack traces
- `--keep-temp` preserves the downloaded ZIP and extracted XML in the workspace
- `--workspace <path>` overrides `FORM990_WORKSPACE_DIR` for that run only
- `--xml-parser-workers <n>` overrides the local XML parser worker pool for the single-archive pipeline
- the local runner is a thin wrapper over the monthly ECS worker processing core, not a separate ingest implementation
- the `run` and `ecs-run` paths now keep IRS ZIP/XML handling off S3 and use only the local workspace plus PostgreSQL-backed persistence
- local runs may also set `FORM990_XML_PARSER_WORKERS` to tune the bounded XML parser worker pool when the CLI flag is not supplied

Local EO/BMF runner:

- `run-eo-bmf` downloads `eo1.csv` through `eo4.csv` into a local workspace and upserts canonical nonprofit rows into PostgreSQL
- `ecs-run-eo-bmf` reuses the same EO/BMF runtime core behind ECS-style env wiring
- `--strict` stops on the first file failure and includes stack traces
- `--keep-temp` preserves the downloaded CSVs in the workspace
- `--workspace <path>` overrides `EOBMF_WORKSPACE_DIR` for that run only
- the EO/BMF path is workspace-local and PostgreSQL-backed; it no longer uploads raw CSVs to S3

Container build/run:

```powershell
docker build -f backend/ingest-task/Dockerfile .
docker run --env-file backend/.env.local <ingest-image>
docker run --env-file backend/.env.local <ingest-image> run-eo-bmf
docker run --env-file backend/.env.local <ingest-image> run --archive-url https://example.org/2026_TEOS_XML_02A.zip
docker run --env-file backend/.env.local <ingest-image> monthly-worker
```

Manual Docker runs with host-provided PostgreSQL:

```powershell
docker build -f backend/ingest-task/Dockerfile -t verification-ingest-task .
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e FORM990_WORKSPACE_DIR=/tmp/charity-status/form990 `
  -v "${PWD}\\backend\\ingest-task\\.workspace\\form990:/tmp/charity-status/form990" `
  verification-ingest-task `
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
  -v "${PWD}\\backend\\ingest-task\\.workspace\\form990:/tmp/charity-status/form990" `
  verification-ingest-task `
  run --strict
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e FORM990_WORKSPACE_DIR=/tmp/charity-status/form990 `
  -v "${PWD}\\backend\\ingest-task\\.workspace\\form990:/tmp/charity-status/form990" `
  verification-ingest-task `
  run --limit 1 --strict
```

```powershell
docker run --rm `
  --env-file backend/.env.local `
  -e PLATFORM_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_platform `
  -e PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit `
  -e PLATFORM_NONPROFIT_QUERY_POSTGRES_URL=postgresql+psycopg://postgres:postgres@host.docker.internal:5432/verification_nonprofit_query `
  -e EOBMF_WORKSPACE_DIR=/tmp/charity-status/eo_bmf `
  -v "${PWD}\\backend\\ingest-task\\.workspace\\eo_bmf:/tmp/charity-status/eo_bmf" `
  verification-ingest-task `
  run-eo-bmf --strict
```

Containerized ingest runs must not use `localhost` for PostgreSQL. Override
database hosts to `host.docker.internal` so the container can reach the
host-provided databases.

Container contract:

- canonical ECS-aligned task image for ingest runtimes
- image entrypoint: `python -m verification_backend.ingest_task.cli`
- default command: `monthly-worker`
- deployment model: ECS task definition invoked by schedules or one-off runs,
  not a long-lived worker service
- supported command overrides:
  - `ecs-run`
  - `ecs-run-eo-bmf`
  - `monthly-worker`
- managed ECS parity path now routes through `ecs-run`, which reuses the same
  orchestration core as local `run`

ECS/local parity env aliases:

- `DATABASE_URL` maps to `PLATFORM_POSTGRES_URL` when the native env is absent
- `DATABASE_URL` also maps to `PLATFORM_NONPROFIT_POSTGRES_URL` when the native nonprofit URL is absent
- `WORKSPACE_PATH` maps to `FORM990_WORKSPACE_DIR` when the native env is absent
- `WORKSPACE_PATH` also maps to `EOBMF_WORKSPACE_DIR` for the EO/BMF runtime when the native env is absent
- `STRICT_MODE` maps to strict failure behavior
- `MAX_ARCHIVES` maps to the archive-processing limit
- `LOG_LEVEL` controls runtime log verbosity for the parity path

Backend-owned runtime modules:

- `eo_bmf_runner.py`
  - local EO/BMF runtime ownership and workspace-local CSV orchestration
- `eo_bmf_ecs_runtime.py`
  - ECS wrapper for the EO/BMF runtime
- `eo_bmf_ingest.py`
  - EO/BMF CSV parsing and PostgreSQL upsert mapping
- `monthly/worker.py`
  - monthly ECS worker runtime ownership
- `persistence.py`
  - shared nonprofit ingest persistence runtime helper

Local-first Form 990 workspace model:

- canonical workspace root comes from `FORM990_WORKSPACE_DIR`
- default local example: `./.workspace/form990`
- default container example: `/tmp/charity-status/form990`
- workspace layout:

```text
workspace/
  archives/
    {archive_name}.zip
  extracted/
    {archive_name}/
      *.xml
  logs/
  state/
```

- only one archive should be processed at a time inside a given workspace
- extracted XML files are expected to be deleted immediately after each XML has been parsed or skipped
- ZIP files are expected to be deleted after archive processing completes
- the local archive path now parses each extracted XML once and overlaps unzip plus parse work through a bounded in-archive worker pipeline
- the runtime keeps this model local-first so the same logic can run on a developer machine or inside ECS ephemeral storage
- current workspace helpers live under:
  - `orchestration/workspace.py`
  - `cleanup/`
  - `metadata/`

Form 990 local-first module map:

- `discovery/`
  - source discovery and archive-selection seams
- `metadata/`
  - archive-scoped runtime metadata and workspace retention contracts
  - archive `HEAD` probe normalization and change-detection helpers
- `download/`
  - archive acquisition into workspace `archives/`
- `extract/`
  - ZIP extraction into workspace `extracted/`
- `hashing/`
  - archive and payload fingerprint helpers
  - deterministic normalized XML SHA-256 hashing for extracted-file change detection
- `parse/`
  - XML parsing seams layered over reusable `verification.form990` logic
- `persist/`
  - PostgreSQL-backed nonprofit persistence entrypoints and adapters
  - archive metadata and extracted-file hash state used to skip unchanged work
- `cleanup/`
  - deterministic deletion of extracted XML and processed ZIP files
- `orchestration/`
  - workspace lifecycle, archive-at-a-time execution, and runtime coordination
- `cli.py`
  - local developer command surface
- `entrypoint.py`
  - env-aware local execution bootstrap

Current migration boundary:

- `backend/ingest-task` is now the canonical runtime architecture home for the local-first Form 990 workspace model
- reusable parser and batch-processing logic under `infrastructure/verification/form990/` still remains in place while the runtime migrates toward the new module seams
- PostgreSQL-backed archive/file change tracking now owns the active monthly task path end to end
- future refactors should keep moving archive download, extraction, parsing, persistence, and cleanup responsibilities through the module map rather than reintroducing Lambda/S3-era runtime hosts

Planned inbound migration:

- `infrastructure.eo_bmf_ingest_worker`
- `infrastructure.monthly_ingest_worker`
- `infrastructure.nonprofit_ingest_persistence`

Temporary compatibility note:

- checked-in runtime assets such as `infrastructure/verification/form990/Form990Links.txt` may remain in their current paths until a later extraction phase moves them safely
- infrastructure-owned deployment wiring may continue to reference compatibility shims during the transition
- `infrastructure.monthly_ingest_worker` and `infrastructure.nonprofit_ingest_persistence` remain as thin compatibility adapters
- the ECS task definition should now align to this backend-owned image contract
  rather than an infrastructure-owned Dockerfile path

