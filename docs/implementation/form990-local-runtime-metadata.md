# Form 990 Local Runtime Metadata

The active Form 990 archive-at-a-time ingest path now treats PostgreSQL as the durable processing store and the workspace as the only transient artifact store.

Current active runtime behavior:

- archive ZIP files are downloaded from their HTTP source URL into the workspace
- ZIP files remain workspace-local on disk while XML members are processed
- the main thread lists processable ZIP members and queues lightweight member descriptors only
- XML parser workers read their assigned ZIP members into memory, hash, parse, persist, and release memory before taking the next member
- `FORM990_PERSIST_BATCH_SIZE` is enforced inside each worker's persistence buffer
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
- Form 990 ZIP artifacts stay in the workspace only; durable archive, extracted-file, and filing state lives in PostgreSQL
