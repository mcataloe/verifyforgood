import pathlib

from infrastructure.charity_status.form990.index import parse_index_records
from infrastructure.charity_status.form990.ingest import ingest_form990_records


class FakeS3:
    def __init__(self):
        self.objects = []

    def put_object(self, Bucket, Key, Body):
        self.objects.append({"Bucket": Bucket, "Key": Key, "Body": Body})


def test_ingest_manifest_and_result_success():
    records = parse_index_records([
        {
            "ein": "123456789",
            "tax_year": "2023",
            "filing_date": "2024-05-15",
            "return_type": "990",
            "irs_object_id": "obj-1",
            "xml_url": "https://example.org/obj-1.xml",
        }
    ])
    s3 = FakeS3()
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()

    result = ingest_form990_records(
        records=records,
        bucket="test-bucket",
        raw_prefix="form990/raw/",
        metadata_prefix="form990/normalized/metadata/",
        manifest_prefix="form990/normalized/manifests/",
        metrics_prefix="form990/normalized/metrics/",
        governance_prefix="form990/normalized/governance/",
        quality_prefix="form990/normalized/quality/",
        s3_client=s3,
        download_raw=True,
        downloader=lambda url: xml_content,
    )

    assert result.status == "success"
    assert result.records_processed == 1
    assert result.parsed_count == 1
    assert result.failed_count == 0
    assert any(item["Key"].startswith("form990/raw/") for item in s3.objects)
    assert any(item["Key"].startswith("form990/normalized/metadata/filings_") for item in s3.objects)
    assert any(item["Key"].startswith("form990/normalized/metrics/metrics_") for item in s3.objects)
    assert any(item["Key"].startswith("form990/normalized/governance/governance_") for item in s3.objects)
    assert any(item["Key"].startswith("form990/normalized/quality/quality_") for item in s3.objects)
    assert any(item["Key"].startswith("form990/normalized/manifests/") for item in s3.objects)


def test_ingest_malformed_xml_fallback():
    records = parse_index_records([
        {
            "ein": "123456789",
            "tax_year": "2023",
            "filing_date": "2024-05-15",
            "return_type": "990",
            "irs_object_id": "obj-2",
            "xml_url": "https://example.org/obj-2.xml",
        }
    ])
    s3 = FakeS3()

    result = ingest_form990_records(
        records=records,
        bucket="test-bucket",
        raw_prefix="form990/raw/",
        metadata_prefix="form990/normalized/metadata/",
        manifest_prefix="form990/normalized/manifests/",
        metrics_prefix="form990/normalized/metrics/",
        governance_prefix="form990/normalized/governance/",
        quality_prefix="form990/normalized/quality/",
        s3_client=s3,
        download_raw=True,
        downloader=lambda url: b"<Return><bad></Return>",
    )

    assert result.status == "failed"
    assert result.failed_count == 1
    assert result.records[0]["parse_status"] == "malformed_xml"


def test_ingest_unsupported_return_type_keeps_index_only():
    records = parse_index_records([
        {
            "ein": "123456789",
            "tax_year": "2023",
            "filing_date": "2024-05-15",
            "return_type": "990EZ",
            "irs_object_id": "obj-3",
            "xml_url": "https://example.org/obj-3.xml",
        }
    ])
    s3 = FakeS3()

    result = ingest_form990_records(
        records=records,
        bucket="test-bucket",
        raw_prefix="form990/raw/",
        metadata_prefix="form990/normalized/metadata/",
        manifest_prefix="form990/normalized/manifests/",
        metrics_prefix="form990/normalized/metrics/",
        governance_prefix="form990/normalized/governance/",
        quality_prefix="form990/normalized/quality/",
        s3_client=s3,
        download_raw=True,
        downloader=lambda url: b"",
    )

    assert result.records[0]["parse_status"] == "unsupported_return_type"
    assert result.parsed_count == 0
