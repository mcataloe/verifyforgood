from __future__ import annotations

import json
import logging
import os
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from charity_status.form990.storage import teos_raw_xml_member_key, teos_raw_xml_source_batch_prefix
from charity_status.runtime_logging import configure_runtime_logging, log_structured


LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)


class TeosZipExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedTeosXmlMember:
    member_name: str
    content_length: int


@dataclass(frozen=True)
class TeosZipExtractionResult:
    zip_s3_key: str
    destination_raw_s3_prefix: str
    extracted_members: tuple[ExtractedTeosXmlMember, ...]
    extracted_at: str

    @property
    def extracted_file_count(self) -> int:
        return len(self.extracted_members)


def extract_teos_zip_from_s3(
    *,
    s3_client: Any,
    bucket: str,
    zip_s3_key: str,
    raw_xml_prefix: str,
    tax_year: str,
    zip_basename: str,
    max_xml_file_size_bytes: int,
) -> TeosZipExtractionResult:
    extracted_at = datetime.now(timezone.utc).isoformat()
    with _download_s3_object_to_temp_file(s3_client=s3_client, bucket=bucket, key=zip_s3_key) as archive_path:
        extracted_members = extract_teos_zip_members(
            archive_path=archive_path,
            max_xml_file_size_bytes=max_xml_file_size_bytes,
        )
        result = write_teos_xml_members_to_s3(
            s3_client=s3_client,
            bucket=bucket,
            raw_xml_prefix=raw_xml_prefix,
            tax_year=tax_year,
            zip_basename=zip_basename,
            extracted_members=extracted_members,
        )
        return TeosZipExtractionResult(
            zip_s3_key=zip_s3_key,
            destination_raw_s3_prefix=result.destination_raw_s3_prefix,
            extracted_members=result.extracted_members,
            extracted_at=extracted_at,
        )


def extract_teos_zip_members(
    *,
    archive_path: str,
    max_xml_file_size_bytes: int,
) -> list[tuple[str, bytes]]:
    members: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            for member in archive.infolist():
                if member.is_dir() or not member.filename.lower().endswith(".xml"):
                    continue
                if member.file_size > max_xml_file_size_bytes:
                    continue
                members.append((member.filename, archive.read(member)))
    except zipfile.BadZipFile as exc:
        raise TeosZipExtractionError(f"bad zip archive at {archive_path}") from exc
    return members


def write_teos_xml_members_to_s3(
    *,
    s3_client: Any,
    bucket: str,
    raw_xml_prefix: str,
    tax_year: str,
    zip_basename: str,
    extracted_members: list[tuple[str, bytes]],
) -> TeosZipExtractionResult:
    written: list[ExtractedTeosXmlMember] = []
    for member_name, payload in extracted_members:
        key = teos_raw_xml_member_key(raw_xml_prefix, tax_year, zip_basename, member_name)
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=payload,
            Metadata={
                "tax_year": str(tax_year)[:32],
                "source_batch": str(zip_basename)[:256],
                "member_name": str(member_name)[:1024],
            },
        )
        written.append(ExtractedTeosXmlMember(member_name=os.path.basename(member_name), content_length=len(payload)))

    return TeosZipExtractionResult(
        zip_s3_key="",
        destination_raw_s3_prefix=teos_raw_xml_source_batch_prefix(raw_xml_prefix, tax_year, zip_basename),
        extracted_members=tuple(written),
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )


def _download_s3_object_to_temp_file(*, s3_client: Any, bucket: str, key: str):
    class _TempPath:
        def __enter__(self):
            self.file = tempfile.NamedTemporaryFile(delete=False)
            response = s3_client.get_object(Bucket=bucket, Key=key)
            body = response["Body"]
            while True:
                chunk = body.read(64 * 1024)
                if not chunk:
                    break
                self.file.write(chunk)
            self.file.close()
            return self.file.name

        def __exit__(self, exc_type, exc, tb):
            try:
                os.unlink(self.file.name)
            except OSError:
                pass
            return False

    return _TempPath()


def _log_structured(event: str, **fields: Any) -> None:
    log_structured(LOGGER, event, **fields)


__all__ = [
    "ExtractedTeosXmlMember",
    "TeosZipExtractionError",
    "TeosZipExtractionResult",
    "extract_teos_zip_from_s3",
    "extract_teos_zip_members",
    "write_teos_xml_members_to_s3",
]
