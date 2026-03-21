from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .catalog import SourceCatalog, SourceConnectorCatalog, default_organization_source_catalog, default_us_source_catalog
from .normalization import (
    NormalizedOrganizationSourceRecord,
    NormalizedSourceRecord,
    ProviderCapability,
    SourceAttribution,
    SourceCategory,
    SourceConnectorCapability,
    SourceFreshness,
    SourceMetadata,
)

if TYPE_CHECKING:
    from charity_status.ingest import FileIngestResult


def __getattr__(name: str) -> Any:
    if name == "FileIngestResult":
        from charity_status.ingest import FileIngestResult

        return FileIngestResult
    if name == "build_ingest_result":
        from charity_status.ingest import build_ingest_result

        return build_ingest_result
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "FileIngestResult",
    "NormalizedOrganizationSourceRecord",
    "NormalizedSourceRecord",
    "ProviderCapability",
    "SourceAttribution",
    "SourceCatalog",
    "SourceCategory",
    "SourceConnectorCapability",
    "SourceConnectorCatalog",
    "SourceFreshness",
    "SourceMetadata",
    "build_ingest_result",
    "default_organization_source_catalog",
    "default_us_source_catalog",
]
