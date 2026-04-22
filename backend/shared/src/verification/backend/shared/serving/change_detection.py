from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Literal

RefreshMode = Literal["refresh_changed", "backfill_missing", "refresh_hot", "force_refresh", "bootstrap_all"]


@dataclass(frozen=True)
class ChangeDetectionConfig:
    mode: RefreshMode
    environment: str
    source_detection_enabled: bool = False


def normalize_mode(value: str | None) -> RefreshMode:
    candidate = (value or "refresh_changed").strip().lower()
    if candidate in {"refresh_changed", "backfill_missing", "refresh_hot", "force_refresh", "bootstrap_all"}:
        return candidate
    raise ValueError(f"Unsupported refresh mode: {value}")


def parse_explicit_eins(payload: dict[str, Any] | None) -> list[str]:
    if not payload:
        return []

    event_eins = payload.get("eins")
    if isinstance(event_eins, list):
        return _normalize_eins(event_eins)

    csv_eins = payload.get("eins_csv")
    if isinstance(csv_eins, str):
        return _normalize_eins(csv_eins.split(","))

    return []


def select_target_eins(
    config: ChangeDetectionConfig,
    explicit_eins: list[str],
    source_detector: Callable[[], Iterable[str]] | None = None,
) -> list[str]:
    if explicit_eins:
        return _dedupe_preserve_order(explicit_eins)

    if config.mode == "backfill_missing":
        return []

    if config.environment != "prod" and not config.source_detection_enabled:
        return []

    if source_detector is None:
        return []

    return _dedupe_preserve_order(_normalize_eins(list(source_detector())))


def _normalize_eins(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        cleaned = "".join(ch for ch in str(value) if ch.isdigit())
        if len(cleaned) == 9:
            normalized.append(cleaned)
    return normalized


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
