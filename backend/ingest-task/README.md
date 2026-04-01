# Backend Ingest Task Runtime

Target ownership for `backend/ingest-task/`:

- EO/BMF ingest runtime host
- Form 990 ingest/discovery runtime host
- Form 990 orchestration and chunk-processing task hosts
- ECS task entrypoints and queue/chunk-processing runtime assembly for ingest workloads

Planned inbound migration:

- `infrastructure.lambda_ingest`
- `infrastructure.lambda_form990`
- `infrastructure.lambda_form990_orchestrator`
- `infrastructure.lambda_form990_worker`

Temporary compatibility note:

- checked-in runtime assets such as `infrastructure/charity_status/form990/Form990Links.txt` may remain in their current paths until a later extraction phase moves them safely
- infrastructure-owned deployment wiring may continue to reference compatibility shims during the transition
