from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from charity_status.serving.change_events import build_change_event
from charity_status.serving.materializer import materialize_profile_item
from charity_status.serving.writer import MaterializedProfileWriter


class ProfileBuilder(Protocol):
    def __call__(self, ein: str) -> dict[str, Any] | None:
        ...


@dataclass(frozen=True)
class PostIngestRefreshConfig:
    environment: str
    mode: str = "post_ingest_refresh"
    force_refresh: bool = False


def refresh_from_ingest_output(
    *,
    config: PostIngestRefreshConfig,
    ingest_output: dict[str, Any],
    store: Any,
    profile_builder: ProfileBuilder,
    refresh_run_id: str | None = None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    run_id = refresh_run_id or f"refresh_{started.strftime('%Y%m%dT%H%M%SZ')}"
    source_run_id = str(ingest_output.get("run_id") or ingest_output.get("ingest_run_id") or "")
    affected_eins = _derive_affected_eins(ingest_output)
    source_filing_ids = _derive_source_filing_ids(ingest_output)
    writer = MaterializedProfileWriter(store)

    results: list[dict[str, Any]] = []
    refreshed_count = 0
    unchanged_count = 0
    failed_count = 0
    change_events: list[dict[str, Any]] = []

    for ein in affected_eins:
        filing_ids = source_filing_ids.get(ein, [])
        try:
            payload = profile_builder(ein)
            if payload is None:
                failed_count += 1
                results.append(
                    _ein_result(
                        ein=ein,
                        trigger_reason="ingest_changed_filing",
                        source_filing_ids=filing_ids,
                        changed=False,
                        status="failed",
                        error="profile_build_miss",
                    )
                )
                continue

            source_versions = {
                "model_version": payload.get("score_explanation", {}).get("model_version"),
                "score_data_sources": payload.get("score_explanation", {}).get("score_data_sources"),
            }
            item = materialize_profile_item(
                ein=ein,
                response_payload=payload,
                environment=config.environment,
                source_data_versions=source_versions,
            )
            write = writer.write_if_needed(ein=ein, item=item, force_refresh=config.force_refresh)
            previous_hash = (write.previous_item or {}).get("source_hash")
            new_hash = item.get("source_hash")

            changed = bool(write.wrote)
            if changed:
                refreshed_count += 1
                event = build_change_event(ein=ein, previous_item=write.previous_item, current_item=item)
                if event:
                    change_events.append(event)
            else:
                unchanged_count += 1

            results.append(
                _ein_result(
                    ein=ein,
                    trigger_reason="ingest_changed_filing",
                    source_filing_ids=filing_ids,
                    previous_hash=previous_hash,
                    new_hash=new_hash,
                    changed=changed,
                    status="refreshed" if changed else "unchanged",
                )
            )
        except Exception as exc:
            failed_count += 1
            results.append(
                _ein_result(
                    ein=ein,
                    trigger_reason="ingest_changed_filing",
                    source_filing_ids=filing_ids,
                    changed=False,
                    status="failed",
                    error=str(exc),
                )
            )

    completed = datetime.now(timezone.utc)
    return {
        "refresh_run_id": run_id,
        "ingest_run_id": source_run_id or None,
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "mode": config.mode,
        "environment": config.environment,
        "affected_ein_count": len(affected_eins),
        "refreshed_count": refreshed_count,
        "unchanged_count": unchanged_count,
        "failed_count": failed_count,
        "results": results,
        "change_events": change_events,
    }


def _derive_affected_eins(ingest_output: dict[str, Any]) -> list[str]:
    explicit = ingest_output.get("affected_eins")
    if isinstance(explicit, list):
        return sorted({str(item).strip() for item in explicit if str(item).strip()})

    eins = set()
    records = ingest_output.get("records")
    if isinstance(records, list):
        for row in records:
            if not isinstance(row, dict):
                continue
            ein = str(row.get("ein") or "").strip()
            if ein:
                eins.add(ein)
    return sorted(eins)


def _derive_source_filing_ids(ingest_output: dict[str, Any]) -> dict[str, list[str]]:
    explicit = ingest_output.get("affected_filing_ids")
    if isinstance(explicit, dict):
        normalized: dict[str, list[str]] = {}
        for ein, values in explicit.items():
            if not isinstance(values, list):
                continue
            normalized[str(ein)] = sorted({str(item).strip() for item in values if str(item).strip()})
        return normalized

    mapping: dict[str, set[str]] = {}
    records = ingest_output.get("records")
    if isinstance(records, list):
        for row in records:
            if not isinstance(row, dict):
                continue
            ein = str(row.get("ein") or "").strip()
            obj = str(row.get("irs_object_id") or "").strip()
            if not ein or not obj:
                continue
            mapping.setdefault(ein, set()).add(obj)
    return {ein: sorted(values) for ein, values in mapping.items()}


def _ein_result(
    *,
    ein: str,
    trigger_reason: str,
    source_filing_ids: list[str],
    previous_hash: str | None = None,
    new_hash: str | None = None,
    changed: bool,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "ein": ein,
        "trigger_reason": trigger_reason,
        "source_filing_ids": source_filing_ids,
        "previous_profile_hash": previous_hash,
        "new_profile_hash": new_hash,
        "changed": changed,
        "status": status,
        "error": error,
    }
