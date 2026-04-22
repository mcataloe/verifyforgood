from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError

from infrastructure.verification.backend.ingest.federal.form990.teos_zip_probe import probe_teos_zip_metadata, should_download_teos_zip


@dataclass(frozen=True)
class _PreviousProbeState:
    etag: str | None
    last_modified: str | None
    content_length: int | None


class _FakeResponse:
    def __init__(self, *, url: str, headers: dict[str, str], status: int = 200):
        self._url = url
        self.headers = headers
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def geturl(self):
        return self._url

    def read(self, _size: int | None = None):
        return b"x"


def test_probe_teos_zip_metadata_prefers_head():
    calls = []

    def _opener(request, timeout=60):
        calls.append((request.get_method(), request.full_url))
        return _FakeResponse(
            url="https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
            headers={
                "ETag": '"etag-1"',
                "Last-Modified": "Thu, 20 Mar 2026 00:00:00 GMT",
                "Content-Length": "1234",
            },
        )

    result = probe_teos_zip_metadata(
        "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
        opener=_opener,
    )

    assert calls == [("HEAD", "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip")]
    assert result.method_used == "HEAD"
    assert result.etag == '"etag-1"'
    assert result.last_modified == "Thu, 20 Mar 2026 00:00:00 GMT"
    assert result.content_length == 1234


def test_probe_teos_zip_metadata_falls_back_to_get_when_head_is_not_supported():
    calls = []

    def _opener(request, timeout=60):
        calls.append(request.get_method())
        if request.get_method() == "HEAD":
            raise HTTPError(request.full_url, 405, "Method Not Allowed", hdrs=None, fp=None)
        return _FakeResponse(
            url="https://downloads.irs.gov/2026_TEOS_XML_03A.zip",
            headers={
                "ETag": '"etag-2"',
                "Last-Modified": "Fri, 21 Mar 2026 00:00:00 GMT",
                "Content-Length": "4321",
            },
        )

    result = probe_teos_zip_metadata(
        "https://apps.irs.gov/pub/epostcard/990/xml/2026/2026_TEOS_XML_03A.zip",
        opener=_opener,
    )

    assert calls == ["HEAD", "GET"]
    assert result.method_used == "GET"
    assert result.resolved_source_url == "https://downloads.irs.gov/2026_TEOS_XML_03A.zip"


def test_should_download_teos_zip_when_no_previous_manifest_record_exists():
    decision = should_download_teos_zip(
        previous=None,
        current_probe=probe_teos_zip_metadata(
            "https://example.org/2025_TEOS_XML_01A.zip",
            opener=lambda request, timeout=60: _FakeResponse(
                url=request.full_url,
                headers={"ETag": '"etag-1"'},
            ),
        ),
    )

    assert decision.should_download is True
    assert decision.reason == "new_zip"


def test_should_download_teos_zip_when_probe_metadata_changes():
    previous = _PreviousProbeState(
        etag='"etag-1"',
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
    )
    current = probe_teos_zip_metadata(
        "https://example.org/2025_TEOS_XML_01A.zip",
        opener=lambda request, timeout=60: _FakeResponse(
            url=request.full_url,
            headers={"ETag": '"etag-2"', "Content-Length": "1234"},
        ),
    )

    decision = should_download_teos_zip(previous=previous, current_probe=current)

    assert decision.should_download is True
    assert decision.reason == "etag_changed"


def test_should_download_teos_zip_skips_unchanged_remote_zip():
    previous = _PreviousProbeState(
        etag='"etag-1"',
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
    )
    current = probe_teos_zip_metadata(
        "https://example.org/2025_TEOS_XML_01A.zip",
        opener=lambda request, timeout=60: _FakeResponse(
            url=request.full_url,
            headers={
                "ETag": '"etag-1"',
                "Last-Modified": "Thu, 20 Mar 2026 00:00:00 GMT",
                "Content-Length": "1234",
            },
        ),
    )

    decision = should_download_teos_zip(previous=previous, current_probe=current)

    assert decision.should_download is False
    assert decision.reason == "unchanged_remote_zip"

