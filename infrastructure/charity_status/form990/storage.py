from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def normalized_metadata_key(prefix: str, now: datetime | None = None) -> str:
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    base = prefix.strip("/")
    return f"{base}/metadata_{ts}.jsonl"


def normalized_dataset_key(prefix: str, dataset_name: str, now: datetime | None = None) -> str:
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    base = prefix.strip("/")
    return f"{base}/{dataset_name}_{ts}.jsonl"


def manifest_key(prefix: str, now: datetime | None = None) -> str:
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    base = prefix.strip("/")
    return f"{base}/manifest_{ts}.json"


def discovery_manifest_key(prefix: str, run_id: str) -> str:
    base = prefix.strip("/")
    return f"{base}/discovery/runs/{run_id}/catalog.json"


def discovery_diff_key(prefix: str, run_id: str) -> str:
    base = prefix.strip("/")
    return f"{base}/discovery/runs/{run_id}/diff.json"


def filing_manifest_key(prefix: str, run_id: str, batch_index: int) -> str:
    base = prefix.strip("/")
    return f"{base}/filings/{run_id}/batch_{batch_index:05d}.json"


def filing_catalog_key(prefix: str, run_id: str) -> str:
    base = prefix.strip("/")
    return f"{base}/filings/{run_id}/catalog.json"


def filing_diff_key(prefix: str, run_id: str) -> str:
    base = prefix.strip("/")
    return f"{base}/filings/{run_id}/diff.json"


def checkpoint_key(prefix: str) -> str:
    base = prefix.strip("/")
    return f"{base}/checkpoint/latest.json"


def state_manifest_key(prefix: str) -> str:
    base = prefix.strip("/")
    return f"{base}/state/latest_filing_manifest.json"


def discovery_state_key(prefix: str) -> str:
    base = prefix.strip("/")
    return f"{base}/discovery/state/latest_sources.json"


def to_jsonl(records: list[dict[str, Any]]) -> bytes:
    lines = [json.dumps(record, sort_keys=True) for record in records]
    return ("\n".join(lines) + "\n").encode("utf-8")
