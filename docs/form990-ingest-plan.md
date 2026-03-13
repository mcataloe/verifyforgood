# Form 990 Ingest Refactor Plan

## 1. Current Flow

- `infrastructure/lambda_form990.py` supports:
  - explicit `records[]` -> direct ingest
  - legacy `index_url` / `index_urls` -> fetch index rows and ingest
  - discovery mode -> discover source artifacts, persist discovery state/diffs, persist raw source artifacts, reconcile CSV filing catalog, and select filing work
- IRS-page discovery lives in `charity_status.form990.irs_page_discovery` and returns per-artifact ZIP/CSV source entries.
- Discovery state and discovery diff artifacts are already persisted separately from filing manifests.
- Raw source ZIP/CSV download persistence is implemented and tracked via downloaded-source state.
- Filing reconciliation from downloaded yearly CSV indexes is implemented and tracked via filing catalog/diff/state manifests.
- Selected filings are now resolved/extracted from raw ZIP artifacts first, with explicit URL fallback only when ZIP-member resolution fails.

## 2. Gaps

- Structured observability is still thin across discovery/download/reconciliation/ZIP extraction and worker chunk lifecycle.
- Retry/error categorization is not explicit enough for transient download failures, malformed ZIPs, ZIP-miss fallbacks, and chunk retries.
- Resume behavior is present but needs hardening for chunk idempotency and clearer checkpoints.
- Runtime configuration validation and infrastructure/IAM operational assumptions need explicit guardrails and documentation.

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

The CSV reconciliation step now extends the pipeline to:

`discovery -> discovery-state persistence/diff -> raw source download/persistence -> downloaded-source state -> CSV filing reconciliation -> selected filing ingest`

The next implementation step should extend the pipeline to:

`discovery -> raw source persistence -> CSV diff/reconciliation -> selected filing extraction from ZIP -> normalized parsing`

with explicit fallback to direct XML URL only when ZIP-member resolution fails for a selected filing.

The current hardening step focuses on production safety for the implemented flow:

`discovery -> raw source persistence -> CSV diff/reconciliation -> selected filing extraction from ZIP -> normalized parsing`

including structured logging, explicit retries/error handling, resumability/idempotency, configuration validation, and operational documentation.

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

## 7. Filing Reconciliation

- Yearly CSV indexes are the authoritative filing catalog for incremental Form 990 selection.
- CSV reconciliation must read the persisted raw CSV source artifacts already downloaded for the selected years.
- CSV row parsing must normalize the IRS shapes already observed in the repo:
  - header-based CSV rows (`EIN`, `TaxYr`, `FilingDt`, `ReturnType`, `ObjectId`, `URL`)
  - upper-snake variations (`TAX_YR`, `FILING_DT`, `OBJECT_ID`, `XML_URL`)
  - positional export rows beginning with `.EFILE`
- Filing identity should prioritize `irs_object_id` when present and otherwise fall back to a deterministic composite of:
  - `ein`
  - `tax_year`
  - `return_type`
  - `filing_date`
  - `source_year`
  - `source_archive`
- Filing change detection should use a CSV-derived filing signature built from the normalized filing metadata, not from ZIP contents.
- Filing state must be persisted separately from source discovery/download state and must track, per filing:
  - filing identity
  - filing signature
  - normalized filing metadata from CSV
  - whether the raw source CSV was present
  - whether raw filing XML has been extracted/persisted
  - whether normalized outputs are complete
  - latest parse status / terminal outcome
- Completion criteria must be explicit:
  - `parsed` filings are complete only when the filing state records the normalized dataset artifact keys written by ingest
  - terminal non-parse outcomes such as `unsupported_return_type` may be treated as complete when explicitly recorded in filing state
  - `index_only`, missing-output, or failed parse states are incomplete and must be re-selected
- Reconciliation should replace filing state for the years inspected in the current run while preserving prior state for years not inspected.
- Per-run reconciliation artifacts should include:
  - the CSV-derived filing catalog seen for that run
  - the filing diff summary (`new`, `changed`, `unchanged`, `incomplete`)
  - the selected filing set scheduled for downstream processing

## 8. Execution and Backward Compatibility

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
- In the CSV reconciliation phase:
  - explicit `records[]` and legacy direct `index_url` entry paths remain unchanged
  - source-catalog execution must reconcile selected filings from downloaded CSV indexes before downstream ingest
  - inline mode may immediately ingest only the selected filings through the existing direct `xml_url` path
  - orchestrated mode should write chunks containing only selected filings so workers process those selected filings only
- In the ZIP extraction phase:
  - selected filing processing should use raw ZIP artifacts from S3 as the primary XML source
  - extraction should target only needed XML members for selected filings (not full ZIP parse)
  - fallback to direct `xml_url` is allowed only when ZIP-member mapping fails and URL is available
  - inline and worker chunk execution should remain retry-safe and resumable

## 9. Files to Change

- `infrastructure/lambda_form990.py`
- `infrastructure/lambda_form990_worker.py`
- `infrastructure/charity_status/form990/irs_page_discovery.py`
- `infrastructure/charity_status/form990/discovery.py`
- `infrastructure/charity_status/form990/source_catalog.py`
- `infrastructure/charity_status/form990/source_downloads.py`
- `infrastructure/charity_status/form990/index.py`
- `infrastructure/charity_status/form990/filing_reconciliation.py`
- `infrastructure/charity_status/form990/zip_selected_processing.py`
- `infrastructure/charity_status/form990/zip_processing.py`
- `infrastructure/charity_status/form990/ingest.py`
- `infrastructure/charity_status/form990/storage.py`
- `infrastructure/charity_status/form990/manifest.py` if source diff helpers belong there
- Terraform bucket/prefix wiring for raw source artifacts
- tests covering discovery, Lambda flow, storage, and worker behavior
- `README.md`

## 10. Risks

- Discovery-mode responses will change because this phase no longer performs filing ingestion after discovery.
- Existing tests that assume discovery mode ingests filings will need to be updated to the new phase boundary.
- Source identity must be stable enough to avoid false-positive diffs across runs.
- Configured source catalog compatibility must be preserved for old `year/index_url` entries.
- Download state must be independent from discovery state to avoid incorrectly skipping never-downloaded but unchanged sources.
- Raw source key design must preserve history without creating duplicate keys for the same signature.
- Filing identity fallback must be stable enough to avoid false-positive reprocessing when `irs_object_id` is missing.
- Completion-state tracking must not regress explicit/legacy direct ingest by causing already-parsed filings to be re-selected indefinitely.
- ZIP member resolution may fail for some legacy/malformed entries; fallback behavior must be explicit and observable.
- ZIP extraction must avoid accidentally scanning/parsing all members for every run, which can regress runtime and cost.
- Record-to-ZIP mapping heuristics must stay deterministic across TEOS and download990xml/CT1 naming eras.
- Current Terraform IAM policy is intentionally broad (`s3:*`, `sqs:*`) and should be narrowed in a follow-up least-privilege hardening effort.

## 11. Test Plan

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
- CSV row normalization across header-based, upper-snake, and positional IRS index shapes
- filing identity generation and filing-signature diff behavior
- new CSV rows selected for processing
- unchanged CSV rows skipped
- changed CSV rows selected for reprocessing
- incomplete or missing normalized-output state causing a filing to be re-selected
- mixed-year reconciliation where only inspected years are replaced in latest filing state
- current + previous year incremental window behavior
- explicit-records and legacy direct-index backward compatibility after filing state persistence is added
- selected filing to ZIP member resolution by `irs_object_id` and source metadata hints
- ZIP subset extraction only for selected filings
- fallback to direct XML URL when ZIP member cannot be resolved
- TEOS and legacy ZIP naming-era coverage for resolver behavior
- worker chunk processing using ZIP-backed extraction path
- structured logging and stage counters for discovery/download/reconciliation/ZIP extraction
- transient-download retry behavior (source and fallback URL paths)
- malformed ZIP handling with explicit error categorization
- chunk resume/idempotency behavior when result artifact already exists
- partial worker failure handling and run summary consistency
- configuration validation guardrails for required env vars and sane numeric defaults
