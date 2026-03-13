import importlib
import json
import sys

from infrastructure.charity_status.form990.models import Form990IndexRecord

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
        keys = [{"Key": key} for (b, key), _body in self.store.items() if b == Bucket and key.startswith(Prefix)]
        return {"Contents": keys}


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self):
        if isinstance(self._value, bytes):
            return self._value
        return str(self._value).encode("utf-8")


def test_worker_processes_chunk_success(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setenv("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r1/chunks/c1.json"
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=chunk_key,
        Body=json.dumps({"records": [{"ein": "123456789", "tax_year": "2024", "return_type": "990", "irs_object_id": "obj-1"}]}).encode("utf-8"),
    )
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "records_processed": len(payload),
        "parsed_count": 0,
        "failed_count": 0,
    }
    event = {"Records": [{"body": json.dumps({"run_id": "r1", "chunk_id": "c1", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 1})}]}
    result = module.handler(event, None)
    assert result["status"] == "success"
    assert ("test-bucket", "ops/form990-runs/r1/results/c1.json") in fake_s3.store


def test_worker_rejects_invalid_runtime_config(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_ZIP_FETCH_TIMEOUT_SECONDS", "0")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    event = {"Records": [{"body": json.dumps({})}]}
    try:
        module.handler(event, None)
        assert False, "expected config validation failure"
    except ValueError as exc:
        assert "FORM990_ZIP_FETCH_TIMEOUT_SECONDS must be > 0" in str(exc)


def test_worker_chunk_failure_raises_for_retry(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setenv("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r2/chunks/c2.json"
    fake_s3.put_object(Bucket="test-bucket", Key=chunk_key, Body=json.dumps({"records": [{"ein": "123"}]}).encode("utf-8"))

    def _boom(self, payload, download_raw=True, record_downloader=None):
        raise RuntimeError("boom")

    module.Form990IngestService.ingest_index_payload = _boom
    event = {"Records": [{"body": json.dumps({"run_id": "r2", "chunk_id": "c2", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 2})}]}
    try:
        module.handler(event, None)
        assert False, "expected exception"
    except RuntimeError:
        pass
    assert ("test-bucket", "ops/form990-runs/r2/results/c2.json") in fake_s3.store
    failure = json.loads(fake_s3.store[("test-bucket", "ops/form990-runs/r2/results/c2.json")]["Body"].decode("utf-8"))
    assert failure["error_type"] == "processing_error"


def test_worker_processes_source_catalog_chunk_success(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setenv("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r3/chunks/c3.json"
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=chunk_key,
        Body=json.dumps(
            {
                "task_type": "source_download",
                "chunk_index": 0,
                "sources": [
                    {
                        "source_year": "2024",
                        "source_kind": "csv_index",
                        "source_url": "https://example.org/index_2024.csv",
                        "source_filename": "index_2024.csv",
                        "source_archive_key": "index_2024",
                        "source_signature": "sig-1",
                        "page_url": "https://example.org/page",
                    }
                ],
            }
        ).encode("utf-8"),
    )
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/r3/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    event = {"Records": [{"body": json.dumps({"run_id": "r3", "chunk_id": "c3", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 1})}]}
    result = module.handler(event, None)
    assert result["status"] == "success"
    stored = json.loads(fake_s3.store[("test-bucket", "ops/form990-runs/r3/results/c3.json")]["Body"].decode("utf-8"))
    assert stored["task_type"] == "source_download"
    assert stored["result"]["status"] == "success"


def test_worker_filing_chunk_uses_zip_backed_loader(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setenv("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r4/chunks/c4.json"
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=chunk_key,
        Body=json.dumps(
            {
                "task_type": "filing_records",
                "records": [
                    {
                        "ein": "123456789",
                        "tax_year": "2024",
                        "return_type": "990",
                        "filing_date": "2025-01-01",
                        "irs_object_id": "obj-1",
                        "xml_url": "https://example.org/obj-1.xml",
                        "source_year": "2024",
                    }
                ],
                "zip_sources": [],
            }
        ).encode("utf-8"),
    )

    def _ingest(self, payload, download_raw=True, record_downloader=None):
        assert callable(record_downloader)
        fallback_bytes, source_ref = record_downloader(
            Form990IndexRecord(
                ein="123456789",
                tax_year="2024",
                filing_date="2025-01-01",
                return_type="990",
                irs_object_id="obj-1",
                xml_url="https://example.org/obj-1.xml",
                source_year="2024",
                source_archive=None,
                source_signature=None,
            )
        )
        assert fallback_bytes == b"<xml/>"
        assert source_ref == "https://example.org/obj-1.xml"
        return {
            "records_processed": len(payload),
            "parsed_count": 1,
            "failed_count": 0,
            "records": [{"parse_status": "parsed", "raw_s3_key": "form990/raw/123456789/2024/obj-1.xml"}],
        }

    module.Form990IngestService.ingest_index_payload = _ingest
    module._update_run_status = lambda *args, **kwargs: None
    module._write_summary_snapshot = lambda *args, **kwargs: None
    module.update_filing_state_from_ingest_result = lambda **kwargs: []
    module.ZipBackedXmlLoader.load = lambda self, record: (b"<xml/>", str(record.xml_url or ""))
    event = {"Records": [{"body": json.dumps({"run_id": "r4", "chunk_id": "c4", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 1})}]}
    result = module.handler(event, None)
    assert result["status"] == "success"


def test_worker_skips_chunk_when_result_already_succeeded(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r5/chunks/c5.json"
    result_key = "ops/form990-runs/r5/results/c5.json"
    fake_s3.put_object(Bucket="test-bucket", Key=chunk_key, Body=json.dumps({"records": [{"ein": "123"}]}).encode("utf-8"))
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=result_key,
        Body=json.dumps({"status": "succeeded", "result": {"records_processed": 1}}).encode("utf-8"),
    )
    module.Form990IngestService.ingest_index_payload = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not run"))
    event = {"Records": [{"body": json.dumps({"run_id": "r5", "chunk_id": "c5", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 2})}]}
    result = module.handler(event, None)
    assert result["status"] == "success"
