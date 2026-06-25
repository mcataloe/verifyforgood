from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, Protocol

from verification.backend.shared.serving.change_detection import ChangeDetectionConfig, RefreshMode, select_target_eins
from verification.backend.shared.serving.change_events import build_change_event
from verification.backend.shared.serving.materializer import materialize_profile_item
from verification.backend.shared.serving.writer import MaterializedProfileWriter


class ProfileBuilder(Protocol):
    def __call__(self, ein: str) -> dict[str, Any] | None:
        ...


@dataclass(frozen=True)
class RefreshConfig:
    environment: str
    mode: RefreshMode = "refresh_changed"
    batch_size: int = 100
    force_refresh: bool = False
    source_detection_enabled: bool = False
    allow_nonprod_bootstrap_override: bool = False
    max_batches_per_run: int | None = None


def refresh_materialized_profiles(
    config: RefreshConfig,
    explicit_eins: list[str],
    store: Any,
    profile_builder: ProfileBuilder,
    source_detector: Callable[[], list[str]] | None = None,
    source_page_fetcher: Callable[[str | None, int], tuple[list[str], str | None]] | None = None,
    bootstrap_start_after: str | None = None,
) -> dict[str, Any]:
    if config.mode == "bootstrap_all":
        return bootstrap_all_profiles(
            config=config,
            store=store,
            profile_builder=profile_builder,
            source_page_fetcher=source_page_fetcher,
            start_after=bootstrap_start_after,
        )

    selected_eins = select_target_eins(
        config=ChangeDetectionConfig(
            mode=config.mode,
            environment=config.environment,
            source_detection_enabled=config.source_detection_enabled,
        ),
        explicit_eins=explicit_eins,
        source_detector=source_detector,
    )
    limited_eins = selected_eins[: max(0, config.batch_size)]

    writer = MaterializedProfileWriter(store)
    result = {
        "mode": config.mode,
        "environment": config.environment,
        "requested": len(explicit_eins),
        "selected": len(selected_eins),
        "processed": 0,
        "written": 0,
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "build_miss": 0,
        "reasons": {},
        "change_events": [],
    }

    for ein in limited_eins:
        payload = profile_builder(ein)
        if not payload:
            result["build_miss"] += 1
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

        result["processed"] += 1

        if config.mode == "backfill_missing" and not config.force_refresh:
            if store.get_profile(ein) is not None:
                _increment_reason(result, "backfill_existing")
                result["skipped"] += 1
                continue

        write_result = writer.write_if_needed(
            ein=ein,
            item=item,
            force_refresh=config.force_refresh or config.mode == "force_refresh",
        )
        _increment_reason(result, write_result.reason)

        if write_result.wrote:
            result["written"] += 1
            if write_result.reason == "missing_item":
                result["inserted"] += 1
            else:
                result["updated"] += 1
                change_event = build_change_event(ein=ein, previous_item=write_result.previous_item, current_item=item)
                if change_event is not None:
                    result["change_events"].append(change_event)
        else:
            result["skipped"] += 1

    return result


def _increment_reason(result: dict[str, Any], reason: str) -> None:
    reasons = result["reasons"]
    reasons[reason] = reasons.get(reason, 0) + 1


def bootstrap_all_profiles(
    config: RefreshConfig,
    store: Any,
    profile_builder: ProfileBuilder,
    source_page_fetcher: Callable[[str | None, int], tuple[list[str], str | None]] | None,
    start_after: str | None = None,
) -> dict[str, Any]:
    if config.environment != "prod" and not config.allow_nonprod_bootstrap_override:
        raise ValueError("bootstrap_all is only allowed when APP_ENV=prod unless override is explicitly enabled")
    if source_page_fetcher is None:
        raise ValueError("bootstrap_all requires a source_page_fetcher")

    started = datetime.now(timezone.utc)
    started_perf = perf_counter()
    writer = MaterializedProfileWriter(store)
    cursor = start_after
    batch_count = 0
    total_seen = 0
    inserted = 0
    updated = 0
    skipped = 0
    failed = 0
    errors: list[dict[str, str]] = []
    status = "completed"

    while True:
        if config.max_batches_per_run is not None and config.max_batches_per_run > 0 and batch_count >= config.max_batches_per_run:
            status = "partial"
            break

        eins, next_cursor = source_page_fetcher(cursor, max(1, config.batch_size))
        if not eins:
            cursor = next_cursor
            break

        batch_count += 1
        for ein in eins:
            total_seen += 1
            try:
                payload = profile_builder(ein)
                if not payload:
                    skipped += 1
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
                write_result = writer.write_if_needed(ein=ein, item=item, force_refresh=config.force_refresh)
                if write_result.wrote:
                    if write_result.reason == "missing_item":
                        inserted += 1
                    else:
                        updated += 1
                else:
                    skipped += 1
            except Exception as exc:
                failed += 1
                status = "completed_with_errors"
                if len(errors) < 25:
                    errors.append({"ein": ein, "error": str(exc)})

        if next_cursor is None or next_cursor == cursor:
            cursor = next_cursor
            break
        cursor = next_cursor

    completed = datetime.now(timezone.utc)
    duration_ms = int((perf_counter() - started_perf) * 1000)
    return {
        "status": status,
        "mode": config.mode,
        "environment": config.environment,
        "total_seen": total_seen,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "duration_ms": duration_ms,
        "batch_count": batch_count,
        "next_cursor": cursor,
        "errors": errors,
        "change_events": [],
    }

