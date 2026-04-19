# Backend Worker Runtime

Target ownership for `backend/worker/`:

- non-HTTP runtime hosts
- profile refresh job runtime composition
- future generic worker/background-job entrypoints
- shared worker bootstrap that is not specific to ingest-task execution

Python package root:

- `backend/worker/src/verification_backend/worker/`
- local scaffold entrypoint: `python -m verification_backend.worker.entrypoint`

Container build/run:

```powershell
docker build -f backend/worker/Dockerfile .
docker run --env-file backend/.env.local <worker-image>
```

Container contract:

- long-lived non-HTTP worker/service image shape
- default command: `python -m verification_backend.worker.entrypoint`
- intended Terraform/ECS mapping: private-subnet ECS service with no ALB
- Terraform now exposes a disabled-by-default service slot so the deployment
  boundary exists before runtime ownership fully moves here
- intentionally scaffold-only until `infrastructure.lambda_refresh` runtime
  ownership moves into `backend/worker`

Planned inbound migration:

- `infrastructure.lambda_refresh`
- future worker-oriented runtime wrappers that should not stay in deployment-only paths

Not owned here:

- Form 990 and EO ingest task hosts that belong in `backend/ingest-task/`
- reusable application/domain logic from `public-core/`
- private service implementations from `private-platform/`

