from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from charity_status_backend.ingest_task.hashing import sha256_xml_content_hash
from charity_status_backend.ingest_task.metadata.archive_change_detection import should_process_archive
from charity_status_backend.ingest_task.metadata.archive_probe import ArchiveProbeResult, normalize_etag
from charity_status_platform.nonprofits import Form990ArchiveRecord


def test_normalize_etag_strips_quotes_and_weak_prefix():
    assert normalize_etag('  W/"etag-1"  ') == "etag-1"
    assert normalize_etag('"etag-1"') == "etag-1"
    assert normalize_etag("") is None


def test_should_process_archive_prefers_normalized_etag_and_falls_back():
    previous = Form990ArchiveRecord(
        archive_id=1,
        source_url="https://example.org/a.zip",
        etag="etag-1",
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
        created_at="2026-04-03T00:00:00+00:00",
        update_started_at="2026-04-03T00:00:00+00:00",
    )
    same = ArchiveProbeResult(
        source_url=previous.source_url,
        resolved_source_url=previous.source_url,
        etag='"etag-1"',
        normalized_etag="etag-1",
        last_modified=previous.last_modified,
        content_length=1234,
        response_status=200,
        checked_at="2026-04-03T00:00:00+00:00",
        method_used="HEAD",
    )
    changed = ArchiveProbeResult(
        **{**same.__dict__, "etag": '"etag-2"', "normalized_etag": "etag-2"}
    )
    fallback = ArchiveProbeResult(
        **{**same.__dict__, "etag": None, "normalized_etag": None, "last_modified": "Fri, 21 Mar 2026 00:00:00 GMT"}
    )

    assert should_process_archive(previous=previous, current_probe=same).should_process is False
    assert should_process_archive(previous=previous, current_probe=changed).reason == "etag_changed"
    assert should_process_archive(previous=previous, current_probe=fallback).reason == "last_modified_changed"


def test_sha256_xml_content_hash_is_deterministic_for_bom_and_newlines(tmp_path: Path):
    lf = tmp_path / "lf.xml"
    crlf = tmp_path / "crlf.xml"
    changed = tmp_path / "changed.xml"
    lf.write_bytes(b'<?xml version="1.0"?>\n<Return>\n  <A>1</A>\n</Return>\n')
    crlf.write_bytes(b'\xef\xbb\xbf<?xml version="1.0"?>\r\n<Return>\r\n  <A>1</A>\r\n</Return>\r\n')
    changed.write_bytes(b'<?xml version="1.0"?>\n<Return>\n  <A>2</A>\n</Return>\n')

    assert sha256_xml_content_hash(lf) == sha256_xml_content_hash(crlf)
    assert sha256_xml_content_hash(lf) != sha256_xml_content_hash(changed)
