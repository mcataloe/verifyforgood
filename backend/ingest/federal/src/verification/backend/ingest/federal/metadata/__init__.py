"""Metadata contracts for archive-scoped Form 990 ingest runs."""

from __future__ import annotations

from dataclasses import dataclass

from .archive_change_detection import ArchiveProcessingDecision, should_process_archive
from .archive_probe import ArchiveProbeResult, normalize_etag, probe_archive_metadata


@dataclass(frozen=True)
class ArchiveProcessingMetadata:
    archive_name: str
    archive_year: str | None = None
    archive_identity: str | None = None
    source_url: str | None = None
    run_id: str | None = None
    correlation_id: str | None = None


__all__ = [
    "ArchiveProbeResult",
    "ArchiveProcessingDecision",
    "ArchiveProcessingMetadata",
    "normalize_etag",
    "probe_archive_metadata",
    "should_process_archive",
]
