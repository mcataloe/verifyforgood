from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from verification.backend.shared.serving.compare import WriteReason, compare_materialized_items


class ProfileStore(Protocol):
    def get_profile(self, ein: str) -> dict[str, Any] | None:
        ...

    def put_profile(self, item: dict[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class WriteResult:
    wrote: bool
    reason: WriteReason
    previous_item: dict[str, Any] | None = None


class MaterializedProfileWriter:
    def __init__(self, store: ProfileStore) -> None:
        self._store = store

    def write_if_needed(self, ein: str, item: dict[str, Any], force_refresh: bool = False) -> WriteResult:
        current = self._store.get_profile(ein)
        decision = compare_materialized_items(current, item, force_refresh=force_refresh)
        if decision.should_write:
            self._store.put_profile(item)
        return WriteResult(wrote=decision.should_write, reason=decision.reason, previous_item=current)

