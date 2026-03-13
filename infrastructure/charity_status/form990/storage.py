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


def raw_source_key(prefix: str, source_year: str, source_kind: str, source_archive_key: str, source_signature: str, source_filename: str) -> str:
    base = prefix.strip("/")
    year = (source_year or "unknown_year").strip()
    kind = (source_kind or "unknown_kind").strip()
    archive = (source_archive_key or "unknown_source").strip().replace("/", "_")
    signature = (source_signature or "unknown_signature").strip()
    filename = (source_filename or "unknown_source").strip().replace("/", "_")
    return f"{base}/{year}/{kind}/{archive}/{signature}/{filename}"


def source_download_manifest_key(prefix: str, run_id: str, batch_index: int) -> str:
    base = prefix.strip("/")
    return f"{base}/source-download/runs/{run_id}/batch_{batch_index:05d}.json"


def source_download_state_prefix(prefix: str) -> str:
    base = prefix.strip("/")
    return f"{base}/source-download/state/latest"


def source_download_state_entry_key(prefix: str, source_year: str, source_kind: str, source_archive_key: str) -> str:
    base = source_download_state_prefix(prefix)
    year = (source_year or "unknown_year").strip()
    kind = (source_kind or "unknown_kind").strip()
    archive = (source_archive_key or "unknown_source").strip().replace("/", "_")
    return f"{base}/{year}/{kind}/{archive}.json"


def raw_xml_key(prefix: str, ein: str | None, tax_year: str | None, irs_object_id: str | None) -> str:
    base = prefix.strip("/")
    ein_part = (ein or "unknown_ein").strip()
    year_part = (tax_year or "unknown_year").strip()
    obj_part = (irs_object_id or "unknown_object").strip()
    return f"{base}/{ein_part}/{year_part}/{obj_part}.xml"


def to_jsonl(records: list[dict[str, Any]]) -> bytes:
    lines = [json.dumps(record, sort_keys=True) for record in records]
    return ("\n".join(lines) + "\n").encode("utf-8")
