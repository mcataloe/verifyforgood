from __future__ import annotations

import io
import zipfile

from infrastructure.charity_status.form990.models import Form990IndexRecord
from infrastructure.charity_status.form990.zip_selected_processing import ZipBackedXmlLoader, select_zip_sources_for_records


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

    def read(self):
        if isinstance(self._value, bytes):
            return self._value
        return str(self._value).encode("utf-8")


def _zip_payload(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return stream.getvalue()


def _source(*, year: str, archive_key: str, s3_key: str) -> dict[str, str]:
    return {
        "source_year": year,
        "source_kind": "zip_archive",
        "source_archive_key": archive_key,
        "raw_source_s3_key": s3_key,
    }


def test_zip_loader_resolves_teos_archive_and_extracts_selected_member():
    s3 = FakeS3()
    zip_key = "form990/raw-sources/2024/zip_archive/2024_teos_xml_11b/sig/2024_TEOS_XML_11B.zip"
    s3.put_object(
        Bucket="test-bucket",
        Key=zip_key,
        Body=_zip_payload({"obj-1.xml": b"<Return>one</Return>", "obj-2.xml": b"<Return>two</Return>"}),
    )
    loader = ZipBackedXmlLoader(
        s3_client=s3,
        bucket="test-bucket",
        zip_sources=[_source(year="2024", archive_key="2024_teos_xml_11b", s3_key=zip_key)],
        allow_url_fallback=False,
    )
    record = Form990IndexRecord(
        ein="123456789",
        tax_year="2024",
        filing_date="2025-01-01",
        return_type="990",
        irs_object_id="obj-2",
        xml_url="https://example.org/obj-2.xml",
        source_year="2024",
        source_archive="2024_TEOS_XML_11B",
        source_signature="sig",
    )
    xml_bytes, source_ref = loader.load(record)
    assert xml_bytes == b"<Return>two</Return>"
    assert source_ref.endswith(f"{zip_key}#obj-2.xml")
    assert loader.zip_extracted_count == 1
    assert loader.url_fallback_count == 0


def test_zip_loader_supports_legacy_download990xml_archive_hint():
    s3 = FakeS3()
    zip_key = "form990/raw-sources/2020/zip_archive/download990xml_2020_1/sig/download990xml_2020_1.zip"
    s3.put_object(
        Bucket="test-bucket",
        Key=zip_key,
        Body=_zip_payload({"202033189349300318.xml": b"<Return/>"}),
    )
    loader = ZipBackedXmlLoader(
        s3_client=s3,
        bucket="test-bucket",
        zip_sources=[_source(year="2020", archive_key="download990xml_2020_1", s3_key=zip_key)],
        allow_url_fallback=False,
    )
    record = Form990IndexRecord(
        ein="150406405",
        tax_year="2020",
        filing_date="2021-01-01",
        return_type="990",
        irs_object_id="202033189349300318",
        xml_url="https://example.org/202033189349300318_public.xml",
        source_year="2020",
        source_archive="download990xml_2020_1",
        source_signature="sig",
    )
    xml_bytes, _source_ref = loader.load(record)
    assert xml_bytes == b"<Return/>"
    assert loader.zip_extracted_count == 1


def test_zip_loader_falls_back_to_xml_url_when_member_not_found(monkeypatch):
    s3 = FakeS3()
    zip_key = "form990/raw-sources/2024/zip_archive/2024_teos_xml_ct1/sig/2024_TEOS_XML_CT1.zip"
    s3.put_object(Bucket="test-bucket", Key=zip_key, Body=_zip_payload({"obj-1.xml": b"<Return>one</Return>"}))
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda req, timeout=60: _FakeResponse(b"<Return>fallback</Return>"),
    )
    loader = ZipBackedXmlLoader(
        s3_client=s3,
        bucket="test-bucket",
        zip_sources=[_source(year="2024", archive_key="2024_teos_xml_ct1", s3_key=zip_key)],
        allow_url_fallback=True,
        url_timeout_seconds=60,
    )
    record = Form990IndexRecord(
        ein="123456789",
        tax_year="2024",
        filing_date="2025-01-01",
        return_type="990",
        irs_object_id="obj-missing",
        xml_url="https://example.org/obj-missing.xml",
        source_year="2024",
        source_archive="2024_TEOS_XML_CT1",
        source_signature="sig",
    )
    xml_bytes, source_ref = loader.load(record)
    assert xml_bytes == b"<Return>fallback</Return>"
    assert source_ref == "https://example.org/obj-missing.xml"
    assert loader.zip_extracted_count == 0
    assert loader.url_fallback_count == 1


def test_select_zip_sources_for_records_filters_by_year():
    selected = select_zip_sources_for_records(
        [{"source_year": "2024", "irs_object_id": "obj-1"}],
        [
            _source(year="2023", archive_key="2023_teos_xml_11b", s3_key="k1"),
            _source(year="2024", archive_key="2024_teos_xml_11b", s3_key="k2"),
        ],
    )
    assert len(selected) == 1
    assert selected[0]["source_archive_key"] == "2024_teos_xml_11b"


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
