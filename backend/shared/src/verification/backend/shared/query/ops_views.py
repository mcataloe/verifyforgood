from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def list_ingest_runs(run_store: Any, limit: int = 50) -> tuple[int, dict[str, Any]]:
    runs = run_store.list_run_summaries("ingest", limit=limit)
    return 200, {"runs": runs, "count": len(runs)}


def get_ingest_run(run_store: Any, ingest_run_id: str) -> tuple[int, dict[str, Any]]:
    run = run_store.get_run("ingest", ingest_run_id)
    if run is None:
        return 404, {"message": "Ingest run not found", "ingest_run_id": ingest_run_id}
    return 200, run


def get_ingest_run_filings(run_store: Any, ingest_run_id: str) -> tuple[int, dict[str, Any]]:
    items = run_store.get_run_items("ingest", ingest_run_id, "filings")
    if items is None:
        return 404, {"message": "Ingest run filings not found", "ingest_run_id": ingest_run_id}
    return 200, {"ingest_run_id": ingest_run_id, "filings": items, "count": len(items)}


def list_refresh_runs(run_store: Any, limit: int = 50) -> tuple[int, dict[str, Any]]:
    runs = run_store.list_run_summaries("refresh", limit=limit)
    return 200, {"runs": runs, "count": len(runs)}


def get_refresh_run(run_store: Any, refresh_run_id: str) -> tuple[int, dict[str, Any]]:
    run = run_store.get_run("refresh", refresh_run_id)
    if run is None:
        return 404, {"message": "Refresh run not found", "refresh_run_id": refresh_run_id}
    return 200, run


def get_refresh_run_eins(run_store: Any, refresh_run_id: str) -> tuple[int, dict[str, Any]]:
    items = run_store.get_run_items("refresh", refresh_run_id, "eins")
    if items is None:
        return 404, {"message": "Refresh run EIN results not found", "refresh_run_id": refresh_run_id}
    return 200, {"refresh_run_id": refresh_run_id, "eins": items, "count": len(items)}


def get_nonprofit_pipeline_status(run_store: Any, profile_store: Any, ein: str) -> tuple[int, dict[str, Any]]:
    profile = profile_store.get_profile(ein) if profile_store else None
    ingest_runs = run_store.list_run_summaries("ingest", limit=100)
    refresh_runs = run_store.list_run_summaries("refresh", limit=100)

    latest_ingest = _latest_run_for_ein(ingest_runs, run_store, "ingest", "filings", ein)
    latest_refresh = _latest_run_for_ein(refresh_runs, run_store, "refresh", "eins", ein)

    if profile is None and latest_ingest is None and latest_refresh is None:
        return 404, {"message": "Pipeline status not found", "ein": ein}

    staleness_indicators = []
    if latest_ingest and latest_ingest.get("status") in {"failed", "partial_success"}:
        staleness_indicators.append("ingest_partial_or_failed")
    if latest_refresh and latest_refresh.get("status") in {"failed", "completed_with_errors"}:
        staleness_indicators.append("refresh_partial_or_failed")

    return 200, {
        "ein": ein,
        "latest_filing_processing": latest_ingest,
        "latest_refresh": latest_refresh,
        "latest_profile_generation": {
            "materialized_at": (profile or {}).get("materialized_at"),
            "model_version": (profile or {}).get("model_version"),
            "environment": (profile or {}).get("environment"),
        }
        if profile
        else None,
        "current_profile_hash": (profile or {}).get("source_hash"),
        "staleness_indicators": staleness_indicators,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _latest_run_for_ein(runs: list[dict[str, Any]], run_store: Any, run_type: str, item_name: str, ein: str) -> dict[str, Any] | None:
    for run in runs:
        run_id = run.get("ingest_run_id") if run_type == "ingest" else run.get("refresh_run_id")
        if not run_id:
            continue
        items = run_store.get_run_items(run_type, str(run_id), item_name) or []
        if any(str(item.get("ein") or "") == ein for item in items if isinstance(item, dict)):
            return run
    return None
