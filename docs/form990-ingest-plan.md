# Form 990 Ingest Refactor Plan

## 1. Current Flow

- `infrastructure/lambda_form990.py` supports:
  - explicit `records[]` -> direct ingest
  - legacy `index_url` / `index_urls` -> fetch index rows and ingest
  - discovery mode -> discover sources, immediately fetch filing records, then ingest
- IRS-page discovery currently lives in `charity_status.form990.irs_page_discovery` and returns mixed ZIP/CSV link records.
- Discovery state is persisted, but the handler still proceeds directly into filing-level work in the same flow.
- Orchestrated mode chunks filing records, not source artifacts.

## 2. Gaps

- The current source model is too narrow. It does not represent each yearly artifact explicitly as a source catalog entry.
- IRS-page discovery groups links in a way that still pushes the system toward filing fetch/parsing instead of source-catalog-first orchestration.
- Discovery-state persistence exists, but there is no first-class diff output for new, removed, and changed sources.
- Discovery manifests and filing manifests are not clearly separated by stage semantics.
- Orchestrated mode queues filing chunks before the source catalog stage is formalized.

## 3. Target Flow

The long-term target flow remains:

`discovery -> raw source persistence -> CSV diff/reconciliation -> selected filing extraction from ZIP -> normalized parsing`

This implementation step is intentionally limited to the first stage and its persistence contract:

`discovery -> discovery-state persistence/diff -> schedule next source-stage work`

This step must not implement:

- ZIP parsing for filing extraction
- raw ZIP/CSV download persistence
- CSV filing reconciliation
- selected filing extraction
- normalized filing parsing changes

## 4. Source Catalog Model

Each discovered source artifact must capture:

- `source_year`
- `source_kind` (`csv_index` or `zip_archive`)
- `source_url`
- `source_filename`
- `source_archive_key`
- `discovered_at`
- `source_signature`
- optional `source_etag`
- optional `source_last_modified`
- `page_url`

Discovery must remain resilient to evolving IRS filenames and should key off yearly Form 990 CSV/ZIP link patterns published on the IRS downloads page, not hardcoded suffix enumerations.

Known filename examples the design must support:

- `index_{year}.csv`
- `{year}_TEOS_XML_01A.zip`
- `{year}_TEOS_XML_11B.zip`
- `{year}_TEOS_XML_11C.zip`
- `{year}_TEOS_XML_11D.zip`
- `{year}_TEOS_XML_CT1.zip`
- `download990xml_{year}_{n}.zip`

## 5. Persistence and Diffing

- Persist the full discovered source catalog as discovery state in S3.
- Persist a per-run discovery manifest representing the full catalog seen in that run.
- Persist a per-run discovery diff artifact with:
  - new sources
  - removed sources
  - changed sources
  - unchanged count
- Keep source manifests, filing manifests, and ops metadata separated.
- Do not rely on S3 versioning for historical retention. History must come from object keys/manifests.

## 6. Execution and Backward Compatibility

- Explicit `records[]` ingest remains supported.
- Legacy `index_url` / `index_urls` direct ingest remains supported when callers use that legacy entry path.
- `configured` source mode remains supported, but it should normalize configured entries into the same source artifact model used by IRS-page discovery.
- `irs_page` remains the preferred dynamic discovery mode.
- `inline` and `orchestrated` execution modes remain supported.
- In this phase, discovery-mode execution should stop after source-catalog persistence/diffing and only schedule source-stage work descriptors for later phases.

## 7. Files to Change

- `infrastructure/lambda_form990.py`
- `infrastructure/lambda_form990_worker.py`
- `infrastructure/charity_status/form990/irs_page_discovery.py`
- `infrastructure/charity_status/form990/discovery.py`
- `infrastructure/charity_status/form990/storage.py`
- `infrastructure/charity_status/form990/manifest.py` if source diff helpers belong there
- tests covering discovery, Lambda flow, storage, and worker behavior
- `README.md`

## 8. Risks

- Discovery-mode responses will change because this phase no longer performs filing ingestion after discovery.
- Existing tests that assume discovery mode ingests filings will need to be updated to the new phase boundary.
- Source identity must be stable enough to avoid false-positive diffs across runs.
- Configured source catalog compatibility must be preserved for old `year/index_url` entries.

## 9. Test Plan

- IRS-page discovery of CSV and ZIP links across mixed filename patterns
- multiple ZIP artifacts within the same year
- old-style and new-style filenames
- configured-source normalization into the common source artifact model
- discovery-state diff behavior for new/removed/changed sources
- inline discovery-mode response and persistence behavior
- orchestrated discovery-stage queueing behavior
- worker compatibility with source-stage work items
