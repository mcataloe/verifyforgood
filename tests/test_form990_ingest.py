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
        relationships_prefix="form990/normalized/relationships/",
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
    assert any(item["Key"].startswith("form990/normalized/relationships/relationships_") for item in s3.objects)
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
        relationships_prefix="form990/normalized/relationships/",
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
            "return_type": "1120",
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
        relationships_prefix="form990/normalized/relationships/",
        s3_client=s3,
        download_raw=True,
        downloader=lambda url: b"",
    )

    assert result.records[0]["parse_status"] == "unsupported_return_type"
    assert result.parsed_count == 0


def test_ingest_supports_990t_return_type():
    records = parse_index_records(
        [
            {
                "ein": "123456789",
                "tax_year": "2023",
                "filing_date": "2024-05-15",
                "return_type": "990T",
                "irs_object_id": "obj-4",
                "xml_url": "https://example.org/obj-4.xml",
            }
        ]
    )
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
        relationships_prefix="form990/normalized/relationships/",
        s3_client=s3,
        download_raw=True,
        downloader=lambda url: xml_content,
    )
    assert result.records[0]["parse_status"] == "parsed"


def test_parse_index_records_supports_irs_style_keys():
    records = parse_index_records(
        [
            {
                "EIN": "530196605",
                "TaxYr": "2023",
                "FilingDt": "2024-05-15",
                "ReturnType": "990",
                "ObjectId": "obj-arc-1",
                "URL": "https://example.org/arc.xml",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].ein == "530196605"
    assert records[0].tax_year == "2023"
    assert records[0].return_type == "990"


def test_parse_index_records_supports_upper_snake_irs_keys():
    records = parse_index_records(
        [
            {
                "EIN": "630809530",
                "TAX_YR": "2024",
                "FILING_DT": "2025-02-14",
                "RETURN_TYPE": "990",
                "OBJECT_ID": "93492348",
                "XML_URL": "https://example.org/93492348_public.xml",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].ein == "630809530"
    assert records[0].tax_year == "2024"
    assert records[0].filing_date == "2025-02-14"
    assert records[0].return_type == "990"
    assert records[0].irs_object_id == "93492348"
    assert records[0].xml_url == "https://example.org/93492348_public.xml"


def test_parse_index_records_defaults_xml_url_from_object_id():
    records = parse_index_records(
        [
            {
                "EIN": "150406405",
                "RETURN_TYPE": "990",
                "OBJECT_ID": "202430239349300918",
            }
        ]
    )
    assert len(records) == 1
    assert records[0].xml_url == "https://apps.irs.gov/pub/epostcard/cor/202430239349300918_public.xml"


def test_ingest_supports_record_downloader_zip_reference():
    records = parse_index_records(
        [
            {
                "ein": "123456789",
                "tax_year": "2024",
                "filing_date": "2025-01-01",
                "return_type": "990",
                "irs_object_id": "obj-zip-1",
                "xml_url": "https://example.org/obj-zip-1.xml",
            }
        ]
    )
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
        relationships_prefix="form990/normalized/relationships/",
        s3_client=s3,
        download_raw=True,
        record_downloader=lambda record: (xml_content, "s3://test-bucket/form990/raw-sources/2024/zip_archive/a#obj-zip-1.xml"),
    )
    assert result.parsed_count == 1
    assert result.records[0]["xml_source_reference"].startswith("s3://test-bucket/form990/raw-sources/")
