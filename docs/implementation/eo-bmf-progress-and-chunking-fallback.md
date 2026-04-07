# EO/BMF Progress Tuning And Chunking Fallback

EO/BMF local ingest now treats live terminal progress and throughput tuning as separate concerns:

- single-worker runs keep per-file row progress with ETA
- multi-worker runs render one aggregate row-progress line owned by the coordinator thread
- structured JSON logs remain the operational source of truth

## Phase 5 Tuning Baseline

Measure these scenarios before considering any architectural change:

1. `workers=1`, `batch_size=500`
2. `workers=4`, `batch_size=500`
3. `workers=4`, smaller batch size
4. `workers=4`, larger batch size

Track:

- per-file row counts
- per-file download, map, and DB durations
- aggregate rows per second
- aggregate files per second
- worker count and batch size

The tuning goal is to improve rows/sec without making progress stale, increasing DB failures, or weakening file-level rerun safety.

## Chunking Fallback Trigger

Do not implement merged-file chunking unless tuning shows file-level parallelism is still leaving substantial wall-clock time on the table. Consider chunking only when one or more of these conditions remain true after tuning:

- one or two IRS files dominate total run time
- worker utilization stays poor because file sizes are badly skewed
- DB throughput is no longer the bottleneck, but CPU or row mapping still leaves workers idle

## Chunking Fallback Shape

If chunking becomes necessary later, use this shape:

- preserve original IRS file attribution in every chunk manifest
- create chunk manifests during preprocessing rather than changing the nonprofit schema
- reuse the existing EO/BMF batch persistence seam for chunk execution
- treat chunk reruns as idempotent restart-from-beginning work
- do not require mid-chunk resume

Until those triggers are met, file-per-worker remains the preferred EO/BMF architecture.
