"""Archive change-detection decisions backed by persisted metadata."""

from __future__ import annotations

from dataclasses import dataclass

from verification_platform.nonprofits import Form990ArchiveRecord

from .archive_probe import ArchiveProbeResult


@dataclass(frozen=True)
class ArchiveProcessingDecision:
    should_process: bool
    reason: str


def should_process_archive(
    *,
    previous: Form990ArchiveRecord | None,
    current_probe: ArchiveProbeResult,
) -> ArchiveProcessingDecision:
    if previous is None:
        return ArchiveProcessingDecision(should_process=True, reason="new_archive")
    if current_probe.normalized_etag and _normalize_record_etag(previous) is not None:
        if current_probe.normalized_etag != _normalize_record_etag(previous):
            return ArchiveProcessingDecision(should_process=True, reason="etag_changed")
        return ArchiveProcessingDecision(should_process=False, reason="unchanged_archive")
    if current_probe.last_modified and current_probe.last_modified != (previous.last_modified or ""):
        return ArchiveProcessingDecision(should_process=True, reason="last_modified_changed")
    if current_probe.content_length is not None and current_probe.content_length != previous.content_length:
        return ArchiveProcessingDecision(should_process=True, reason="content_length_changed")
    return ArchiveProcessingDecision(should_process=False, reason="unchanged_archive")


def _normalize_record_etag(previous: Form990ArchiveRecord) -> str | None:
    text = str(previous.etag or "").strip()
    return text or None


__all__ = ["ArchiveProcessingDecision", "should_process_archive"]

