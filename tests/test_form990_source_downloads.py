from __future__ import annotations

import json

from infrastructure.charity_status.form990.source_downloads import execute_source_download_batch, load_downloaded_source_state, plan_source_downloads


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        return {"Body": _Body(self.store[(Bucket, Key)]["Body"])}

    def list_objects_v2(self, Bucket, Prefix):
        return {"Contents": [{"Key": key} for (b, key), value in self.store.items() if b == Bucket and key.startswith(Prefix)]}


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self):
        if isinstance(self._value, bytes):
            return self._value
        return str(self._value).encode("utf-8")


def _source(kind: str, url: str, archive_key: str, filename: str) -> dict[str, str]:
    return {
        "source_year": "2024",
        "source_kind": kind,
        "source_url": url,
        "source_filename": filename,
        "source_archive_key": archive_key,
        "source_signature": f"sig-{archive_key}",
        "page_url": "https://example.org/page",
    }


def test_execute_source_download_batch_persists_raw_csv():
    s3 = FakeS3()
    manifest = execute_source_download_batch(
        sources=[_source("csv_index", "https://example.org/index_2024.csv", "index_2024", "index_2024.csv")],
        bucket="test-bucket",
        raw_source_prefix="form990/raw-sources/",
        manifest_prefix="form990/normalized/manifests/",
        s3_client=s3,
        run_id="run1",
        batch_index=0,
        timeout_seconds=10,
        downloader=lambda source_url, timeout_seconds: (b"col1,col2\n1,2\n", "text/csv"),
    )
    assert manifest["downloaded_count"] == 1
    raw_keys = [key for (bucket, key), value in s3.store.items() if bucket == "test-bucket" and key.startswith("form990/raw-sources/")]
    assert len(raw_keys) == 1
    assert raw_keys[0].endswith("/index_2024.csv")
    state = load_downloaded_source_state(s3, "test-bucket", "form990/normalized/manifests/")
    assert len(state) == 1
    assert state[0]["raw_source_s3_key"] == raw_keys[0]


def test_execute_source_download_batch_persists_raw_zip():
    s3 = FakeS3()
    manifest = execute_source_download_batch(
        sources=[_source("zip_archive", "https://example.org/2024_TEOS_XML_11B.zip", "2024_teos_xml_11b", "2024_TEOS_XML_11B.zip")],
        bucket="test-bucket",
        raw_source_prefix="form990/raw-sources/",
        manifest_prefix="form990/normalized/manifests/",
        s3_client=s3,
        run_id="run2",
        batch_index=1,
        timeout_seconds=10,
        downloader=lambda source_url, timeout_seconds: (b"PK\x03\x04fakezip", "application/zip"),
    )
    assert manifest["downloaded_count"] == 1
    raw_keys = [key for (bucket, key), value in s3.store.items() if bucket == "test-bucket" and key.startswith("form990/raw-sources/")]
    assert len(raw_keys) == 1
    assert raw_keys[0].endswith("/2024_TEOS_XML_11B.zip")
    put_record = s3.store[("test-bucket", raw_keys[0])]
    assert put_record["Metadata"]["source_kind"] == "zip_archive"


def test_plan_source_downloads_skips_matching_signature():
    source = _source("csv_index", "https://example.org/index_2024.csv", "index_2024", "index_2024.csv")
    plan = plan_source_downloads(
        [source],
        [
            {
                "source_year": "2024",
                "source_kind": "csv_index",
                "source_archive_key": "index_2024",
                "source_signature": "sig-index_2024",
                "raw_source_s3_key": "form990/raw-sources/2024/csv_index/index_2024/sig-index_2024/index_2024.csv",
                "downloaded_at": "2026-01-01T00:00:00+00:00",
            }
        ],
    )
    assert plan["to_download"] == []
    assert len(plan["skipped"]) == 1
    assert plan["skipped"][0]["reason"] == "already_downloaded"


def test_execute_source_download_batch_writes_manifest():
    s3 = FakeS3()
    execute_source_download_batch(
        sources=[_source("csv_index", "https://example.org/index_2024.csv", "index_2024", "index_2024.csv")],
        bucket="test-bucket",
        raw_source_prefix="form990/raw-sources/",
        manifest_prefix="form990/normalized/manifests/",
        s3_client=s3,
        run_id="run3",
        batch_index=4,
        timeout_seconds=10,
        downloader=lambda source_url, timeout_seconds: (b"a,b\n", "text/csv"),
    )
    manifest_body = s3.store[("test-bucket", "form990/normalized/manifests/source-download/runs/run3/batch_00004.json")]["Body"]
    payload = json.loads(manifest_body.decode("utf-8"))
    assert payload["downloaded_count"] == 1


def test_execute_source_download_batch_retries_transient_download_errors():
    s3 = FakeS3()
    attempts = {"count": 0}

    def _flaky(source_url, timeout_seconds):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TimeoutError("temporary timeout")
        return (b"ok", "text/plain")

    manifest = execute_source_download_batch(
        sources=[_source("csv_index", "https://example.org/index_2024.csv", "index_2024", "index_2024.csv")],
        bucket="test-bucket",
        raw_source_prefix="form990/raw-sources/",
        manifest_prefix="form990/normalized/manifests/",
        s3_client=s3,
        run_id="run4",
        batch_index=0,
        timeout_seconds=10,
        downloader=_flaky,
        max_attempts=3,
    )
    assert manifest["downloaded_count"] == 1
    assert attempts["count"] == 3
