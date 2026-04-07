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

`nonprofit_raw_filings`

- canonical parsed Form 990 content linked to the logical filing row
- JSONB source-of-truth payload for the full filing tree after deterministic
  XML-to-JSON canonicalization
- filing-version tracking through normalized XML content hashes and parser /
  canonicalization versions
- immutable XML artifact/reference location for replay without storing XML
  bytes on the main serving row

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
- upserts filing rows by natural filing identity instead of a Python-generated
  filing ID
- upserts filing provenance/source rows by source lineage keys
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

Current key model for the nonprofit/Form 990 slice:

- every table in the slice uses a database-generated `BIGINT` primary key
- natural unique constraints remain the upsert identity for nonprofit, filing,
  source, archive, extracted-file, and canonical raw-filing writes
- repository writes use PostgreSQL/SQLite `ON CONFLICT` semantics rather than
  Python-generated primary-key values

Phase 27Q extends the nonprofit/Form 990 slice with canonical raw filing
storage:

- `nonprofit_raw_filings`
  - one row per logical filing version keyed by `filing_id` plus normalized XML
    content hash
  - stores `raw_filing_json` as the durable parsed filing source of truth
  - keeps `nonprofit_filings` as the lean serving projection for stable query
    contracts

That metadata is now used by the monthly Form 990 task runtime to skip
unchanged remote archives when `schedule_context.source_url` is available and
to skip unchanged extracted XML files deterministically across local and ECS
execution.
