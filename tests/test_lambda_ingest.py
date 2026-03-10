import importlib
import os
import sys
from types import SimpleNamespace


def _load_module(monkeypatch):
    uploads = []

    class FakeS3:
        def put_object(self, Bucket, Key, Body):
            uploads.append({"Bucket": Bucket, "Key": Key, "Body": Body})

    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setattr("boto3.client", lambda name: FakeS3())

    sys.modules.pop("infrastructure.lambda_ingest", None)
    module = importlib.import_module("infrastructure.lambda_ingest")
    return module, uploads


def test_handler_success(monkeypatch):
    module, uploads = _load_module(monkeypatch)

    async def fake_download(session, filename):
        return f"content-{filename}".encode()

    monkeypatch.setattr(module, "_download_file", fake_download)

    result = module.handler({}, SimpleNamespace())

    assert result["status"] == "success"
    assert sorted(result["downloaded"]) == sorted(module.IRS_FILES)
    assert result["failed"] == []
    assert len(uploads) == len(module.IRS_FILES)


def test_handler_partial_failure(monkeypatch):
    module, uploads = _load_module(monkeypatch)

    async def fake_download(session, filename):
        if filename == "eo2.csv":
            raise RuntimeError("network down")
        return b"ok"

    monkeypatch.setattr(module, "_download_file", fake_download)

    result = module.handler({}, SimpleNamespace())

    assert result["status"] == "partial_success"
    assert "eo2.csv" not in result["downloaded"]
    assert any(item["filename"] == "eo2.csv" for item in result["failed"])
    assert len(uploads) == len(module.IRS_FILES) - 1


def test_handler_upload_failure(monkeypatch):
    module, uploads = _load_module(monkeypatch)

    async def fake_download(session, filename):
        return b"ok"

    monkeypatch.setattr(module, "_download_file", fake_download)

    original_put_object = module.s3.put_object

    def flaky_put_object(Bucket, Key, Body):
        if Key.endswith("eo3.csv"):
            raise RuntimeError("s3 error")
        return original_put_object(Bucket=Bucket, Key=Key, Body=Body)

    monkeypatch.setattr(module.s3, "put_object", flaky_put_object)

    result = module.handler({}, SimpleNamespace())

    assert result["status"] == "partial_success"
    assert "eo3.csv" not in result["downloaded"]
    assert any(item["filename"] == "eo3.csv" for item in result["failed"])
    assert len(uploads) == len(module.IRS_FILES) - 1


def test_handler_all_failure(monkeypatch):
    module, uploads = _load_module(monkeypatch)

    async def fake_download(session, filename):
        raise RuntimeError("download fail")

    monkeypatch.setattr(module, "_download_file", fake_download)

    result = module.handler({}, SimpleNamespace())

    assert result["status"] == "failed"
    assert result["downloaded"] == []
    assert len(result["failed"]) == len(module.IRS_FILES)
    assert uploads == []
