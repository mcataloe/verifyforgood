from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Form990MetadataSource:
    name: str = "irs_form_990_metadata"

    def describe(self) -> dict[str, str]:
        return {
            "status": "planned",
            "note": "Form 990 metadata ingestion hook for a future phase.",
        }
