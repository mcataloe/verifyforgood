# Backend Worker Runtime

Target ownership for `backend/worker/`:

- non-HTTP runtime hosts
- profile refresh job runtime composition
- future generic worker/background-job entrypoints
- shared worker bootstrap that is not specific to ingest-task execution

Python package root:

- `backend/worker/src/charity_status_backend/worker/`
- local scaffold entrypoint: `python -m charity_status_backend.worker.entrypoint`

Planned inbound migration:

- `infrastructure.lambda_refresh`
- future worker-oriented runtime wrappers that should not stay in deployment-only paths

Not owned here:

- Form 990 and EO ingest task hosts that belong in `backend/ingest-task/`
- reusable application/domain logic from `public-core/`
- private service implementations from `private-platform/`
