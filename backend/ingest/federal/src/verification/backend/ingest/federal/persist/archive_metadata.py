"""Archive and extracted-file metadata persistence services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from verification.backend.shared.nonprofits import (
    Form990ArchiveRecord,
    Form990ExtractedFileRecord,
    SqlAlchemyNonprofitRepository,
)

from ..metadata import ArchiveProbeResult, should_process_archive


@dataclass(frozen=True)
class ArchiveProbeOutcome:
    archive: Form990ArchiveRecord
    should_process: bool
    reason: str


class Form990ArchiveMetadataService:
    def __init__(self, repository: SqlAlchemyNonprofitRepository) -> None:
        self._repository = repository

    def record_archive_probe(
        self,
        *,
        source_url: str,
        filename: str | None,
        probe: ArchiveProbeResult,
    ) -> ArchiveProbeOutcome:
        previous = self._repository.get_archive_by_source_url(source_url)
        decision = should_process_archive(previous=previous, current_probe=probe)
        now_iso = probe.checked_at or _utc_now_iso()
        archive = Form990ArchiveRecord(
            archive_id=previous.archive_id if previous is not None else None,
            source_url=source_url,
            filename=filename,
            etag=probe.normalized_etag,
            last_modified=probe.last_modified,
            content_length=probe.content_length,
            response_status=probe.response_status,
            last_checked_at=probe.checked_at,
            last_processed_at=previous.last_processed_at if previous is not None else None,
            status="pending" if decision.should_process else "checked",
            created_at=previous.created_at if previous is not None else now_iso,
            update_started_at=previous.update_started_at if previous is not None else now_iso,
            update_ended_at=previous.update_ended_at if previous is not None else None,
            processing_duration_ms=previous.processing_duration_ms if previous is not None else None,
        )
        persisted = self._repository.upsert_archive_probe(archive)
        return ArchiveProbeOutcome(archive=persisted, should_process=decision.should_process, reason=decision.reason)

    def ensure_archive_record(
        self,
        *,
        source_url: str,
        filename: str | None,
        checked_at: datetime | None = None,
        status: str = "pending",
    ) -> Form990ArchiveRecord:
        existing = self._repository.get_archive_by_source_url(source_url)
        now_iso = _format_timestamp(checked_at or datetime.now(timezone.utc))
        record = Form990ArchiveRecord(
            archive_id=existing.archive_id if existing is not None else None,
            source_url=source_url,
            filename=filename,
            etag=existing.etag if existing is not None else None,
            last_modified=existing.last_modified if existing is not None else None,
            content_length=existing.content_length if existing is not None else None,
            response_status=existing.response_status if existing is not None else None,
            last_checked_at=now_iso,
            last_processed_at=existing.last_processed_at if existing is not None else None,
            status=status,
            created_at=existing.created_at if existing is not None else now_iso,
            update_started_at=existing.update_started_at if existing is not None else now_iso,
            update_ended_at=existing.update_ended_at if existing is not None else None,
            processing_duration_ms=existing.processing_duration_ms if existing is not None else None,
        )
        return self._repository.upsert_archive_probe(record)

    def mark_archive_processing_started(
        self,
        archive_id: int,
        *,
        started_at: datetime | None = None,
    ) -> Form990ArchiveRecord | None:
        effective = _format_timestamp(started_at or datetime.now(timezone.utc))
        return self._repository.mark_archive_processing(
            archive_id,
            started_at=effective,
            status="processing",
        )

    def get_extracted_file(self, archive_id: int, filename: str) -> Form990ExtractedFileRecord | None:
        return self._repository.get_extracted_file(archive_id, filename)

    def list_extracted_files_for_archive(self, archive_id: int) -> list[Form990ExtractedFileRecord]:
        return self._repository.list_extracted_files_for_archive(archive_id)

    def upsert_extracted_file(
        self,
        *,
        archive_id: int,
        filename: str,
        content_hash: str | None,
        parse_status: str | None,
        parsed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> Form990ExtractedFileRecord:
        existing = self._repository.get_extracted_file(archive_id, filename)
        now_iso = _format_timestamp(parsed_at or datetime.now(timezone.utc))
        record = Form990ExtractedFileRecord(
            file_id=existing.file_id if existing is not None else None,
            archive_id=archive_id,
            filename=filename,
            content_hash=content_hash,
            parse_status=parse_status,
            parsed_at=now_iso,
            error_message=error_message,
            created_at=existing.created_at if existing is not None else now_iso,
            updated_at=now_iso,
        )
        return self._repository.upsert_extracted_file(record)

    def mark_archive_processing_completed(
        self,
        archive_id: int,
        *,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        processed_at: datetime | None = None,
        status: str = "processed",
    ) -> Form990ArchiveRecord | None:
        effective_end = ended_at or processed_at or datetime.now(timezone.utc)
        return self._repository.mark_archive_processing(
            archive_id,
            started_at=_format_timestamp(started_at) if started_at is not None else None,
            ended_at=_format_timestamp(effective_end),
            processed_at=_format_timestamp(processed_at or effective_end),
            status=status,
        )

    def mark_archive_processing_failed(
        self,
        archive_id: int,
        *,
        started_at: datetime | None = None,
        failed_at: datetime | None = None,
    ) -> Form990ArchiveRecord | None:
        effective = failed_at or datetime.now(timezone.utc)
        return self._repository.mark_archive_processing(
            archive_id,
            started_at=_format_timestamp(started_at) if started_at is not None else None,
            ended_at=_format_timestamp(effective),
            processed_at=_format_timestamp(effective),
            status="failed",
        )


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _utc_now_iso() -> str:
    return _format_timestamp(datetime.now(timezone.utc))


__all__ = ["ArchiveProbeOutcome", "Form990ArchiveMetadataService"]

