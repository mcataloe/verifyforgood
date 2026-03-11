import importlib
import json
import pathlib
import sys


class FakeS3:
    def __init__(self):
        self.puts = []

    def put_object(self, Bucket, Key, Body):
        self.puts.append({"Bucket": Bucket, "Key": Key, "Body": Body})


def _load_module(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_RAW_PREFIX", "form990/raw/")
    monkeypatch.setenv("FORM990_METADATA_PREFIX", "form990/normalized/metadata/")
    monkeypatch.setenv("FORM990_MANIFEST_PREFIX", "form990/normalized/manifests/")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")
    return module, fake_s3


def test_lambda_form990_success(monkeypatch):
    module, _ = _load_module(monkeypatch)
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_text(encoding="utf-8")

    event = {
        "records": [
            {
                "ein": "123456789",
                "tax_year": "2023",
                "filing_date": "2024-05-15",
                "return_type": "990",
                "irs_object_id": "obj-1",
                "xml_url": "https://example.org/obj-1.xml",
            }
        ],
        "download_raw": False,
    }

    result = module.handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["records_processed"] == 1
    assert body["records"][0]["parse_status"] == "index_only"


def test_lambda_form990_invalid_records_payload(monkeypatch):
    module, _ = _load_module(monkeypatch)
    result = module.handler({"records": {}}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "records must be an array" in body["message"]


def test_lambda_form990_json_body(monkeypatch):
    module, _ = _load_module(monkeypatch)

    result = module.handler({"body": "{not-json"}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "valid JSON" in body["message"]
