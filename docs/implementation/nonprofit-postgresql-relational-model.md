# Nonprofit PostgreSQL Relational Model

This note captures the additive nonprofit relational schema introduced for the
PostgreSQL foundation.

The current nonprofit runtime remains Athena-first for lookup, filings, search,
source views, and verification assembly. The DynamoDB materialized profile
cache also remains active. PostgreSQL now provides a normalized target schema
for future backfill and cutover work.

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
- nonprofit-to-child indexes for filings, sources, and compliance checks
- composite lookup indexes for latest filing/source/check retrieval
- provenance uniqueness on nonprofit source lineage

## Follow-On Work

This schema foundation does not yet:

- backfill from Athena or the materialized profile cache
- replace Athena nonprofit reads
- replace the DynamoDB serving cache
- add PostgreSQL-native nonprofit search behavior beyond the normalized name
  index
