# Form 990 Ingest Refactor Plan

## 1. Current Flow

- `infrastructure/lambda_form990.py` supports:
  - explicit `records[]` -> direct ingest
  - legacy `index_url` / `index_urls` -> fetch index rows and ingest
  - discovery mode -> discover source artifacts, persist discovery state/diffs, and select source-stage work
- IRS-page discovery lives in `charity_status.form990.irs_page_discovery` and returns per-artifact ZIP/CSV source entries.
- Discovery state and discovery diff artifacts are already persisted separately from filing manifests.
- Orchestrated mode currently chunks source-stage work items, but workers only acknowledge them; raw source download persistence has not yet been implemented.

## 2. Gaps

- Raw IRS ZIP/CSV downloads are not yet persisted as source-of-truth artifacts.
- Download decisions are not yet based on a dedicated downloaded-source state.
- The worker path does not yet perform raw source artifact download/persistence.
- Raw source artifacts, extracted raw XML, and normalized datasets are not yet separated by dedicated storage helpers and prefixes.
- Terraform does not yet explicitly document and enforce the non-versioned raw-source retention strategy.

## 3. Target Flow

The long-term target flow remains:

`discovery -> raw source persistence -> CSV diff/reconciliation -> selected filing extraction from ZIP -> normalized parsing`

The previous implementation step was intentionally limited to the first stage and its persistence contract:

`discovery -> discovery-state persistence/diff -> schedule next source-stage work`

The current implementation step extends the pipeline to:

`discovery -> discovery-state persistence/diff -> raw source download/persistence -> downloaded-source state`

This step must not implement:

- ZIP parsing for filing extraction
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

## 6. Raw Source Persistence

- Persist original IRS CSV and ZIP files to S3 unchanged before any filing parsing occurs.
- Raw source artifacts must be stored under a dedicated prefix separate from:
  - extracted raw filing XML
  - normalized parsed datasets
- Raw source object keys must be deterministic and history-preserving. The key shape should include source year, source kind, logical archive key or filename, and source signature so changed IRS artifacts create new keys without requiring S3 versioning.
- Source download state must be tracked separately from discovery state. Download decisions must compare selected source artifacts against the latest downloaded-source state, not only against discovery diffs.
- Persist:
  - latest downloaded-source state
  - per-run source download manifest(s)
  - enough metadata to answer whether a source artifact is already present and can be skipped
- Stored source metadata should include at minimum:
  - source URL
  - source kind
  - source year
  - source signature
  - downloaded at
  - raw source S3 key
- If the source-data bucket is managed in Terraform here, versioning must be explicitly disabled or suspended for the bucket used for raw IRS source downloads. Historical retention must come from object naming, not bucket versioning.

## 7. Execution and Backward Compatibility

- Explicit `records[]` ingest remains supported.
- Legacy `index_url` / `index_urls` direct ingest remains supported when callers use that legacy entry path.
- `configured` source mode remains supported, but it should normalize configured entries into the same source artifact model used by IRS-page discovery.
- `irs_page` remains the preferred dynamic discovery mode.
- `inline` and `orchestrated` execution modes remain supported.
- In this phase:
  - discovery-mode execution should persist discovery state first
  - then determine which selected source artifacts require raw download
  - inline mode should download and persist those source artifacts directly
  - orchestrated mode should queue raw source download work items
  - filing parsing still remains out of scope

## 8. Files to Change

- `infrastructure/lambda_form990.py`
- `infrastructure/lambda_form990_worker.py`
- `infrastructure/charity_status/form990/irs_page_discovery.py`
- `infrastructure/charity_status/form990/discovery.py`
- `infrastructure/charity_status/form990/source_catalog.py`
- `infrastructure/charity_status/form990/source_downloads.py`
- `infrastructure/charity_status/form990/storage.py`
- `infrastructure/charity_status/form990/manifest.py` if source diff helpers belong there
- Terraform bucket/prefix wiring for raw source artifacts
- tests covering discovery, Lambda flow, storage, and worker behavior
- `README.md`

## 9. Risks

- Discovery-mode responses will change because this phase no longer performs filing ingestion after discovery.
- Existing tests that assume discovery mode ingests filings will need to be updated to the new phase boundary.
- Source identity must be stable enough to avoid false-positive diffs across runs.
- Configured source catalog compatibility must be preserved for old `year/index_url` entries.
- Download state must be independent from discovery state to avoid incorrectly skipping never-downloaded but unchanged sources.
- Raw source key design must preserve history without creating duplicate keys for the same signature.

## 10. Test Plan

- IRS-page discovery of CSV and ZIP links across mixed filename patterns
- multiple ZIP artifacts within the same year
- old-style and new-style filenames
- configured-source normalization into the common source artifact model
- discovery-state diff behavior for new/removed/changed sources
- raw ZIP download and S3 persistence
- raw CSV download and S3 persistence
- download skip behavior when downloaded-source state already matches source signature
- raw source key generation and manifest/state key generation
- inline raw source download behavior
- orchestrated raw source download queueing behavior
- worker compatibility with raw source download work items
- Terraform/infrastructure coverage for versioning-disabled expectations where feasible
