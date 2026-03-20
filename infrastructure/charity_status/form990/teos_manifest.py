from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from charity_status.form990.storage import (
    teos_raw_xml_source_batch_prefix,
    teos_zip_manifest_run_catalog_key,
    teos_zip_manifest_state_key,
    teos_zip_manifest_state_prefix,
)
from charity_status.form990.teos_zip_discovery import TeosZipDiscoveryRecord
from charity_status.form990.teos_zip_probe import (
    TeosZipDownloadDecision,
    TeosZipProbeFailure,
    TeosZipProbeResult,
    should_download_teos_zip,
)

DEFAULT_CURRENT_SYNC_STATUS = "discovered"
DEFAULT_STEP_STATUS = "pending"
MISSING_FROM_DISCOVERY_STATUS = "not_listed"
CHECKED_SYNC_STATUS = "checked"
CHANGED_SYNC_STATUS = "changed"
PROBE_FAILED_SYNC_STATUS = "probe_failed"
DOWNLOAD_SCHEDULED_STATUS = "scheduled"
DOWNLOAD_SKIPPED_UNCHANGED_STATUS = "skipped_unchanged"
DOWNLOAD_PROBE_FAILED_STATUS = "probe_failed"


@dataclass(frozen=True)
class TeosZipManifestRecord:
    tax_year: str
    source_url: str
    zip_basename: str
    discovered_at: str
    last_checked_at: str
    resolved_source_url: str | None
    content_length: int | None
    etag: str | None
    last_modified: str | None
    current_sync_status: str
    download_status: str
    extraction_status: str
    processing_status: str
    destination_raw_s3_prefix: str
    downloaded_zip_s3_key: str | None = None
    extracted_file_count: int | None = None
    last_error: str | None = None
    download_attempted_at: str | None = None
    extraction_attempted_at: str | None = None
    processing_attempted_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TeosZipManifestRecord":
        return cls(
            tax_year=str(payload.get("tax_year") or ""),
            source_url=str(payload.get("source_url") or ""),
            zip_basename=str(payload.get("zip_basename") or ""),
            discovered_at=str(payload.get("discovered_at") or ""),
            last_checked_at=str(payload.get("last_checked_at") or ""),
            resolved_source_url=_as_optional_text(payload.get("resolved_source_url")),
            content_length=_as_optional_int(payload.get("content_length")),
            etag=_as_optional_text(payload.get("etag")),
            last_modified=_as_optional_text(payload.get("last_modified")),
            current_sync_status=str(payload.get("current_sync_status") or DEFAULT_CURRENT_SYNC_STATUS),
            download_status=str(payload.get("download_status") or DEFAULT_STEP_STATUS),
            extraction_status=str(payload.get("extraction_status") or DEFAULT_STEP_STATUS),
            processing_status=str(payload.get("processing_status") or DEFAULT_STEP_STATUS),
            destination_raw_s3_prefix=str(payload.get("destination_raw_s3_prefix") or ""),
            downloaded_zip_s3_key=_as_optional_text(payload.get("downloaded_zip_s3_key")),
            extracted_file_count=_as_optional_int(payload.get("extracted_file_count")),
            last_error=_as_optional_text(payload.get("last_error")),
            download_attempted_at=_as_optional_text(payload.get("download_attempted_at")),
            extraction_attempted_at=_as_optional_text(payload.get("extraction_attempted_at")),
            processing_attempted_at=_as_optional_text(payload.get("processing_attempted_at")),
            created_at=_as_optional_text(payload.get("created_at")),
            updated_at=_as_optional_text(payload.get("updated_at")),
        )


@dataclass(frozen=True)
class TeosZipManifestSyncSummary:
    run_id: str
    checked_at: str
    state_prefix: str
    catalog_keys: tuple[str, ...]
    discovered_count: int
    new_count: int
    changed_count: int
    removed_count: int
    unchanged_count: int
    scheduled_download_count: int = 0
    skipped_download_count: int = 0
    probe_failed_count: int = 0
    records: tuple[TeosZipManifestRecord, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "checked_at": self.checked_at,
            "state_prefix": self.state_prefix,
            "catalog_keys": list(self.catalog_keys),
            "discovered_count": self.discovered_count,
            "new_count": self.new_count,
            "changed_count": self.changed_count,
            "removed_count": self.removed_count,
            "unchanged_count": self.unchanged_count,
            "scheduled_download_count": self.scheduled_download_count,
            "skipped_download_count": self.skipped_download_count,
            "probe_failed_count": self.probe_failed_count,
        }


class TeosZipManifestRepository(Protocol):
    def load_year_records(self, tax_year: str) -> list[TeosZipManifestRecord]:
        ...

    def load_record(self, tax_year: str, zip_basename: str) -> TeosZipManifestRecord | None:
        ...

    def save_record(self, record: TeosZipManifestRecord) -> None:
        ...

    def sync_discovered_records(
        self,
        *,
        run_id: str,
        discovered_sources: list[TeosZipDiscoveryRecord],
        probe_results: dict[tuple[str, str], TeosZipProbeResult | TeosZipProbeFailure] | None = None,
        checked_years: list[str] | tuple[str, ...] | None = None,
        checked_at: datetime | str | None = None,
    ) -> TeosZipManifestSyncSummary:
        ...


class S3TeosZipManifestRepository:
    def __init__(self, *, s3_client: Any, bucket: str, manifest_prefix: str, raw_xml_prefix: str) -> None:
        self._s3 = s3_client
        self._bucket = bucket
        self._manifest_prefix = manifest_prefix
        self._raw_xml_prefix = raw_xml_prefix

    def load_year_records(self, tax_year: str) -> list[TeosZipManifestRecord]:
        prefix = f"{teos_zip_manifest_state_prefix(self._manifest_prefix)}/year={str(tax_year).strip()}/"
        try:
            response = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        except Exception:
            return []

        records: list[TeosZipManifestRecord] = []
        for item in response.get("Contents", []):
            key = str(item.get("Key") or "")
            if not key.endswith(".json"):
                continue
            try:
                body = self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read().decode("utf-8")
                payload = json.loads(body)
            except Exception:
                continue
            if isinstance(payload, dict):
                records.append(TeosZipManifestRecord.from_dict(payload))
        return sorted(records, key=lambda item: (item.tax_year, item.zip_basename))

    def load_record(self, tax_year: str, zip_basename: str) -> TeosZipManifestRecord | None:
        key = teos_zip_manifest_state_key(self._manifest_prefix, tax_year, zip_basename)
        try:
            body = self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read().decode("utf-8")
            payload = json.loads(body)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return TeosZipManifestRecord.from_dict(payload)

    def save_record(self, record: TeosZipManifestRecord) -> None:
        key = teos_zip_manifest_state_key(self._manifest_prefix, record.tax_year, record.zip_basename)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(record.to_dict(), sort_keys=True).encode("utf-8"),
        )

    def sync_discovered_records(
        self,
        *,
        run_id: str,
        discovered_sources: list[TeosZipDiscoveryRecord],
        probe_results: dict[tuple[str, str], TeosZipProbeResult | TeosZipProbeFailure] | None = None,
        checked_years: list[str] | tuple[str, ...] | None = None,
        checked_at: datetime | str | None = None,
    ) -> TeosZipManifestSyncSummary:
        checked_at_iso = _as_iso_timestamp(checked_at)
        probe_outcomes = probe_results or {}
        discovered_by_year: dict[str, list[TeosZipDiscoveryRecord]] = {}
        for source in discovered_sources:
            discovered_by_year.setdefault(source.tax_year, []).append(source)
        years_to_sync = sorted({*discovered_by_year.keys(), *(str(year).strip() for year in (checked_years or []) if str(year).strip())})

        catalog_keys: list[str] = []
        discovered_count = 0
        new_count = 0
        changed_count = 0
        removed_count = 0
        unchanged_count = 0
        scheduled_download_count = 0
        skipped_download_count = 0
        probe_failed_count = 0
        all_records: list[TeosZipManifestRecord] = []

        for tax_year in years_to_sync:
            discovered_year_sources = sorted(
                discovered_by_year.get(tax_year, []),
                key=lambda item: (item.tax_year, item.zip_basename, item.source_url),
            )
            previous_records = {item.zip_basename: item for item in self.load_year_records(tax_year)}
            current_records: list[TeosZipManifestRecord] = []
            year_new = 0
            year_changed = 0
            year_removed = 0
            year_unchanged = 0
            year_scheduled = 0
            year_skipped = 0
            year_probe_failed = 0

            for source in discovered_year_sources:
                previous = previous_records.pop(source.zip_basename, None)
                probe_outcome = probe_outcomes.get((source.tax_year, source.zip_basename))
                current = _merge_discovered_record(
                    source=source,
                    previous=previous,
                    probe_outcome=probe_outcome,
                    checked_at=checked_at_iso,
                    raw_xml_prefix=self._raw_xml_prefix,
                )
                current_records.append(current)
                if previous is None:
                    year_new += 1
                elif _record_changed(previous, current):
                    year_changed += 1
                else:
                    year_unchanged += 1
                if current.download_status == DOWNLOAD_SCHEDULED_STATUS:
                    year_scheduled += 1
                elif current.download_status == DOWNLOAD_PROBE_FAILED_STATUS:
                    year_probe_failed += 1
                else:
                    year_skipped += 1

            for previous in previous_records.values():
                current_records.append(_mark_not_listed(previous, checked_at=checked_at_iso))
                year_removed += 1

            current_records = sorted(current_records, key=lambda item: (item.tax_year, item.zip_basename))
            for record in current_records:
                state_key = teos_zip_manifest_state_key(self._manifest_prefix, record.tax_year, record.zip_basename)
                self._s3.put_object(
                    Bucket=self._bucket,
                    Key=state_key,
                    Body=json.dumps(record.to_dict(), sort_keys=True).encode("utf-8"),
                )

            catalog_key = teos_zip_manifest_run_catalog_key(self._manifest_prefix, run_id, tax_year)
            self._s3.put_object(
                Bucket=self._bucket,
                Key=catalog_key,
                Body=json.dumps(
                    {
                        "run_id": run_id,
                        "tax_year": tax_year,
                        "checked_at": checked_at_iso,
                        "state_prefix": teos_zip_manifest_state_prefix(self._manifest_prefix),
                        "discovered_count": len(discovered_year_sources),
                        "new_count": year_new,
                        "changed_count": year_changed,
                        "removed_count": year_removed,
                        "unchanged_count": year_unchanged,
                        "scheduled_download_count": year_scheduled,
                        "skipped_download_count": year_skipped,
                        "probe_failed_count": year_probe_failed,
                        "records": [record.to_dict() for record in current_records],
                    },
                    sort_keys=True,
                ).encode("utf-8"),
            )
            catalog_keys.append(catalog_key)
            discovered_count += len(discovered_year_sources)
            new_count += year_new
            changed_count += year_changed
            removed_count += year_removed
            unchanged_count += year_unchanged
            scheduled_download_count += year_scheduled
            skipped_download_count += year_skipped
            probe_failed_count += year_probe_failed
            all_records.extend(current_records)

        return TeosZipManifestSyncSummary(
            run_id=run_id,
            checked_at=checked_at_iso,
            state_prefix=teos_zip_manifest_state_prefix(self._manifest_prefix),
            catalog_keys=tuple(catalog_keys),
            discovered_count=discovered_count,
            new_count=new_count,
            changed_count=changed_count,
            removed_count=removed_count,
            unchanged_count=unchanged_count,
            scheduled_download_count=scheduled_download_count,
            skipped_download_count=skipped_download_count,
            probe_failed_count=probe_failed_count,
            records=tuple(sorted(all_records, key=lambda item: (item.tax_year, item.zip_basename))),
        )


def _merge_discovered_record(
    *,
    source: TeosZipDiscoveryRecord,
    previous: TeosZipManifestRecord | None,
    probe_outcome: TeosZipProbeResult | TeosZipProbeFailure | None,
    checked_at: str,
    raw_xml_prefix: str,
) -> TeosZipManifestRecord:
    destination_prefix = teos_raw_xml_source_batch_prefix(raw_xml_prefix, source.tax_year, source.zip_basename)
    if _is_probe_failure(probe_outcome):
        return _merge_probe_failure(
            source=source,
            previous=previous,
            checked_at=checked_at,
            destination_prefix=destination_prefix,
            probe_outcome=probe_outcome,
        )

    decision = _download_decision(previous=previous, probe_outcome=probe_outcome)
    current_sync_status = _current_sync_status(previous=previous, source=source, destination_prefix=destination_prefix, probe_outcome=probe_outcome)
    if previous is None:
        return TeosZipManifestRecord(
            tax_year=source.tax_year,
            source_url=source.source_url,
            zip_basename=source.zip_basename,
            discovered_at=source.discovered_at,
            last_checked_at=checked_at,
            resolved_source_url=_probe_attr(probe_outcome, "resolved_source_url"),
            content_length=_probe_attr(probe_outcome, "content_length"),
            etag=_probe_attr(probe_outcome, "etag"),
            last_modified=_probe_attr(probe_outcome, "last_modified"),
            current_sync_status=current_sync_status,
            download_status=_decision_status(decision),
            extraction_status=DEFAULT_STEP_STATUS,
            processing_status=DEFAULT_STEP_STATUS,
            destination_raw_s3_prefix=destination_prefix,
            downloaded_zip_s3_key=None,
            extracted_file_count=None,
            created_at=checked_at,
            updated_at=checked_at,
        )

    return TeosZipManifestRecord(
        tax_year=source.tax_year,
        source_url=source.source_url,
        zip_basename=source.zip_basename,
        discovered_at=previous.discovered_at or source.discovered_at,
        last_checked_at=checked_at,
        resolved_source_url=_probe_attr(probe_outcome, "resolved_source_url") or previous.resolved_source_url,
        content_length=_probe_attr(probe_outcome, "content_length", previous.content_length),
        etag=_probe_attr(probe_outcome, "etag") or previous.etag,
        last_modified=_probe_attr(probe_outcome, "last_modified") or previous.last_modified,
        current_sync_status=current_sync_status,
        download_status=_decision_status(decision),
        extraction_status=previous.extraction_status or DEFAULT_STEP_STATUS,
        processing_status=previous.processing_status or DEFAULT_STEP_STATUS,
        destination_raw_s3_prefix=destination_prefix,
        downloaded_zip_s3_key=previous.downloaded_zip_s3_key,
        extracted_file_count=previous.extracted_file_count,
        last_error=None,
        download_attempted_at=previous.download_attempted_at,
        extraction_attempted_at=previous.extraction_attempted_at,
        processing_attempted_at=previous.processing_attempted_at,
        created_at=previous.created_at or source.discovered_at,
        updated_at=checked_at,
    )


def _mark_not_listed(previous: TeosZipManifestRecord, *, checked_at: str) -> TeosZipManifestRecord:
    return TeosZipManifestRecord(
        tax_year=previous.tax_year,
        source_url=previous.source_url,
        zip_basename=previous.zip_basename,
        discovered_at=previous.discovered_at,
        last_checked_at=checked_at,
        resolved_source_url=previous.resolved_source_url,
        content_length=previous.content_length,
        etag=previous.etag,
        last_modified=previous.last_modified,
        current_sync_status=MISSING_FROM_DISCOVERY_STATUS,
        download_status=previous.download_status,
        extraction_status=previous.extraction_status,
        processing_status=previous.processing_status,
        destination_raw_s3_prefix=previous.destination_raw_s3_prefix,
        downloaded_zip_s3_key=previous.downloaded_zip_s3_key,
        extracted_file_count=previous.extracted_file_count,
        last_error=previous.last_error,
        download_attempted_at=previous.download_attempted_at,
        extraction_attempted_at=previous.extraction_attempted_at,
        processing_attempted_at=previous.processing_attempted_at,
        created_at=previous.created_at,
        updated_at=checked_at,
    )


def _record_changed(previous: TeosZipManifestRecord, current: TeosZipManifestRecord) -> bool:
    return (
        previous.source_url != current.source_url
        or previous.resolved_source_url != current.resolved_source_url
        or previous.destination_raw_s3_prefix != current.destination_raw_s3_prefix
        or previous.content_length != current.content_length
        or previous.etag != current.etag
        or previous.last_modified != current.last_modified
        or previous.last_error != current.last_error
        or previous.current_sync_status == MISSING_FROM_DISCOVERY_STATUS
    )


def _merge_probe_failure(
    *,
    source: TeosZipDiscoveryRecord,
    previous: TeosZipManifestRecord | None,
    checked_at: str,
    destination_prefix: str,
    probe_outcome: TeosZipProbeFailure,
) -> TeosZipManifestRecord:
    if previous is None:
        return TeosZipManifestRecord(
            tax_year=source.tax_year,
            source_url=source.source_url,
            zip_basename=source.zip_basename,
            discovered_at=source.discovered_at,
            last_checked_at=checked_at,
            resolved_source_url=None,
            content_length=None,
            etag=None,
            last_modified=None,
            current_sync_status=PROBE_FAILED_SYNC_STATUS,
            download_status=DOWNLOAD_PROBE_FAILED_STATUS,
            extraction_status=DEFAULT_STEP_STATUS,
            processing_status=DEFAULT_STEP_STATUS,
            destination_raw_s3_prefix=destination_prefix,
            downloaded_zip_s3_key=None,
            extracted_file_count=None,
            last_error=probe_outcome.error,
            created_at=checked_at,
            updated_at=checked_at,
        )

    return TeosZipManifestRecord(
        tax_year=source.tax_year,
        source_url=source.source_url,
        zip_basename=source.zip_basename,
        discovered_at=previous.discovered_at or source.discovered_at,
        last_checked_at=checked_at,
        resolved_source_url=previous.resolved_source_url,
        content_length=previous.content_length,
        etag=previous.etag,
        last_modified=previous.last_modified,
        current_sync_status=PROBE_FAILED_SYNC_STATUS,
        download_status=DOWNLOAD_PROBE_FAILED_STATUS,
        extraction_status=previous.extraction_status or DEFAULT_STEP_STATUS,
        processing_status=previous.processing_status or DEFAULT_STEP_STATUS,
        destination_raw_s3_prefix=destination_prefix,
        downloaded_zip_s3_key=previous.downloaded_zip_s3_key,
        extracted_file_count=previous.extracted_file_count,
        last_error=probe_outcome.error,
        download_attempted_at=previous.download_attempted_at,
        extraction_attempted_at=previous.extraction_attempted_at,
        processing_attempted_at=previous.processing_attempted_at,
        created_at=previous.created_at or source.discovered_at,
        updated_at=checked_at,
    )


def _current_sync_status(
    *,
    previous: TeosZipManifestRecord | None,
    source: TeosZipDiscoveryRecord,
    destination_prefix: str,
    probe_outcome: TeosZipProbeResult | None,
) -> str:
    if previous is None:
        return DEFAULT_CURRENT_SYNC_STATUS
    if previous.current_sync_status == MISSING_FROM_DISCOVERY_STATUS:
        return CHANGED_SYNC_STATUS
    if previous.source_url != source.source_url or previous.destination_raw_s3_prefix != destination_prefix:
        return CHANGED_SYNC_STATUS
    if not _is_probe_result(probe_outcome):
        return CHECKED_SYNC_STATUS
    if probe_outcome.etag and probe_outcome.etag != (previous.etag or ""):
        return CHANGED_SYNC_STATUS
    if probe_outcome.last_modified and probe_outcome.last_modified != (previous.last_modified or ""):
        return CHANGED_SYNC_STATUS
    if probe_outcome.content_length is not None and probe_outcome.content_length != previous.content_length:
        return CHANGED_SYNC_STATUS
    return CHECKED_SYNC_STATUS


def _download_decision(
    *,
    previous: TeosZipManifestRecord | None,
    probe_outcome: TeosZipProbeResult | None,
) -> TeosZipDownloadDecision:
    if not _is_probe_result(probe_outcome):
        return TeosZipDownloadDecision(should_download=previous is None, reason="new_zip" if previous is None else "unchanged_remote_zip")
    return should_download_teos_zip(previous=previous, current_probe=probe_outcome)


def _probe_attr(probe_outcome: TeosZipProbeResult | None, attr_name: str, default: Any = None) -> Any:
    if not _is_probe_result(probe_outcome):
        return default
    return getattr(probe_outcome, attr_name)


def _decision_status(decision: TeosZipDownloadDecision) -> str:
    return DOWNLOAD_SCHEDULED_STATUS if decision.should_download else DOWNLOAD_SKIPPED_UNCHANGED_STATUS


def _is_probe_result(value: Any) -> bool:
    return hasattr(value, "source_url") and hasattr(value, "checked_at") and hasattr(value, "method_used")


def _is_probe_failure(value: Any) -> bool:
    return hasattr(value, "source_url") and hasattr(value, "checked_at") and hasattr(value, "error") and not hasattr(value, "method_used")


def _as_iso_timestamp(value: datetime | str | None) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return datetime.now(timezone.utc).isoformat()


def _as_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "S3TeosZipManifestRepository",
    "TeosZipManifestRecord",
    "TeosZipManifestRepository",
    "TeosZipManifestSyncSummary",
]
