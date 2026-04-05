# Backend Ingest Task Runtime

Target ownership for `backend/ingest-task/`:

- EO/BMF ingest runtime host
- Form 990 monthly workspace runtime host
- ECS task entrypoints and local workspace runtime assembly for ingest workloads

Python package root:

- `backend/ingest-task/src/charity_status_backend/ingest_task/`
- local entrypoint module: `python -m charity_status_backend.ingest_task.entrypoint`
- local CLI:
  - `python -m ingest_task.cli run`
  - `python -m ingest_task.cli run --archive-url <url>`
  - `python -m charity_status_backend.ingest_task.cli run`
  - `python -m charity_status_backend.ingest_task.cli ecs-run`
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
docker run --env-file backend/.env.local <ingest-image> monthly-worker
```

Container contract:

- canonical ECS-aligned task image for ingest runtimes
- image entrypoint: `python -m charity_status_backend.ingest_task.cli`
- default command: `monthly-worker`
- deployment model: ECS task definition invoked by schedules or one-off runs,
  not a long-lived worker service
- supported command overrides:
  - `ecs-run`
  - `monthly-worker`
- managed ECS parity path now routes through `ecs-run`, which reuses the same
  orchestration core as local `run`

ECS/local parity env aliases:

- `DATABASE_URL` maps to `PLATFORM_POSTGRES_URL` when the native env is absent
- `WORKSPACE_PATH` maps to `FORM990_WORKSPACE_DIR` when the native env is absent
- `STRICT_MODE` maps to strict failure behavior
- `MAX_ARCHIVES` maps to the archive-processing limit
- `LOG_LEVEL` controls runtime log verbosity for the parity path

Backend-owned runtime modules:

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
- PostgreSQL-backed archive/file change tracking now owns the active monthly task path end to end
- future refactors should keep moving archive download, extraction, parsing, persistence, and cleanup responsibilities through the module map rather than reintroducing Lambda/S3-era runtime hosts

Planned inbound migration:

- `infrastructure.lambda_ingest`
- `infrastructure.monthly_ingest_worker`
- `infrastructure.nonprofit_ingest_persistence`

Temporary compatibility note:

- checked-in runtime assets such as `infrastructure/charity_status/form990/Form990Links.txt` may remain in their current paths until a later extraction phase moves them safely
- infrastructure-owned deployment wiring may continue to reference compatibility shims during the transition
- `infrastructure.monthly_ingest_worker` and `infrastructure.nonprofit_ingest_persistence` remain as thin compatibility adapters
- the ECS task definition should now align to this backend-owned image contract
  rather than an infrastructure-owned Dockerfile path
