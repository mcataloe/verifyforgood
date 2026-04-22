from __future__ import annotations

import io
import zipfile

from infrastructure.verification.backend.ingest.federal.form990.zip_processing import fetch_zip_records


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = io.BytesIO(body)
        self.status = status

    def read(self, size: int = -1):
        return self._body.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_zip(xml_payload: bytes) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("2024/obj-1.xml", xml_payload)
        zf.writestr("README.txt", b"ignored")
    return stream.getvalue()


def test_fetch_zip_records_extracts_xml(monkeypatch):
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Return xmlns="http://www.irs.gov/efile">
  <ReturnHeader><TaxYr>2024</TaxYr></ReturnHeader>
  <ReturnData>
    <IRS990>
      <Filer><EIN>123456789</EIN></Filer>
    </IRS990>
  </ReturnData>
</Return>
"""
    payload = _make_zip(xml)
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=120: _FakeResponse(payload))
    records = fetch_zip_records(
        zip_url="https://example.org/download990xml_2024.zip",
        source_year="2024",
        source_archive="irs-page-2024",
    )
    assert len(records) == 1
    record, xml_bytes = records[0]
    assert record.irs_object_id == "obj-1"
    assert record.source_year == "2024"
    assert record.source_signature
    assert xml_bytes.startswith(b"<?xml")

