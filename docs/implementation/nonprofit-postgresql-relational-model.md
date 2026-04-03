# Nonprofit PostgreSQL Relational Model

This note captures the additive nonprofit relational schema introduced for the
PostgreSQL foundation.

The nonprofit runtime is now mixed:

- PostgreSQL can serve lookup, search, and filings through
  `PLATFORM_NONPROFIT_QUERY_BACKEND=postgres`
- verification assembly remains hybrid because enrichment and peer-benchmark
  calls still delegate to Athena
- source views, compliance, and federal-awards routes still remain
  enrichment-driven
- the DynamoDB materialized profile cache also remains active

## Canonical vs Source-Specific Data

Canonical nonprofit identity lives in `nonprofits`:

- stable EIN-centered identity
- canonical name and normalized name
- IRS status, deductibility, subsection, entity type, revocation, geography,
  and NTEE category
- source bookkeeping such as canonical source, source version, and last seen
  timestamp

Source-specific and provenance-heavy records live outside the canonical row:

- `nonprofit_filings` stores one-to-many filing facts per nonprofit
- `nonprofit_sources` stores provider/source provenance, freshness, and
  normalized/raw source payload fragments
- `compliance_checks` stores snapshot-style compliance and policy-evaluation
  outputs that are useful for serving, audit, or later materialization

## Table Roles

`nonprofits`

- canonical nonprofit identity
- unique EIN and indexed normalized name

`nonprofit_filings`

- filing-level records linked to a nonprofit
- structured filing facts for tax year, form type, filing date, parse status,
  and key numeric amounts
- optional raw filing payload JSON for fields not worth normalizing yet

`nonprofit_sources`

- explicit source provenance using `source_id`, `provider_name`, `category`,
  `record_id`, and freshness timestamps
- source/evaluation state fields used by the current nonprofit source views
- JSON payloads for normalized provider fragments and raw source payloads

`compliance_checks`

- one row per compliance or policy-evaluation snapshot
- stable columns for common status fields already exposed by current
  compliance and verification payloads
- JSON payloads for flags, reasons, evidence, summary, and related metadata

## Indexing Defaults

- unique index on `nonprofits.ein`
- name lookup index on `nonprofits.normalized_name`
- ordered lookup index on `nonprofits(normalized_name, ein)`
- nonprofit-to-child indexes for filings, sources, and compliance checks
- composite lookup indexes for latest filing/source/check retrieval
- PostgreSQL trigram search index on `nonprofits.normalized_name`
- provenance uniqueness on nonprofit source lineage

## Follow-On Work

This schema foundation does not yet:

- backfill from Athena or the materialized profile cache
- replace the remaining Athena-backed source, compliance, and federal-awards
  reads
- replace the DynamoDB serving cache
- add PostgreSQL-native nonprofit search behavior beyond the normalized name
  index

Phase 24F adds an opt-in PostgreSQL ingest persistence path for normalized Form
990 outputs. That path:

- upserts canonical nonprofit rows by EIN
- upserts filing rows with deterministic filing identifiers
- upserts filing provenance/source rows with archive and signature metadata
- leaves discovery manifests, raw-source storage, Athena reads, and the
  materialized serving cache unchanged

Phase 27F extends the nonprofit PostgreSQL slice with Form 990 ingest execution
metadata:

- `form990_archives`
  - one row per canonical archive source URL
  - stores normalized `ETag`, `Last-Modified`, `Content-Length`, response
    status, last checked timestamp, last processed timestamp, and runtime
    status
- `form990_extracted_files`
  - one row per extracted XML member per archive
  - stores deterministic normalized content hash, parse status, parsed
    timestamp, and optional error text

That metadata is now used by the monthly Form 990 task runtime to skip
unchanged remote archives when `schedule_context.source_url` is available and
to skip unchanged extracted XML files deterministically across local and ECS
execution.
