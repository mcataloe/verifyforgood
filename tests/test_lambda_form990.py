import importlib
import json
import sys

from infrastructure.charity_status.form990.models import Form990IndexRecord
from infrastructure.charity_status.form990.source_catalog import Form990SourceArtifact, normalize_configured_sources


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


class FakeSQS:
    def __init__(self):
        self.messages = []

    def send_message(self, QueueUrl, MessageBody):
        self.messages.append({"QueueUrl": QueueUrl, "MessageBody": MessageBody})
        return {"MessageId": str(len(self.messages))}


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


def _source(
    *,
    source_year: str,
    source_kind: str,
    source_url: str,
    source_archive_key: str,
) -> Form990SourceArtifact:
    return Form990SourceArtifact(
        source_year=source_year,
        source_kind=source_kind,
        source_url=source_url,
        source_filename=source_url.rstrip("/").split("/")[-1],
        source_archive_key=source_archive_key,
        discovered_at="2026-01-01T00:00:00+00:00",
        source_signature=f"sig-{source_archive_key}",
        page_url="https://www.irs.gov/charities-non-profits/form-990-series-downloads",
    )


def test_lambda_form990_success(monkeypatch):
    module, _ = _load_module(monkeypatch)
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


def test_discovery_mode_persists_source_catalog_and_diff(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    module.fetch_index_records = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("filing fetch should not run in discovery stage"))

    result = module.handler({"mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["stage"] == "source_catalog"
    assert body["source_catalog_count"] == 1
    assert body["new_sources"] == 1
    assert body["changed_sources"] == 0
    assert body["processed_records"] == 0
    assert ("test-bucket", body["discovery_state_key"]) in fake_s3.store
    assert ("test-bucket", body["discovery_manifest_key"]) in fake_s3.store
    assert ("test-bucket", body["discovery_diff_key"]) in fake_s3.store


def test_discovery_mode_reports_unchanged_state(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    state_key = module.discovery_state_key(module.MANIFEST_PREFIX)
    existing = normalize_configured_sources([{"year": "2024", "index_url": "https://example.org/index_2024.csv"}])[0].to_dict()
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=state_key,
        Body=json.dumps({"sources": [existing]}).encode("utf-8"),
    )

    result = module.handler({"mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["new_sources"] == 0
    assert body["changed_sources"] == 0
    assert body["removed_sources"] == 0
    assert body["unchanged_sources"] == 1


def test_policy_config_override_target_years(monkeypatch):
    module, _ = _load_module(monkeypatch)
    result = module.handler(
        {
            "mode": "incremental",
            "target_years": ["2023"],
            "source_catalog": [
                {"year": "2022", "index_url": "https://example.org/index_2022.csv"},
                {"year": "2023", "index_url": "https://example.org/index_2023.csv"},
            ],
        },
        None,
    )
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["policy"]["target_years"] == ["2023"]
    assert body["selected_source_count"] == 1


def test_irs_page_source_mode_discovers_source_artifacts(monkeypatch):
    module, _ = _load_module(monkeypatch)
    monkeypatch.setenv("FORM990_SOURCE_MODE", "irs_page")
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    module.discover_irs_form990_sources = lambda page_url, timeout_seconds=60, now=None: [
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
        _source(source_year="2024", source_kind="zip_archive", source_url="https://example.org/2024_TEOS_XML_11B.zip", source_archive_key="2024_teos_xml_11b"),
    ]

    result = module.handler({"mode": "incremental"}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["source_mode"] == "irs_page"
    assert body["source_catalog_count"] == 2
    assert body["scheduled_source_count"] == 2


def test_orchestrated_mode_enqueues_source_chunks(monkeypatch):
    fake_s3 = FakeS3()
    fake_sqs = FakeSQS()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_SOURCE_MODE", "irs_page")
    monkeypatch.setenv("FORM990_EXECUTION_MODE", "orchestrated")
    monkeypatch.setenv("FORM990_WORK_QUEUE_URL", "https://sqs.example/work")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3 if name == "s3" else fake_sqs)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    module.discover_irs_form990_sources = lambda page_url, timeout_seconds=60, now=None: [
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
        _source(source_year="2024", source_kind="zip_archive", source_url="https://example.org/2024_TEOS_XML_11B.zip", source_archive_key="2024_teos_xml_11b"),
    ]
    result = module.handler({"mode": "bootstrap", "chunk_size": 1}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["execution_mode"] == "orchestrated"
    assert body["stage"] == "source_catalog"
    assert body["chunk_count"] == 2
    assert len(fake_sqs.messages) == 2


def test_orchestrated_mode_applies_target_year_policy_before_chunking(monkeypatch):
    fake_s3 = FakeS3()
    fake_sqs = FakeSQS()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_SOURCE_MODE", "irs_page")
    monkeypatch.setenv("FORM990_EXECUTION_MODE", "orchestrated")
    monkeypatch.setenv("FORM990_WORK_QUEUE_URL", "https://sqs.example/work")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3 if name == "s3" else fake_sqs)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    module.discover_irs_form990_sources = lambda page_url, timeout_seconds=60, now=None: [
        _source(source_year="2023", source_kind="csv_index", source_url="https://example.org/index_2023.csv", source_archive_key="index_2023"),
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
    ]
    result = module.handler({"mode": "incremental", "target_years": ["2023"], "chunk_size": 10}, None)
    body = json.loads(result["body"])
    assert result["statusCode"] == 200
    assert body["selected_source_count"] == 1
    assert body["chunk_count"] == 1
    assert len(fake_sqs.messages) == 1
