import importlib
import json
import pathlib
import sys

from infrastructure.charity_status.form990.models import Form990IndexRecord


class FakeS3:
    def __init__(self):
        self.puts = []
        self.store = {}

    def put_object(self, Bucket, Key, Body):
        self.puts.append({"Bucket": Bucket, "Key": Key, "Body": Body})
        self.store[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        body = self.store[(Bucket, Key)]
        return {"Body": _Body(body)}


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self):
        if isinstance(self._value, bytes):
            return self._value
        return str(self._value).encode("utf-8")


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


def test_lambda_form990_loads_records_from_index_url(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: [
        Form990IndexRecord(
            ein="123456789",
            tax_year="2023",
            filing_date="2024-05-15",
            return_type="990",
            irs_object_id="obj-1",
            xml_url="https://example.org/obj-1.xml",
            source_year=source_year,
            source_archive=source_archive,
            source_signature="sig-1",
        )
    ]

    result = module.handler({"index_url": "https://example.org/index.json", "download_raw": False}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["records_processed"] == 1
    assert body["records"][0]["ein"] == "123456789"


def test_lambda_form990_index_filters_by_ein_and_limit(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: [
        Form990IndexRecord(ein="123456789", tax_year="2023", filing_date=None, return_type="990", irs_object_id="1", xml_url=None, source_year=source_year, source_archive=source_archive, source_signature="1"),
        Form990IndexRecord(ein="987654321", tax_year="2023", filing_date=None, return_type="990", irs_object_id="2", xml_url=None, source_year=source_year, source_archive=source_archive, source_signature="2"),
    ]

    result = module.handler(
        {"index_url": "https://example.org/index.json", "download_raw": False, "eins": ["987654321"], "limit": 1},
        None,
    )
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["records_processed"] == 1
    assert body["records"][0]["ein"] == "987654321"


def test_incremental_noop_when_no_changes(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: []
    result = module.handler({"mode": "incremental", "reconciliation_all_years": True, "source_catalog": [{"year": "2024", "index_url": "https://example.org/2024.json"}]}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["selected_records"] == 0
    assert body["processed_records"] == 0


def test_incremental_processes_new_filings(monkeypatch):
    module, _ = _load_module(monkeypatch)

    def _records(index_url, source_year, source_archive, timeout_seconds=60):
        return [
            Form990IndexRecord(
                ein="123456789",
                tax_year="2024",
                filing_date="2025-01-01",
                return_type="990",
                irs_object_id="obj-new",
                xml_url="https://example.org/new.xml",
                source_year="2024",
                source_archive="a",
                source_signature="sig-new",
            )
        ]

    module.fetch_index_records = _records
    result = module.handler({"mode": "incremental", "reconciliation_all_years": True, "source_catalog": [{"year": "2024", "index_url": "https://example.org/2024.json"}]}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["new_records"] == 1
    assert body["processed_records"] == 1


def test_incremental_processes_changed_signature(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=module.state_manifest_key(module.MANIFEST_PREFIX),
        Body=json.dumps({"entries": [{"irs_object_id": "obj-1", "source_signature": "sig-old"}]}).encode("utf-8"),
    )

    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: [
        Form990IndexRecord(
            ein="123456789",
            tax_year="2024",
            filing_date="2025-01-01",
            return_type="990",
            irs_object_id="obj-1",
            xml_url="https://example.org/new.xml",
            source_year="2024",
            source_archive="a",
            source_signature="sig-new",
        )
    ]
    result = module.handler({"mode": "incremental", "reconciliation_all_years": True, "source_catalog": [{"year": "2024", "index_url": "https://example.org/2024.json"}]}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["changed_records"] == 1
    assert body["processed_records"] == 1


def test_resume_checkpoint_behavior(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=module.checkpoint_key(module.MANIFEST_PREFIX),
        Body=json.dumps({"offset": 1}).encode("utf-8"),
    )
    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: [
        Form990IndexRecord(
            ein="111111111",
            tax_year="2024",
            filing_date="2025-01-01",
            return_type="990",
            irs_object_id="obj-1",
            xml_url="https://example.org/1.xml",
            source_year="2024",
            source_archive="a",
            source_signature="sig-1",
        ),
        Form990IndexRecord(
            ein="222222222",
            tax_year="2024",
            filing_date="2025-01-01",
            return_type="990",
            irs_object_id="obj-2",
            xml_url="https://example.org/2.xml",
            source_year="2024",
            source_archive="a",
            source_signature="sig-2",
        ),
    ]
    result = module.handler({"mode": "bootstrap", "resume": True, "source_catalog": [{"year": "2024", "index_url": "https://example.org/2024.json"}]}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["selected_records"] == 2
    assert body["processed_records"] == 1


def test_policy_config_override_target_years(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: [
        Form990IndexRecord(
            ein="111111111",
            tax_year=source_year,
            filing_date="2025-01-01",
            return_type="990",
            irs_object_id=f"obj-{source_year}",
            xml_url="https://example.org/x.xml",
            source_year=source_year,
            source_archive=source_archive,
            source_signature=f"sig-{source_year}",
        )
    ]
    result = module.handler(
        {
            "mode": "incremental",
            "target_years": ["2023"],
            "source_catalog": [
                {"year": "2022", "index_url": "https://example.org/2022.json"},
                {"year": "2023", "index_url": "https://example.org/2023.json"},
            ],
        },
        None,
    )
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["policy"]["target_years"] == ["2023"]
