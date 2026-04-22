# Backend Federal Ingest Runtime

`backend/ingest/federal/` is the runtime home for federal ingest workloads.

Ownership:

- EO/BMF local and ECS-style runtime entrypoints
- Form 990 monthly workspace runtime entrypoints
- federal ingest CLI surface and container contract

Python package root:

- `backend/ingest/federal/src/verification/backend/ingest/federal/`
- canonical CLI: `python -m verification.backend.ingest.federal.cli`
- canonical local commands:
  - `python -m verification.backend.ingest.federal.cli run`
  - `python -m verification.backend.ingest.federal.cli run-eo-bmf`
  - `python -m verification.backend.ingest.federal.cli ecs-run`
  - `python -m verification.backend.ingest.federal.cli ecs-run-eo-bmf`
  - `python -m verification.backend.ingest.federal.cli monthly-worker`

Local Form 990 runner:

- `run` executes the archive-at-a-time monthly worker path locally
- `ecs-run` executes the same orchestration path behind ECS-style env wiring
- `--archive-url <url>` processes one ZIP directly without discovery
- `--single-archive` stops after the first selected ZIP archive
- `--limit <n>` caps the number of selected ZIP archives
- `--strict` stops on the first archive or XML failure
- `--keep-temp` preserves downloaded ZIPs and extracted XML in the workspace
- `--workspace <path>` overrides `FORM990_WORKSPACE_DIR` for that run
- `--xml-parser-workers <n>` overrides the bounded local XML parser worker pool

Local EO/BMF runner:

- `run-eo-bmf` downloads `eo1.csv` through `eo4.csv` into a local workspace and upserts canonical nonprofit rows into PostgreSQL
- `ecs-run-eo-bmf` reuses the same runtime core behind ECS-style env wiring
- `--strict` stops on the first file failure
- `--keep-temp` preserves downloaded CSVs in the workspace
- `--workspace <path>` overrides `EOBMF_WORKSPACE_DIR` for that run

Container contract:

- image entrypoint: `python -m verification.backend.ingest.federal.cli`
- default command: `monthly-worker`
- deployment model: ECS task definition invoked by schedules or one-off runs
- supported command overrides:
  - `ecs-run`
  - `ecs-run-eo-bmf`
  - `monthly-worker`

Docker examples:

```powershell
docker build -f backend/ingest/federal/Dockerfile -t verification-federal-ingest .
docker run --env-file backend/.env.local verification-federal-ingest
docker run --env-file backend/.env.local verification-federal-ingest run-eo-bmf
docker run --env-file backend/.env.local verification-federal-ingest run --archive-url https://example.org/2026_TEOS_XML_02A.zip
docker run --env-file backend/.env.local verification-federal-ingest monthly-worker
```

Manual Docker runs with host-provided PostgreSQL:

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
  -e EOBMF_WORKSPACE_DIR=/tmp/charity-status/eo_bmf `
  -v "${PWD}\\backend\\ingest\\federal\\.workspace\\eo_bmf:/tmp/charity-status/eo_bmf" `
  verification-federal-ingest `
  run-eo-bmf --strict
```

Workspace model:

- Form 990 workspace root comes from `FORM990_WORKSPACE_DIR`
- EO/BMF workspace root comes from `EOBMF_WORKSPACE_DIR`
- default local Form 990 example: `./.workspace/form990`
- default container Form 990 example: `/tmp/charity-status/form990`

Form 990 workspace layout:

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

Canonical runtime modules:

- `eo_bmf_runner.py`
- `eo_bmf_ecs_runtime.py`
- `eo_bmf_ingest.py`
- `monthly/worker.py`
- `persistence.py`
- `orchestration/`
- `discovery/`
- `download/`
- `extract/`
- `parse/`
- `persist/`
- `cleanup/`
- `form990/`

The checked-in static manifest now lives at:

- `backend/ingest/federal/src/verification/backend/ingest/federal/form990/Form990Links.txt`
