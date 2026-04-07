# Form 990 Canonical Raw Filing Store

This note captures the additive canonical raw filing store introduced for Form
990 ingest persistence.

## Decision

- `nonprofit_filings` remains the lean serving/projection row for common filing
  identity, parse status, and high-value numeric fields
- `nonprofit_raw_filings` becomes the durable parsed filing source of truth for
  canonical Form 990 content in PostgreSQL
- canonical filing content is stored as `raw_filing_json`
- exact XML bytes are not stored in the main relational row; instead the raw
  record keeps an immutable XML artifact/reference locator

## Canonical Payload Contract

- namespaces are stripped from keys
- repeated sibling groups are preserved as arrays
- XML attributes are preserved under `_attrs`
- non-empty mixed text is preserved under `_value`
- whitespace-only text nodes are omitted
- canonical JSON ordering is deterministic so the same filing produces the same
  payload shape across local and ECS runs

## Versioning And Identity

Each canonical raw filing row stores:

- nonprofit and filing linkage
- filing identity fields copied onto the row for direct lookup
- deterministic normalized XML content hash
- parser version
- canonicalization version

The row is unique on `(filing_id, xml_content_hash)` so a logical filing can
retain multiple canonical versions over time without changing the serving
contract in `nonprofit_filings`.

## Deferred Work

- graph-specific projections remain deferred
- form-type-specific extraction parity remains deferred for `990EZ`, `990PF`,
  and `990T`
- `nonprofit_filings.raw_payload` remains a compatibility projection until
  callers move to the canonical raw filing store
