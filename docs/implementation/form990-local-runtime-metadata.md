# Form 990 Local Runtime Metadata

The active Form 990 archive-at-a-time ingest path now treats PostgreSQL as the durable processing store and the workspace as the only transient artifact store.

Current active runtime behavior:

- archive ZIP files are downloaded from their HTTP source URL into the workspace
- extracted XML files remain workspace-local and are deleted after parsing
- the local archive path now parses each extracted XML once and overlaps unzip plus parse work through a bounded local worker pool
- `form990_archives` stores HTTP probe metadata plus processing lifecycle timestamps
- `form990_extracted_files` stores per-member content hashes and parse status
- `nonprofit_filings` stores `raw_file_reference` instead of an S3-specific key

Archive lifecycle fields:

- `update_started_at`: when processing for the archive started
- `update_ended_at`: when processing finished
- `processing_duration_ms`: total elapsed processing time in milliseconds
- `last_processed_at`: last completion timestamp, including failed runs

Current posture:

- the backend-owned monthly runtime no longer depends on legacy S3-backed Form 990 orchestration, reconciliation, or manifest state modules
- Form 990 transient artifacts now stay in the workspace only; durable state lives in PostgreSQL
