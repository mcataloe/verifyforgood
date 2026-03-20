import importlib
import json
import sys

from infrastructure.charity_status.form990.models import Form990IndexRecord
from infrastructure.charity_status.form990.source_catalog import Form990SourceArtifact, normalize_configured_sources
from infrastructure.charity_status.form990.teos_zip_discovery import TeosZipDiscoveryRecord


def _response_envelope(response):
    return json.loads(response["body"])


def _response_data(response):
    return _response_envelope(response)["data"]


def _response_error_message(response):
    return _response_envelope(response)["errors"][0]["message"]


class FakeS3:
    def __init__(self):
        self.puts = []
        self.store = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.puts.append({"Bucket": Bucket, "Key": Key, "Body": Body, **kwargs})
        self.store[(Bucket, Key)] = {"Body": Body, **kwargs}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError(Key)
        body = self.store[(Bucket, Key)]["Body"]
        return {"Body": _Body(body)}

    def list_objects_v2(self, Bucket, Prefix):
        keys = [{"Key": key} for (b, key), value in self.store.items() if b == Bucket and key.startswith(Prefix)]
        return {"Contents": keys}


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


class _ReconciliationResult:
    def __init__(self, *, current_records=None, selected_records=None, new_count=0, changed_count=0, unchanged_count=0, incomplete_count=0):
        self.current_records = tuple(current_records or [])
        self.selected_records = tuple(selected_records or [])
        self.latest_state_entries = ()
        self.new_count = new_count
        self.changed_count = changed_count
        self.unchanged_count = unchanged_count
        self.incomplete_count = incomplete_count
        self.catalog_key = "form990/normalized/manifests/filings/run1/catalog.json"
        self.diff_key = "form990/normalized/manifests/filings/run1/diff.json"
        self.state_key = "form990/normalized/manifests/state/latest_filing_manifest.json"


def _load_module(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_RAW_PREFIX", "form990/raw/")
    monkeypatch.setenv("FORM990_RAW_SOURCE_PREFIX", "form990/raw-sources/")
    monkeypatch.setenv("FORM990_METADATA_PREFIX", "form990/normalized/metadata/")
    monkeypatch.setenv("FORM990_MANIFEST_PREFIX", "form990/normalized/manifests/")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")
    module.fetch_teos_download_page_html = lambda page_url, timeout_seconds=60: "<html></html>"
    module.parse_teos_zip_links = lambda html, page_url, target_year, now=None: []
    module.probe_teos_zip_metadata = lambda source_url, timeout_seconds=60, now=None, max_attempts=3, opener=None: (_ for _ in ()).throw(
        AssertionError("probe_teos_zip_metadata should not be called when no TEOS ZIP records are discovered")
    )
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
    envelope = _response_envelope(result)
    body = envelope["data"]

    assert result["statusCode"] == 200
    assert envelope["api_version"] == "v1"
    assert envelope["api_release"] == "1.0.0"
    assert envelope["plan"] == "internal"
    assert envelope["request_id"]
    assert body["records_processed"] == 1
    assert body["records"][0]["parse_status"] == "index_only"


def test_lambda_form990_invalid_records_payload(monkeypatch):
    module, _ = _load_module(monkeypatch)
    result = module.handler({"records": {}}, None)

    assert result["statusCode"] == 400
    assert "records must be an array" in _response_error_message(result)


def test_lambda_form990_rejects_invalid_runtime_config(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_CHUNK_SIZE", "0")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")
    result = module.handler({}, None)
    assert result["statusCode"] == 500
    assert "FORM990_CHUNK_SIZE must be > 0" in _response_error_message(result)


def test_lambda_form990_rejects_invalid_source_mode_config(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_SOURCE_MODE", "invalid")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    result = module.handler({}, None)

    assert result["statusCode"] == 500
    assert "FORM990_SOURCE_MODE must be one of configured, static_manifest, or irs_page" in _response_error_message(result)


def test_lambda_form990_rejects_blank_legacy_irs_page_url_config(monkeypatch):
    fake_s3 = FakeS3()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_SOURCE_MODE", "irs_page")
    monkeypatch.setenv("FORM990_IRS_DOWNLOADS_PAGE_URL", "")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    result = module.handler({}, None)

    assert result["statusCode"] == 500
    assert "FORM990_IRS_DOWNLOADS_PAGE_URL is required when FORM990_SOURCE_MODE=irs_page" in _response_error_message(result)


def test_lambda_form990_json_body(monkeypatch):
    module, _ = _load_module(monkeypatch)

    result = module.handler({"body": "{not-json"}, None)

    assert result["statusCode"] == 400
    assert "valid JSON" in _response_error_message(result)


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
    body = _response_data(result)

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
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["records_processed"] == 1
    assert body["records"][0]["ein"] == "987654321"


def test_discovery_mode_persists_source_catalog_and_downloads_csv(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    module.fetch_index_records = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("filing fetch should not run in source download stage"))
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": [{**kwargs["sources"][0], "status": "downloaded", "raw_source_s3_key": "form990/raw-sources/2024/csv_index/index_2024/sig/index_2024.csv"}] if kwargs["sources"] else [],
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult(
        current_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2024",
                filing_date="2025-01-01",
                return_type="990",
                irs_object_id="obj-1",
                xml_url="https://example.org/obj-1.xml",
                source_year="2024",
                source_archive="index_2024",
                source_signature="sig-1",
            )
        ],
        selected_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2024",
                filing_date="2025-01-01",
                return_type="990",
                irs_object_id="obj-1",
                xml_url="https://example.org/obj-1.xml",
                source_year="2024",
                source_archive="index_2024",
                source_signature="sig-1",
            )
        ],
        new_count=1,
    )
    module.update_filing_state_from_ingest_result = lambda **kwargs: []
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": len(payload),
        "parsed_count": len(payload),
        "failed_count": 0,
        "manifest_s3_key": "form990/normalized/manifests/manifest_20260101T000000Z.json",
        "records": [{"parse_status": "parsed", "raw_s3_key": "form990/raw/123456789/2024/obj-1.xml"}],
    }

    result = module.handler({"run_id": "run1", "mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["stage"] == "csv_reconciliation"
    assert body["source_catalog_count"] == 1
    assert body["new_sources"] == 1
    assert body["changed_sources"] == 0
    assert body["downloaded_source_count"] == 1
    assert body["selected_records"] == 1
    assert body["processed_records"] == 1
    assert ("test-bucket", body["discovery_state_key"]) in fake_s3.store
    assert ("test-bucket", body["discovery_manifest_key"]) in fake_s3.store
    assert ("test-bucket", body["discovery_diff_key"]) in fake_s3.store
    assert body["source_download_manifest_key"].endswith("batch_00000.json")


def test_discovery_mode_syncs_teos_zip_manifest_foundation(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    module.fetch_teos_download_page_html = lambda page_url, timeout_seconds=60: "<html></html>"
    module.parse_teos_zip_links = lambda html, page_url, target_year, now=None: [
        TeosZipDiscoveryRecord(
            tax_year=str(target_year),
            source_url=f"https://apps.irs.gov/pub/epostcard/990/xml/{target_year}/{target_year}_TEOS_XML_01A.zip",
            source_filename=f"{target_year}_TEOS_XML_01A.zip",
            zip_basename=f"{target_year}_TEOS_XML_01A",
            discovered_at="2026-01-01T00:00:00+00:00",
            page_url=page_url,
        )
    ]
    module.probe_teos_zip_metadata = lambda source_url, timeout_seconds=60, now=None, max_attempts=3, opener=None: module.TeosZipProbeResult(
        source_url=source_url,
        resolved_source_url=source_url,
        etag='"etag-1"',
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
        checked_at="2026-01-01T00:00:00+00:00",
        method_used="HEAD",
    )
    module.execute_source_download_batch = lambda **kwargs: {"manifest_key": None, "downloaded_count": 0, "downloads": []}
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "records": [],
    }

    result = module.handler({"run_id": "run1", "mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["teos_zip_manifest"]["discovered_count"] == 1
    assert body["teos_zip_manifest"]["new_count"] == 1
    assert body["teos_zip_manifest"]["scheduled_download_count"] == 1
    assert body["teos_zip_manifest"]["catalog_keys"] == [
        "form990/normalized/manifests/teos-zip/runs/run1/year=2024/catalog.json"
    ]
    assert ("test-bucket", "form990/normalized/manifests/teos-zip/state/latest/year=2024/source_batch=2024_TEOS_XML_01A.json") in fake_s3.store
    assert ("test-bucket", "form990/normalized/manifests/teos-zip/runs/run1/year=2024/catalog.json") in fake_s3.store


def test_discovery_mode_skips_unchanged_teos_zip_on_rerun(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    module.parse_teos_zip_links = lambda html, page_url, target_year, now=None: [
        TeosZipDiscoveryRecord(
            tax_year=str(target_year),
            source_url=f"https://apps.irs.gov/pub/epostcard/990/xml/{target_year}/{target_year}_TEOS_XML_01A.zip",
            source_filename=f"{target_year}_TEOS_XML_01A.zip",
            zip_basename=f"{target_year}_TEOS_XML_01A",
            discovered_at="2026-01-01T00:00:00+00:00",
            page_url=page_url,
        )
    ]
    module.probe_teos_zip_metadata = lambda source_url, timeout_seconds=60, now=None, max_attempts=3, opener=None: module.TeosZipProbeResult(
        source_url=source_url,
        resolved_source_url=source_url,
        etag='"etag-1"',
        last_modified="Thu, 20 Mar 2026 00:00:00 GMT",
        content_length=1234,
        checked_at="2026-01-01T00:00:00+00:00",
        method_used="HEAD",
    )
    calls = {"count": 0}

    def _download_batch(**kwargs):
        calls["count"] += 1
        downloads = []
        for source in kwargs["sources"]:
            state_key = (
                module.source_download_state_prefix(module.MANIFEST_PREFIX)
                + f"/{source['source_year']}/{source['source_kind']}/{source['source_archive_key']}.json"
            )
            payload = {
                **source,
                "status": "downloaded",
                "raw_source_s3_key": f"form990/raw-sources/{source['source_year']}/{source['source_kind']}/{source['source_archive_key']}/{source['source_signature']}/{source['source_filename']}",
                "downloaded_at": "2026-01-01T00:00:00+00:00",
                "content_length": 1234,
                "content_type": "application/zip",
            }
            fake_s3.put_object(Bucket="test-bucket", Key=state_key, Body=json.dumps(payload).encode("utf-8"))
            downloads.append(payload)
        return {"manifest_key": None, "downloaded_count": len(downloads), "downloads": downloads}

    module.execute_source_download_batch = _download_batch
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "records": [],
    }

    first_result = module.handler(
        {
            "run_id": "run1",
            "mode": "incremental",
            "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}],
        },
        None,
    )
    second_result = module.handler(
        {
            "run_id": "run2",
            "mode": "incremental",
            "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}],
        },
        None,
    )

    first_body = _response_data(first_result)
    second_body = _response_data(second_result)

    assert first_result["statusCode"] == 200
    assert second_result["statusCode"] == 200
    assert calls["count"] == 1
    assert first_body["scheduled_source_count"] == 1
    assert second_body["scheduled_source_count"] == 0
    assert second_body["skipped_source_count"] == 1
    assert second_body["teos_zip_manifest"]["skipped_download_count"] == 1


def test_static_manifest_is_default_discovery_mode(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: [
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
        _source(source_year="2024", source_kind="zip_archive", source_url="https://example.org/2024_TEOS_XML_11B.zip", source_archive_key="2024_teos_xml_11b"),
    ]
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "records": [],
    }

    result = module.handler({"mode": "incremental"}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["source_mode"] == "static_manifest"
    assert body["source_catalog_count"] == 2
    assert body["scheduled_source_count"] == 2


def test_static_manifest_generation_toggle_is_passed_to_discovery(monkeypatch):
    monkeypatch.setenv("FORM990_ENABLE_NEXT_YEAR_GENERATION", "false")
    module, _ = _load_module(monkeypatch)
    captured = {}

    def _discover(now=None, enable_next_year_generation=True):
        captured["enable_next_year_generation"] = enable_next_year_generation
        return [_source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024")]

    module.discover_static_form990_sources = _discover
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "records": [],
    }

    result = module.handler({"mode": "incremental"}, None)

    assert result["statusCode"] == 200
    assert captured["enable_next_year_generation"] is False


def test_static_manifest_missing_returns_clear_operational_error(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: (_ for _ in ()).throw(FileNotFoundError("missing manifest"))

    result = module.handler({"mode": "incremental"}, None)

    assert result["statusCode"] == 500
    assert "Form 990 static manifest is missing" in _response_error_message(result)


def test_static_manifest_malformed_returns_clear_operational_error(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: (_ for _ in ()).throw(
        ValueError("Form 990 static manifest did not contain any parseable CSV or ZIP source URLs")
    )

    result = module.handler({"mode": "incremental"}, None)

    assert result["statusCode"] == 500
    assert "Form 990 static manifest is malformed" in _response_error_message(result)


def test_discovery_mode_reports_unchanged_state(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    state_key = module.discovery_state_key(module.MANIFEST_PREFIX)
    existing = normalize_configured_sources([{"year": "2024", "index_url": "https://example.org/index_2024.csv"}])[0].to_dict()
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {"status": "success", "records_processed": 0, "parsed_count": 0, "failed_count": 0, "records": []}
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=state_key,
        Body=json.dumps({"sources": [existing]}).encode("utf-8"),
    )

    result = module.handler({"mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["new_sources"] == 0
    assert body["changed_sources"] == 0
    assert body["removed_sources"] == 0
    assert body["unchanged_sources"] == 1


def test_static_manifest_mode_reports_unchanged_state(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    state_key = module.discovery_state_key(module.MANIFEST_PREFIX)
    existing = _source(
        source_year="2024",
        source_kind="csv_index",
        source_url="https://example.org/index_2024.csv",
        source_archive_key="index_2024",
    ).to_dict()
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=state_key,
        Body=json.dumps({"sources": [existing]}).encode("utf-8"),
    )
    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: [
        Form990SourceArtifact(
            source_year="2024",
            source_kind="csv_index",
            source_url="https://example.org/index_2024.csv",
            source_filename="index_2024.csv",
            source_archive_key="index_2024",
            discovered_at="2026-01-01T00:00:00+00:00",
            source_signature=existing["source_signature"],
            page_url=existing["page_url"],
        )
    ]
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "records": [],
    }

    result = module.handler({"mode": "incremental"}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["source_mode"] == "static_manifest"
    assert body["new_sources"] == 0
    assert body["changed_sources"] == 0
    assert body["removed_sources"] == 0
    assert body["unchanged_sources"] == 1


def test_discovery_mode_skips_download_when_state_matches(monkeypatch):
    module, fake_s3 = _load_module(monkeypatch)
    existing = normalize_configured_sources([{"year": "2024", "index_url": "https://example.org/index_2024.csv"}])[0].to_dict()
    download_state_key = module.source_download_state_prefix(module.MANIFEST_PREFIX) + "/2024/csv_index/index_2024.json"
    fake_s3.put_object(
        Bucket="test-bucket",
        Key=download_state_key,
        Body=json.dumps(
            {
                "source_year": "2024",
                "source_kind": "csv_index",
                "source_url": existing["source_url"],
                "source_filename": existing["source_filename"],
                "source_archive_key": existing["source_archive_key"],
                "source_signature": existing["source_signature"],
                "raw_source_s3_key": "form990/raw-sources/2024/csv_index/index_2024/sig/index_2024.csv",
                "downloaded_at": "2026-01-01T00:00:00+00:00",
            }
        ).encode("utf-8"),
    )
    called = {"value": False}

    def _unexpected(**kwargs):
        called["value"] = True
        return {"manifest_key": "k", "downloaded_count": 0, "downloads": []}

    module.execute_source_download_batch = _unexpected
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {"status": "success", "records_processed": 0, "parsed_count": 0, "failed_count": 0, "records": []}
    result = module.handler({"run_id": "run1", "mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert called["value"] is False
    assert body["scheduled_source_count"] == 0
    assert body["skipped_source_count"] == 1
    assert body["downloaded_source_count"] == 0


def test_manual_source_catalog_preserves_configured_flow(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: (_ for _ in ()).throw(AssertionError("static discovery should not run for manual catalogs"))
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": 0,
        "parsed_count": 0,
        "failed_count": 0,
        "records": [],
    }

    result = module.handler({"mode": "incremental", "source_catalog": [{"year": "2024", "index_url": "https://example.org/index_2024.csv"}]}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["source_mode"] == "configured"
    assert body["source_catalog_count"] == 1


def test_lambda_form990_rejects_invalid_request_source_mode(monkeypatch):
    module, _ = _load_module(monkeypatch)

    result = module.handler({"mode": "incremental", "source_mode": "unsupported"}, None)

    assert result["statusCode"] == 400
    assert "source_mode must be one of configured, static_manifest, or irs_page" in _response_error_message(result)


def test_policy_config_override_target_years(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult()
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {"status": "success", "records_processed": 0, "parsed_count": 0, "failed_count": 0, "records": []}
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
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["policy"]["target_years"] == ["2023"]
    assert body["selected_source_count"] == 1


def test_irs_page_source_mode_discovers_source_artifacts(monkeypatch):
    module, _ = _load_module(monkeypatch)
    module.discover_irs_form990_sources = lambda page_url, timeout_seconds=60, now=None: [
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
        _source(source_year="2024", source_kind="zip_archive", source_url="https://example.org/2024_TEOS_XML_11B.zip", source_archive_key="2024_teos_xml_11b"),
    ]
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult(
        current_records=[],
        selected_records=[],
    )
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {"status": "success", "records_processed": 0, "parsed_count": 0, "failed_count": 0, "records": []}

    result = module.handler({"mode": "incremental", "source_mode": "irs_page"}, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["source_mode"] == "irs_page"
    assert body["source_catalog_count"] == 2
    assert body["scheduled_source_count"] == 2
    assert body["downloaded_source_count"] == 2


def test_orchestrated_mode_enqueues_source_chunks(monkeypatch):
    fake_s3 = FakeS3()
    fake_sqs = FakeSQS()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_EXECUTION_MODE", "orchestrated")
    monkeypatch.setenv("FORM990_WORK_QUEUE_URL", "https://sqs.example/work")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3 if name == "s3" else fake_sqs)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    module.discover_irs_form990_sources = lambda page_url, timeout_seconds=60, now=None: [
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
        _source(source_year="2024", source_kind="zip_archive", source_url="https://example.org/2024_TEOS_XML_11B.zip", source_archive_key="2024_teos_xml_11b"),
    ]
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult(
        current_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2024",
                filing_date="2025-01-01",
                return_type="990",
                irs_object_id="obj-1",
                xml_url="https://example.org/obj-1.xml",
                source_year="2024",
                source_archive="index_2024",
                source_signature="sig-1",
            )
        ],
        selected_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2024",
                filing_date="2025-01-01",
                return_type="990",
                irs_object_id="obj-1",
                xml_url="https://example.org/obj-1.xml",
                source_year="2024",
                source_archive="index_2024",
                source_signature="sig-1",
            )
        ],
        new_count=1,
    )
    result = module.handler({"mode": "bootstrap", "chunk_size": 1, "source_mode": "irs_page"}, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["execution_mode"] == "orchestrated"
    assert body["stage"] == "zip_extraction"
    assert body["chunk_count"] == 1
    assert len(fake_sqs.messages) == 1
    payload = json.loads(fake_sqs.messages[0]["MessageBody"])
    chunk_body = json.loads(fake_s3.store[("test-bucket", payload["chunk_s3_key"])]["Body"].decode("utf-8"))
    assert chunk_body["task_type"] == "filing_records"
    assert chunk_body["records"][0]["irs_object_id"] == "obj-1"
    assert "zip_sources" not in chunk_body


def test_orchestrated_mode_applies_target_year_policy_before_chunking(monkeypatch):
    fake_s3 = FakeS3()
    fake_sqs = FakeSQS()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_EXECUTION_MODE", "orchestrated")
    monkeypatch.setenv("FORM990_WORK_QUEUE_URL", "https://sqs.example/work")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3 if name == "s3" else fake_sqs)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    module.discover_irs_form990_sources = lambda page_url, timeout_seconds=60, now=None: [
        _source(source_year="2023", source_kind="csv_index", source_url="https://example.org/index_2023.csv", source_archive_key="index_2023"),
        _source(source_year="2024", source_kind="csv_index", source_url="https://example.org/index_2024.csv", source_archive_key="index_2024"),
    ]
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": len(kwargs["sources"]),
        "downloads": list(kwargs["sources"]),
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult(
        current_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2023",
                filing_date="2024-01-01",
                return_type="990",
                irs_object_id="obj-2023",
                xml_url="https://example.org/obj-2023.xml",
                source_year="2023",
                source_archive="index_2023",
                source_signature="sig-2023",
            )
        ],
        selected_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2023",
                filing_date="2024-01-01",
                return_type="990",
                irs_object_id="obj-2023",
                xml_url="https://example.org/obj-2023.xml",
                source_year="2023",
                source_archive="index_2023",
                source_signature="sig-2023",
            )
        ],
        new_count=1,
    )
    result = module.handler({"mode": "incremental", "target_years": ["2023"], "chunk_size": 10, "source_mode": "irs_page"}, None)
    body = _response_data(result)
    assert result["statusCode"] == 200
    assert body["selected_source_count"] == 1
    assert body["chunk_count"] == 1
    assert len(fake_sqs.messages) == 1


def test_orchestrated_mode_continues_when_generated_sources_are_skipped(monkeypatch):
    fake_s3 = FakeS3()
    fake_sqs = FakeSQS()
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("FORM990_EXECUTION_MODE", "orchestrated")
    monkeypatch.setenv("FORM990_WORK_QUEUE_URL", "https://sqs.example/work")
    monkeypatch.setattr("boto3.client", lambda name: fake_s3 if name == "s3" else fake_sqs)
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: [
        Form990SourceArtifact(
            source_year="2026",
            source_kind="csv_index",
            source_url="https://example.org/index_2026.csv",
            source_filename="index_2026.csv",
            source_archive_key="index_2026",
            discovered_at="2026-01-01T00:00:00+00:00",
            source_signature="sig-index_2026",
            page_url="generated://form990-next-year/2025-to-2026",
        ),
        Form990SourceArtifact(
            source_year="2026",
            source_kind="zip_archive",
            source_url="https://example.org/2026_TEOS_XML_03A.zip",
            source_filename="2026_TEOS_XML_03A.zip",
            source_archive_key="2026_teos_xml_03a",
            discovered_at="2026-01-01T00:00:00+00:00",
            source_signature="sig-2026-teos-03a",
            page_url="generated://form990-next-year/2025-to-2026",
        ),
    ]
    module.execute_source_download_batch = lambda **kwargs: {
        "manifest_key": "form990/normalized/manifests/source-download/runs/run1/batch_00000.json",
        "downloaded_count": 1,
        "skipped_unavailable_count": 1,
        "downloads": [
            {
                **kwargs["sources"][0],
                "status": "downloaded",
                "raw_source_s3_key": "form990/raw-sources/2026/csv_index/index_2026/sig/index_2026.csv",
            },
            {
                **kwargs["sources"][1],
                "status": "skipped_unavailable",
                "reason": "generated_source_unavailable",
                "raw_source_s3_key": None,
            },
        ],
    }
    module.reconcile_filing_catalog = lambda **kwargs: _ReconciliationResult(
        current_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2026",
                filing_date="2026-01-01",
                return_type="990",
                irs_object_id="obj-2026",
                xml_url="https://example.org/obj-2026.xml",
                source_year="2026",
                source_archive="index_2026",
                source_signature="sig-2026",
            )
        ],
        selected_records=[
            Form990IndexRecord(
                ein="123456789",
                tax_year="2026",
                filing_date="2026-01-01",
                return_type="990",
                irs_object_id="obj-2026",
                xml_url="https://example.org/obj-2026.xml",
                source_year="2026",
                source_archive="index_2026",
                source_signature="sig-2026",
            )
        ],
        new_count=1,
    )

    result = module.handler({"mode": "incremental"}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert body["execution_mode"] == "orchestrated"
    assert body["downloaded_source_count"] == 1
    assert body["chunk_count"] == 1
    assert len(fake_sqs.messages) == 1


def test_legacy_index_url_path_bypasses_static_manifest(monkeypatch):
    module, _ = _load_module(monkeypatch)
    called = {"fetch": 0}
    module.discover_static_form990_sources = lambda now=None, enable_next_year_generation=True: (_ for _ in ()).throw(AssertionError("static discovery should not run for legacy direct ingest"))
    module.fetch_index_records = lambda index_url, source_year, source_archive, timeout_seconds=60: [
        called.__setitem__("fetch", called["fetch"] + 1) or
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
    module.Form990IngestService.ingest_index_payload = lambda self, payload, download_raw=True, record_downloader=None: {
        "status": "success",
        "records_processed": len(payload),
        "parsed_count": len(payload),
        "failed_count": 0,
        "records": [{"ein": item["ein"], "parse_status": "index_only"} for item in payload],
    }

    result = module.handler({"index_url": "https://example.org/index.json", "download_raw": False}, None)
    body = _response_data(result)

    assert result["statusCode"] == 200
    assert called["fetch"] == 1
    assert body["records_processed"] == 1
