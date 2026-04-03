"""Metadata contracts for archive-scoped Form 990 ingest runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchiveProcessingMetadata:
    archive_name: str
    archive_year: str | None = None
    source_key: str | None = None
    source_url: str | None = None
    run_id: str | None = None
    correlation_id: str | None = None


__all__ = ["ArchiveProcessingMetadata"]
