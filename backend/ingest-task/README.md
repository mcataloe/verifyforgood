# Backend Ingest Task Runtime

Target ownership for `backend/ingest-task/`:

- EO/BMF ingest runtime host
- Form 990 ingest/discovery runtime host
- Form 990 orchestration and chunk-processing task hosts
- ECS task entrypoints and queue/chunk-processing runtime assembly for ingest workloads

Python package root:

- `backend/ingest-task/src/charity_status_backend/ingest_task/`
- local entrypoint module: `python -m charity_status_backend.ingest_task.entrypoint`
- local CLI:
  - `python -m ingest_task.cli run`
  - `python -m ingest_task.cli run --archive-url <url>`
  - `python -m charity_status_backend.ingest_task.cli run`
  - `python -m charity_status_backend.ingest_task.cli ecs-run`
  - `python -m charity_status_backend.ingest_task.cli form990`
  - `python -m charity_status_backend.ingest_task.cli form990-worker`
  - `python -m charity_status_backend.ingest_task.cli form990-orchestrator`
  - `python -m charity_status_backend.ingest_task.cli monthly-staging`
  - `python -m charity_status_backend.ingest_task.cli monthly-worker`

Local Form 990 debug runner:

- `run` executes the archive-at-a-time monthly worker processing path locally
- `ecs-run` executes the same archive-at-a-time orchestration path for ECS task entrypoints using env-driven options
- `--archive-url <url>` processes one ZIP archive directly without discovery
- `--single-archive` stops after the first selected ZIP archive
- `--limit <n>` caps the number of selected ZIP archives
- `--strict` stops on the first archive or XML failure and includes stack traces
- `--keep-temp` preserves the downloaded ZIP and extracted XML in the workspace
- `--workspace <path>` overrides `FORM990_WORKSPACE_DIR` for that run only
- the local runner is a thin wrapper over the monthly ECS worker processing core, not a separate ingest implementation
- the `run` and `ecs-run` paths now keep IRS ZIP/XML handling off S3 and use only the local workspace plus PostgreSQL-backed persistence

Container build/run:

```powershell
docker build -f backend/ingest-task/Dockerfile .
docker run --env-file backend/.env.local <ingest-image>
docker run --env-file backend/.env.local <ingest-image> run --archive-url https://example.org/2026_TEOS_XML_02A.zip
docker run --env-file backend/.env.local <ingest-image> form990
docker run --env-file backend/.env.local <ingest-image> form990-worker
docker run --env-file backend/.env.local <ingest-image> form990-orchestrator
```

Container contract:

- canonical ECS-aligned task image for ingest runtimes
- image entrypoint: `python -m charity_status_backend.ingest_task.cli`
- default command: `monthly-worker`
- deployment model: ECS task definition invoked by schedules or one-off runs,
  not a long-lived worker service
- supported command overrides:
  - `ecs-run`
  - `form990`
  - `form990-worker`
  - `form990-orchestrator`
  - `monthly-staging`
  - `monthly-worker`
- monthly staging remains Lambda-oriented even though the CLI supports local
  invocation of the staging runtime shape
- managed ECS parity path now routes through `ecs-run`, which reuses the same
  orchestration core as local `run`

ECS/local parity env aliases:

- `DATABASE_URL` maps to `PLATFORM_POSTGRES_URL` when the native env is absent
- `WORKSPACE_PATH` maps to `FORM990_WORKSPACE_DIR` when the native env is absent
- `STRICT_MODE` maps to strict failure behavior
- `MAX_ARCHIVES` maps to the archive-processing limit
- `LOG_LEVEL` controls runtime log verbosity for the parity path

Backend-owned runtime modules:

- `form990/runtime.py`
  - primary Form 990 discovery and orchestration runtime
- `form990/worker.py`
  - Form 990 chunk-processing worker runtime
- `form990/orchestrator.py`
  - compatibility orchestrator entrypoint
- `monthly/staging.py`
  - monthly staging Lambda runtime ownership
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
  - XML parsing seams layered over reusable `charity_status.form990` logic
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
- reusable parser and batch-processing logic under `infrastructure/charity_status/form990/` still remains in place while the runtime migrates toward the new module seams
- `form990/runtime.py` and `form990/worker.py` still own the live compatibility behavior today, but future refactors should move archive download, extraction, parsing, persistence, and cleanup responsibilities through the new module map rather than adding more logic directly to the runtime hosts
- PostgreSQL-backed archive/file change tracking is now owned here for the monthly task path; broader TEOS manifest retirement remains an incremental follow-on step while compatibility shims still exist

Planned inbound migration:

- `infrastructure.lambda_ingest`
- `infrastructure.lambda_form990`
- `infrastructure.lambda_form990_orchestrator`
- `infrastructure.lambda_form990_worker`

Temporary compatibility note:

- checked-in runtime assets such as `infrastructure/charity_status/form990/Form990Links.txt` may remain in their current paths until a later extraction phase moves them safely
- infrastructure-owned deployment wiring may continue to reference compatibility shims during the transition
- `infrastructure.lambda_form990`, `infrastructure.lambda_form990_worker`, `infrastructure.lambda_form990_orchestrator`, `infrastructure.lambda_monthly_ingest_staging`, `infrastructure.monthly_ingest_worker`, and `infrastructure.nonprofit_ingest_persistence` now remain as thin compatibility adapters
- the ECS task definition should now align to this backend-owned image contract
  rather than an infrastructure-owned Dockerfile path
