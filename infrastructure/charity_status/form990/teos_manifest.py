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

DEFAULT_CURRENT_SYNC_STATUS = "discovered"
DEFAULT_STEP_STATUS = "pending"
MISSING_FROM_DISCOVERY_STATUS = "not_listed"
CHECKED_SYNC_STATUS = "checked"
CHANGED_SYNC_STATUS = "changed"


@dataclass(frozen=True)
class TeosZipManifestRecord:
    tax_year: str
    source_url: str
    zip_basename: str
    discovered_at: str
    last_checked_at: str
    content_length: int | None
    etag: str | None
    last_modified: str | None
    current_sync_status: str
    download_status: str
    extraction_status: str
    processing_status: str
    destination_raw_s3_prefix: str
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
            content_length=_as_optional_int(payload.get("content_length")),
            etag=_as_optional_text(payload.get("etag")),
            last_modified=_as_optional_text(payload.get("last_modified")),
            current_sync_status=str(payload.get("current_sync_status") or DEFAULT_CURRENT_SYNC_STATUS),
            download_status=str(payload.get("download_status") or DEFAULT_STEP_STATUS),
            extraction_status=str(payload.get("extraction_status") or DEFAULT_STEP_STATUS),
            processing_status=str(payload.get("processing_status") or DEFAULT_STEP_STATUS),
            destination_raw_s3_prefix=str(payload.get("destination_raw_s3_prefix") or ""),
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
        }


class TeosZipManifestRepository(Protocol):
    def load_year_records(self, tax_year: str) -> list[TeosZipManifestRecord]:
        ...

    def sync_discovered_records(
        self,
        *,
        run_id: str,
        discovered_sources: list[TeosZipDiscoveryRecord],
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

    def sync_discovered_records(
        self,
        *,
        run_id: str,
        discovered_sources: list[TeosZipDiscoveryRecord],
        checked_years: list[str] | tuple[str, ...] | None = None,
        checked_at: datetime | str | None = None,
    ) -> TeosZipManifestSyncSummary:
        checked_at_iso = _as_iso_timestamp(checked_at)
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

            for source in discovered_year_sources:
                previous = previous_records.pop(source.zip_basename, None)
                current = _merge_discovered_record(
                    source=source,
                    previous=previous,
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
        )


def _merge_discovered_record(
    *,
    source: TeosZipDiscoveryRecord,
    previous: TeosZipManifestRecord | None,
    checked_at: str,
    raw_xml_prefix: str,
) -> TeosZipManifestRecord:
    destination_prefix = teos_raw_xml_source_batch_prefix(raw_xml_prefix, source.tax_year, source.zip_basename)
    if previous is None:
        return TeosZipManifestRecord(
            tax_year=source.tax_year,
            source_url=source.source_url,
            zip_basename=source.zip_basename,
            discovered_at=source.discovered_at,
            last_checked_at=checked_at,
            content_length=None,
            etag=None,
            last_modified=None,
            current_sync_status=DEFAULT_CURRENT_SYNC_STATUS,
            download_status=DEFAULT_STEP_STATUS,
            extraction_status=DEFAULT_STEP_STATUS,
            processing_status=DEFAULT_STEP_STATUS,
            destination_raw_s3_prefix=destination_prefix,
            created_at=checked_at,
            updated_at=checked_at,
        )

    changed = (
        previous.source_url != source.source_url
        or previous.destination_raw_s3_prefix != destination_prefix
        or previous.current_sync_status == MISSING_FROM_DISCOVERY_STATUS
    )
    return TeosZipManifestRecord(
        tax_year=source.tax_year,
        source_url=source.source_url,
        zip_basename=source.zip_basename,
        discovered_at=previous.discovered_at or source.discovered_at,
        last_checked_at=checked_at,
        content_length=previous.content_length,
        etag=previous.etag,
        last_modified=previous.last_modified,
        current_sync_status=CHANGED_SYNC_STATUS if changed else CHECKED_SYNC_STATUS,
        download_status=previous.download_status or DEFAULT_STEP_STATUS,
        extraction_status=previous.extraction_status or DEFAULT_STEP_STATUS,
        processing_status=previous.processing_status or DEFAULT_STEP_STATUS,
        destination_raw_s3_prefix=destination_prefix,
        last_error=previous.last_error,
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
        content_length=previous.content_length,
        etag=previous.etag,
        last_modified=previous.last_modified,
        current_sync_status=MISSING_FROM_DISCOVERY_STATUS,
        download_status=previous.download_status,
        extraction_status=previous.extraction_status,
        processing_status=previous.processing_status,
        destination_raw_s3_prefix=previous.destination_raw_s3_prefix,
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
        or previous.destination_raw_s3_prefix != current.destination_raw_s3_prefix
        or previous.current_sync_status == MISSING_FROM_DISCOVERY_STATUS
    )


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
