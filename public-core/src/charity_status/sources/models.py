from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SourceCategory(str, Enum):
    IDENTITY = "identity"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    FEDERAL_AWARDS = "federal_awards"
    RISK = "risk"
    TRANSPARENCY = "transparency"


@dataclass(frozen=True)
class SourceMetadata:
    source_id: str
    provider_name: str
    category: SourceCategory
    us_only: bool
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "provider_name": self.provider_name,
            "category": self.category.value,
            "us_only": self.us_only,
            "description": self.description,
        }


@dataclass(frozen=True)
class SourceAttribution:
    provider_name: str
    source_id: str
    record_id: str | None
    retrieved_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "source_id": self.source_id,
            "record_id": self.record_id,
            "retrieved_at": self.retrieved_at,
        }


@dataclass(frozen=True)
class SourceFreshness:
    retrieved_at: str
    valid_as_of: str | None = None
    expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieved_at": self.retrieved_at,
            "valid_as_of": self.valid_as_of,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True)
class NormalizedSourceRecord:
    subject_ein: str
    metadata: SourceMetadata
    fields: dict[str, Any]
    attribution: SourceAttribution
    freshness: SourceFreshness

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_ein": self.subject_ein,
            "metadata": self.metadata.to_dict(),
            "fields": self.fields,
            "attribution": self.attribution.to_dict(),
            "freshness": self.freshness.to_dict(),
        }


@dataclass(frozen=True)
class ProviderCapability:
    provider_name: str
    categories: list[SourceCategory]
    source_ids: list[str]
    us_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "categories": [category.value for category in self.categories],
            "source_ids": self.source_ids,
            "us_only": self.us_only,
        }
