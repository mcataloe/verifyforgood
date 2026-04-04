from __future__ import annotations

import io
import json
import logging
import os
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Any

from charity_status.form990.hardening import is_transient_network_error, retry_call
from charity_status.form990.models import Form990IndexRecord
from charity_status.form990.source_catalog import derive_source_archive_key
from charity_status.runtime_logging import configure_runtime_logging, log_structured

LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)


class ZipMemberNotFoundError(RuntimeError):
    pass


class MalformedZipArchiveError(RuntimeError):
    pass

@dataclass(frozen=True)
class ZipResolution:
    zip_source: dict[str, Any]
    member_name: str


@dataclass
class ZipBackedXmlLoader:
    s3_client: Any
    bucket: str
    zip_sources: list[dict[str, Any]]
    allow_url_fallback: bool = True
    url_timeout_seconds: int = 60
    max_xml_file_size_bytes: int = 20 * 1024 * 1024

    def __post_init__(self) -> None:
        self._zip_sources_by_year: dict[str, list[dict[str, Any]]] = {}
        self._zip_bytes: dict[str, bytes] = {}
        self._zip_member_indexes: dict[str, dict[str, str]] = {}
        self.zip_extracted_count = 0
        self.url_fallback_count = 0
        self.unresolved_count = 0
        for source in self.zip_sources:
            year = str(source.get("source_year") or "").strip()
            if not year:
                continue
            self._zip_sources_by_year.setdefault(year, []).append(source)
        for year in self._zip_sources_by_year:
            self._zip_sources_by_year[year] = sorted(self._zip_sources_by_year[year], key=_zip_source_sort_key)

    def load(self, record: Form990IndexRecord) -> tuple[bytes, str]:
        resolution = self.resolve(record)
        if resolution:
            xml_bytes = self._read_member_xml(resolution.zip_source, resolution.member_name)
            self.zip_extracted_count += 1
            reference = f"s3://{self.bucket}/{resolution.zip_source.get('raw_source_s3_key')}#{resolution.member_name}"
            _log_structured(
                "form990.zip.resolve_hit",
                source_year=record.source_year,
                source_archive=record.source_archive,
                zip_source_archive_key=resolution.zip_source.get("source_archive_key"),
                irs_object_id=record.irs_object_id,
                member_name=resolution.member_name,
            )
            return xml_bytes, reference
        if self.allow_url_fallback and record.xml_url:
            self.url_fallback_count += 1
            _log_structured(
                "form990.zip.resolve_miss_fallback_url",
                source_year=record.source_year,
                source_archive=record.source_archive,
                irs_object_id=record.irs_object_id,
                xml_url=record.xml_url,
                candidate_zip_source_count=len(self._zip_sources_by_year.get(str(record.source_year or "").strip(), [])),
            )
            return (
                _download_xml_url(record.xml_url, timeout_seconds=self.url_timeout_seconds),
                record.xml_url,
            )
        self.unresolved_count += 1
        _log_structured(
            "form990.zip.resolve_miss_no_fallback",
            source_year=record.source_year,
            source_archive=record.source_archive,
            irs_object_id=record.irs_object_id,
            candidate_zip_source_count=len(self._zip_sources_by_year.get(str(record.source_year or "").strip(), [])),
        )
        raise ZipMemberNotFoundError(f"unable to resolve filing XML for object_id={record.irs_object_id or 'unknown'}")

    def resolve(self, record: Form990IndexRecord) -> ZipResolution | None:
        object_id = _record_object_id(record)
        if not object_id:
            return None
        year = str(record.source_year or "").strip()
        candidate_sources = list(self._zip_sources_by_year.get(year, []))
        if not candidate_sources:
            return None

        hinted_archive = _hinted_archive_key(record.source_archive)
        if hinted_archive:
            hinted = [item for item in candidate_sources if _archive_key(item) == hinted_archive]
            non_hinted = [item for item in candidate_sources if _archive_key(item) != hinted_archive]
            candidate_sources = [*hinted, *non_hinted]

        for source in candidate_sources:
            member_name = self._resolve_member_name(source, object_id)
            if member_name:
                return ZipResolution(zip_source=source, member_name=member_name)
        return None

    def stats(self) -> dict[str, int]:
        return {
            "zip_extracted_count": int(self.zip_extracted_count),
            "url_fallback_count": int(self.url_fallback_count),
            "zip_unresolved_count": int(self.unresolved_count),
        }

    def _resolve_member_name(self, source: dict[str, Any], object_id: str) -> str | None:
        index = self._zip_member_index(source)
        return index.get(object_id)

    def _zip_member_index(self, source: dict[str, Any]) -> dict[str, str]:
        source_key = str(source.get("raw_source_s3_key") or "").strip()
        if source_key in self._zip_member_indexes:
            return self._zip_member_indexes[source_key]
        payload = self._zip_blob(source)
        mapping: dict[str, str] = {}
        try:
            with zipfile.ZipFile(io.BytesIO(payload), mode="r") as archive:
                for member in archive.infolist():
                    if member.is_dir() or not member.filename.lower().endswith(".xml"):
                        continue
                    if member.file_size > self.max_xml_file_size_bytes:
                        continue
                    member_object_id = _member_object_id(member.filename)
                    if member_object_id and member_object_id not in mapping:
                        mapping[member_object_id] = member.filename
        except zipfile.BadZipFile as exc:
            raise MalformedZipArchiveError(f"bad zip archive at {source_key}") from exc
        self._zip_member_indexes[source_key] = mapping
        return mapping

    def _read_member_xml(self, source: dict[str, Any], member_name: str) -> bytes:
        payload = self._zip_blob(source)
        try:
            with zipfile.ZipFile(io.BytesIO(payload), mode="r") as archive:
                info = archive.getinfo(member_name)
                if info.file_size > self.max_xml_file_size_bytes:
                    raise RuntimeError(f"xml member exceeds max size for {member_name}")
                return archive.read(member_name)
        except zipfile.BadZipFile as exc:
            raise MalformedZipArchiveError(f"bad zip archive while reading member {member_name}") from exc

    def _zip_blob(self, source: dict[str, Any]) -> bytes:
        source_key = str(source.get("raw_source_s3_key") or "").strip()
        if not source_key:
            raise RuntimeError("zip source missing raw_source_s3_key")
        if source_key in self._zip_bytes:
            return self._zip_bytes[source_key]
        payload = self.s3_client.get_object(Bucket=self.bucket, Key=source_key)["Body"].read()
        self._zip_bytes[source_key] = payload
        return payload


def select_zip_sources_for_records(records: list[dict[str, Any]], downloaded_source_state: list[dict[str, Any]]) -> list[dict[str, Any]]:
    years = {str(item.get("source_year") or "").strip() for item in records if isinstance(item, dict)}
    selected: list[dict[str, Any]] = []
    for entry in downloaded_source_state:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("source_kind") or "").strip() != "zip_archive":
            continue
        year = str(entry.get("source_year") or "").strip()
        if years and year not in years:
            continue
        if not entry.get("raw_source_s3_key"):
            continue
        selected.append(entry)
    return sorted(selected, key=_zip_source_sort_key)


def _record_object_id(record: Form990IndexRecord) -> str:
    if record.irs_object_id:
        return str(record.irs_object_id).strip()
    if record.xml_url:
        candidate = str(record.xml_url).rstrip("/").split("/")[-1]
        if candidate.endswith("_public.xml"):
            candidate = candidate[: -len("_public.xml")]
        if candidate.endswith(".xml"):
            candidate = candidate[:-4]
        return candidate.strip()
    return ""


def _member_object_id(member_name: str) -> str:
    name = os.path.basename(member_name.strip())
    if not name:
        return ""
    lower = name.lower()
    if lower.endswith(".xml"):
        name = name[:-4]
        lower = lower[:-4]
    if lower.endswith("_public"):
        name = name[: -len("_public")]
    return name.strip()


def _archive_key(source: dict[str, Any]) -> str:
    return str(source.get("source_archive_key") or "").strip()


def _hinted_archive_key(source_archive: str | None) -> str | None:
    hint = str(source_archive or "").strip()
    if not hint:
        return None
    if hint.lower().startswith("index_"):
        return None
    return derive_source_archive_key(hint)


def _zip_source_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("source_year") or "").strip(),
        str(entry.get("source_archive_key") or "").strip(),
        str(entry.get("raw_source_s3_key") or "").strip(),
    )


def _download_xml_url(xml_url: str, timeout_seconds: int) -> bytes:
    def _fetch() -> bytes:
        request = urllib.request.Request(xml_url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status >= 400:
                raise RuntimeError(f"download failed with status {response.status}")
            return response.read()

    return retry_call(_fetch, max_attempts=3, is_retryable=is_transient_network_error)


def _log_structured(event: str, **fields: Any) -> None:
    log_structured(LOGGER, event, **fields)
