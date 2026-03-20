from __future__ import annotations

import io
import zipfile

from infrastructure.charity_status.form990.teos_zip_raw_sync import (
    TeosZipExtractionError,
    extract_teos_zip_from_s3,
    extract_teos_zip_members,
)


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        return {"Body": _Body(self.store[(Bucket, Key)]["Body"])}


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self, size: int = -1):
        if isinstance(self._value, bytes):
            if size is None or size < 0:
                value, self._value = self._value, b""
                return value
            value = self._value[:size]
            self._value = self._value[size:]
            return value
        text = str(self._value).encode("utf-8")
        if size is None or size < 0:
            self._value = b""
            return text
        value = text[:size]
        self._value = text[size:]
        return value


def _zip_payload(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return stream.getvalue()


def test_extract_teos_zip_members_filters_to_xml_and_skips_large_entries(tmp_path):
    archive_path = tmp_path / "sample.zip"
    archive_path.write_bytes(
        _zip_payload(
            {
                "a.xml": b"<Return>a</Return>",
                "b.txt": b"ignore",
                "nested/c.xml": b"<Return>c</Return>",
            }
        )
    )

    members = extract_teos_zip_members(archive_path=str(archive_path), max_xml_file_size_bytes=1024)

    assert [name for name, _payload in members] == ["a.xml", "nested/c.xml"]


def test_extract_teos_zip_from_s3_writes_lineage_preserving_keys():
    s3 = FakeS3()
    zip_key = "form990/raw-sources/2025/zip_archive/2025_teos_xml_11c/sig/2025_TEOS_XML_11C.zip"
    s3.put_object(
        Bucket="test-bucket",
        Key=zip_key,
        Body=_zip_payload(
            {
                "202500123_public.xml": b"<Return>one</Return>",
                "nested/202500124_public.xml": b"<Return>two</Return>",
            }
        ),
    )

    result = extract_teos_zip_from_s3(
        s3_client=s3,
        bucket="test-bucket",
        zip_s3_key=zip_key,
        raw_xml_prefix="teos/raw/xml/",
        tax_year="2025",
        zip_basename="2025_TEOS_XML_11C",
        max_xml_file_size_bytes=1024,
    )

    assert result.extracted_file_count == 2
    assert result.destination_raw_s3_prefix == "teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C"
    assert ("test-bucket", "teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C/202500123_public.xml") in s3.store
    assert ("test-bucket", "teos/raw/xml/year=2025/source_batch=2025_TEOS_XML_11C/nested_202500124_public.xml") in s3.store


def test_extract_teos_zip_from_s3_raises_clear_error_for_bad_zip():
    s3 = FakeS3()
    zip_key = "form990/raw-sources/2025/zip_archive/2025_teos_xml_11c/sig/2025_TEOS_XML_11C.zip"
    s3.put_object(Bucket="test-bucket", Key=zip_key, Body=b"not-a-zip")

    try:
        extract_teos_zip_from_s3(
            s3_client=s3,
            bucket="test-bucket",
            zip_s3_key=zip_key,
            raw_xml_prefix="teos/raw/xml/",
            tax_year="2025",
            zip_basename="2025_TEOS_XML_11C",
            max_xml_file_size_bytes=1024,
        )
    except TeosZipExtractionError as exc:
        assert "bad zip archive" in str(exc)
    else:
        raise AssertionError("expected malformed TEOS zip extraction to fail")
