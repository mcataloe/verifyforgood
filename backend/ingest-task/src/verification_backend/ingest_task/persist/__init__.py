"""Persistence seams for backend-owned Form 990 ingest runtime writes."""

from .archive_metadata import ArchiveProbeOutcome, Form990ArchiveMetadataService

__all__ = ["ArchiveProbeOutcome", "Form990ArchiveMetadataService"]
