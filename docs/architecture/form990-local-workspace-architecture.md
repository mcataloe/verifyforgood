# Form 990 Local-first Workspace Architecture

This document defines the local-first runtime model for Form 990 ingestion in
`backend/ingest/federal`.

The goal is to keep runtime behavior executable on a developer machine with the
same archive lifecycle assumptions that later map to ECS task containers.

## Design Goals

- run with local ephemeral disk first
- keep archive processing deterministic and debuggable
- avoid coupling orchestration logic to ECS-specific APIs
- process one archive at a time inside a workspace
- delete extracted XML files as soon as archive-scoped processing completes
- delete the ZIP file after archive processing completes
- keep PostgreSQL persistence compatible with the current backend runtime split
- align the default storage budget with 32 GiB ECS ephemeral storage

## Workspace Contract

The runtime works inside a configurable workspace root from
`FORM990_WORKSPACE_DIR`.

Canonical layout:

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

Meaning:

- `archives/`
  - archive ZIP files staged for one-at-a-time processing
- `extracted/{archive_name}/`
  - temporary XML extraction directory for the active archive only
- `logs/`
  - archive-scoped debug and operational log output
- `state/`
  - archive-scoped processing markers, manifests, and resumable local state

The backend-owned helper for this contract lives in
`verification.backend.ingest.federal.orchestration.workspace`.

## Runtime Module Map

Canonical backend-owned module seams:

- `discovery/`
  - source discovery, archive selection, and future diff-aware source policies
- `metadata/`
  - archive descriptors, processing metadata, and retention contracts
  - remote archive `HEAD` metadata normalization and persisted change-detection decisions
- `download/`
  - archive acquisition into `workspace/archives/`
- `extract/`
  - archive expansion into `workspace/extracted/{archive_name}/`
- `hashing/`
  - archive and artifact fingerprints for idempotency and integrity checks
  - deterministic XML content hashes used to skip unchanged extracted files
- `parse/`
  - XML parsing seams layered over reusable `verification.backend.ingest.federal.form990` logic
- `persist/`
  - PostgreSQL-backed nonprofit persistence and write-facing adapters
  - PostgreSQL-backed archive metadata and extracted-file hash state
- `cleanup/`
  - deterministic cleanup of extracted XML and processed ZIP files
- `orchestration/`
  - workspace lifecycle, archive-at-a-time control flow, and runtime assembly
- `cli.py`
  - local developer command surface
- `entrypoints/` and `entrypoint.py`
  - env-aware process bootstrap for local execution and future container entrypoints

## Current Migration Boundary

This phase defines the architecture and scaffolding, not the full logic
relocation.

Current live logic now routes through:

- `backend/ingest/federal/src/verification/backend/ingest/federal/monthly/worker.py`
- `backend/ingest/federal/src/verification/backend/ingest/federal/persistence.py`
- `backend/ingest/federal/src/verification/backend/ingest/federal/form990/`

New runtime work should keep moving responsibilities into the workspace-oriented
seams instead of reintroducing Lambda/S3-era runtime hosts.

Current Phase 27F note:

- archive metadata and extracted-file hash tracking now live in PostgreSQL for
  the monthly task runtime
- unchanged archives can be skipped from remote `HEAD` metadata when the
  upstream source URL is available in schedule context
- unchanged extracted XML members can be skipped from deterministic normalized
  file hashes
- the active backend monthly runtime no longer depends on the older TEOS S3
  manifest or S3-backed raw-XML state

## Local And ECS Mapping

Local development:

- default example root: `./.workspace/form990`
- local runs use the same `archives/`, `extracted/`, `logs/`, and `state/`
  structure
- VS Code or direct CLI debugging should target
  `python -m verification.backend.ingest.federal.cli run`

Container and ECS mapping:

- default container root: `/tmp/charity-status/form990`
- `FORM990_WORKSPACE_MAX_BYTES` defaults to `34359738368`
- that budget matches the intended 32 GiB ECS ephemeral storage envelope
- ECS-specific task orchestration should inject the workspace root, not change
  the internal archive lifecycle

