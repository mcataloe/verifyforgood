from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
import zipfile
from typing import Any

from verification.form990.extractors.metadata import extract_metadata_fields
from verification.form990.models import Form990IndexRecord
from verification.form990.parser import XmlParseError, parse_xml


def fetch_zip_records(
    zip_url: str,
    source_year: str,
    source_archive: str,
    timeout_seconds: int = 120,
    max_xml_file_size_bytes: int = 20 * 1024 * 1024,
) -> list[tuple[Form990IndexRecord, bytes]]:
    digest = hashlib.sha256()
    with _download_to_temp_file(zip_url=zip_url, timeout_seconds=timeout_seconds, digest=digest) as archive_path:
        zip_signature = digest.hexdigest()
        return _records_from_zip(
            archive_path=archive_path,
            zip_url=zip_url,
            source_year=source_year,
            source_archive=source_archive,
            zip_signature=zip_signature,
            max_xml_file_size_bytes=max_xml_file_size_bytes,
        )


def _records_from_zip(
    archive_path: str,
    zip_url: str,
    source_year: str,
    source_archive: str,
    zip_signature: str,
    max_xml_file_size_bytes: int,
) -> list[tuple[Form990IndexRecord, bytes]]:
    records: list[tuple[Form990IndexRecord, bytes]] = []
    with zipfile.ZipFile(archive_path, mode="r") as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if not member.filename.lower().endswith(".xml"):
                continue
            if member.file_size > max_xml_file_size_bytes:
                continue
            xml_bytes = archive.read(member)
            record = _record_from_xml(
                xml_bytes=xml_bytes,
                member_name=member.filename,
                zip_url=zip_url,
                source_year=source_year,
                source_archive=source_archive,
                zip_signature=zip_signature,
            )
            if record is None:
                continue
            records.append((record, xml_bytes))
    return records


def _record_from_xml(
    xml_bytes: bytes,
    member_name: str,
    zip_url: str,
    source_year: str,
    source_archive: str,
    zip_signature: str,
) -> Form990IndexRecord | None:
    try:
        parsed = parse_xml(xml_bytes)
    except XmlParseError:
        return None
    fields = extract_metadata_fields(parsed)
    irs_object_id = _object_id_from_member(member_name)
    if not irs_object_id:
        return None
    xml_reference = f"{zip_url}#{member_name}"
    record = Form990IndexRecord(
        ein=_as_text(fields.get("ein")),
        tax_year=_as_text(fields.get("tax_year")) or str(source_year),
        filing_date=_as_text(fields.get("filing_date")),
        return_type=_as_text(fields.get("return_type")) or "990",
        irs_object_id=irs_object_id,
        xml_url=xml_reference,
        source_year=str(source_year),
        source_archive=str(source_archive),
        source_signature=_signature_for_record(
            irs_object_id=irs_object_id,
            xml_bytes=xml_bytes,
            zip_signature=zip_signature,
            source_year=source_year,
            source_archive=source_archive,
        ),
    )
    return record


def _download_to_temp_file(zip_url: str, timeout_seconds: int, digest: Any):
    class _TempPath:
        def __enter__(self):
            self.file = tempfile.NamedTemporaryFile(delete=False)
            request = urllib.request.Request(zip_url, method="GET")
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                if response.status >= 400:
                    raise RuntimeError(f"zip download failed with status {response.status}")
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
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


def _object_id_from_member(member_name: str) -> str:
    base = os.path.basename(member_name.strip())
    if not base:
        return ""
    if "." in base:
        base = base.rsplit(".", 1)[0]
    return base.strip()


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _signature_for_record(irs_object_id: str, xml_bytes: bytes, zip_signature: str, source_year: str, source_archive: str) -> str:
    payload = "|".join(
        [
            irs_object_id,
            zip_signature,
            source_year,
            source_archive,
            hashlib.sha256(xml_bytes).hexdigest(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

