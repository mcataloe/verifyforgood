import importlib
import json
import sys


class FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body):
        self.store[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        return {"Body": _Body(self.store[(Bucket, Key)])}

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
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r1/chunks/c1.json"
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=chunk_key,
        Body=json.dumps({"records": [{"ein": "123456789", "tax_year": "2024", "return_type": "990", "irs_object_id": "obj-1"}]}).encode("utf-8"),
    )
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True: {
        "records_processed": len(payload),
        "parsed_count": 0,
        "failed_count": 0,
    }
    event = {"Records": [{"body": json.dumps({"run_id": "r1", "chunk_id": "c1", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 1})}]}
    result = module.handler(event, None)
    assert result["status"] == "success"
    assert ("test-bucket", "ops/form990-runs/r1/results/c1.json") in fake_s3.store


def test_worker_chunk_failure_raises_for_retry(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r2/chunks/c2.json"
    fake_s3.put_object(Bucket="test-bucket", Key=chunk_key, Body=json.dumps({"records": [{"ein": "123"}]}).encode("utf-8"))

    def _boom(self, payload, download_raw=True):
        raise RuntimeError("boom")

    module.Form990IngestService.ingest_index_payload = _boom
    event = {"Records": [{"body": json.dumps({"run_id": "r2", "chunk_id": "c2", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 2})}]}
    try:
        module.handler(event, None)
        assert False, "expected exception"
    except RuntimeError:
        pass
    assert ("test-bucket", "ops/form990-runs/r2/results/c2.json") in fake_s3.store


def test_worker_processes_source_catalog_chunk_success(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_BUCKET", "test-bucket")
    monkeypatch.setenv("OPS_METADATA_PREFIX", "ops")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")
    chunk_key = "ops/form990-runs/r3/chunks/c3.json"
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=chunk_key,
        Body=json.dumps({"task_type": "source_catalog", "sources": [{"source_year": "2024", "source_kind": "csv_index"}]}).encode("utf-8"),
    )
    event = {"Records": [{"body": json.dumps({"run_id": "r3", "chunk_id": "c3", "chunk_s3_bucket": "test-bucket", "chunk_s3_key": chunk_key, "attempt": 1})}]}
    result = module.handler(event, None)
    assert result["status"] == "success"
    stored = json.loads(fake_s3.store[("test-bucket", "ops/form990-runs/r3/results/c3.json")].decode("utf-8"))
    assert stored["task_type"] == "source_catalog"
    assert stored["result"]["status"] == "deferred"
