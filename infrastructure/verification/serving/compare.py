from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

WriteReason = Literal[
    "force_refresh",
    "missing_item",
    "source_hash_changed",
    "model_version_changed",
    "unchanged",
]


@dataclass(frozen=True)
class WriteDecision:
    should_write: bool
    reason: WriteReason


def compare_materialized_items(
    existing_item: dict[str, Any] | None,
    new_item: dict[str, Any],
    force_refresh: bool = False,
) -> WriteDecision:
    if force_refresh:
        return WriteDecision(should_write=True, reason="force_refresh")

    if not existing_item:
        return WriteDecision(should_write=True, reason="missing_item")

    if existing_item.get("model_version") != new_item.get("model_version"):
        return WriteDecision(should_write=True, reason="model_version_changed")

    if existing_item.get("source_hash") != new_item.get("source_hash"):
        return WriteDecision(should_write=True, reason="source_hash_changed")

    return WriteDecision(should_write=False, reason="unchanged")
