from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from charity_status.serving.change_detection import ChangeDetectionConfig, RefreshMode, select_target_eins
from charity_status.serving.materializer import materialize_profile_item
from charity_status.serving.writer import MaterializedProfileWriter


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


def refresh_materialized_profiles(
    config: RefreshConfig,
    explicit_eins: list[str],
    store: Any,
    profile_builder: ProfileBuilder,
    source_detector: Callable[[], list[str]] | None = None,
) -> dict[str, Any]:
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
        else:
            result["skipped"] += 1

    return result


def _increment_reason(result: dict[str, Any], reason: str) -> None:
    reasons = result["reasons"]
    reasons[reason] = reasons.get(reason, 0) + 1
