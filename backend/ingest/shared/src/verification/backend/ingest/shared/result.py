from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_ingest_result(started_at: datetime, files: list[dict[str, Any]]) -> dict[str, Any]:
    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    downloaded_files = [item["name"] for item in files if item.get("status") == "downloaded"]
    failed_files = [
        {"filename": item["name"], "error": item.get("error", "unknown error")}
        for item in files
        if item.get("status") == "failed"
    ]

    if downloaded_files and failed_files:
        status = "partial_success"
    elif downloaded_files:
        status = "success"
    else:
        status = "failed"

    return {
        "status": status,
        "downloaded": downloaded_files,
        "failed": failed_files,
        "downloaded_count": len(downloaded_files),
        "failed_count": len(failed_files),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_ms": duration_ms,
        "files": files,
    }
