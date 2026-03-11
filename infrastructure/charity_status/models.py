from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NonprofitResponse:
    organization: dict[str, Any]
    verification: dict[str, Any]
    scores: dict[str, Any]
    model: dict[str, Any]
    source_record: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "organization": self.organization,
            "verification": self.verification,
            "scores": self.scores,
            "model": self.model,
        }
        if self.source_record is not None:
            payload["source_record"] = self.source_record
        return payload
