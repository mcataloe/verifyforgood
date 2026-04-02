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
  - `python -m charity_status_backend.ingest_task.cli form990`
  - `python -m charity_status_backend.ingest_task.cli form990-worker`
  - `python -m charity_status_backend.ingest_task.cli form990-orchestrator`
  - `python -m charity_status_backend.ingest_task.cli monthly-staging`
  - `python -m charity_status_backend.ingest_task.cli monthly-worker`

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

Planned inbound migration:

- `infrastructure.lambda_ingest`
- `infrastructure.lambda_form990`
- `infrastructure.lambda_form990_orchestrator`
- `infrastructure.lambda_form990_worker`

Temporary compatibility note:

- checked-in runtime assets such as `infrastructure/charity_status/form990/Form990Links.txt` may remain in their current paths until a later extraction phase moves them safely
- infrastructure-owned deployment wiring may continue to reference compatibility shims during the transition
- `infrastructure.lambda_form990`, `infrastructure.lambda_form990_worker`, `infrastructure.lambda_form990_orchestrator`, `infrastructure.lambda_monthly_ingest_staging`, `infrastructure.monthly_ingest_worker`, and `infrastructure.nonprofit_ingest_persistence` now remain as thin compatibility adapters
