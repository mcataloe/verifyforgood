import pathlib

from infrastructure.verification.backend.ingest.federal.form990.index import parse_index_records
from infrastructure.verification.backend.ingest.federal.form990.ingest import ingest_form990_records


class RecordingProgressSession:
    def __init__(self):
        self.calls = []
        self.completed = False

    def item_completed(self, increments=None, *, last_item=None):
        self.calls.append(dict(increments or {}))

    def complete(self):
        self.completed = True


def test_ingest_result_success_without_s3_artifacts():
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
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()

    result = ingest_form990_records(
        records=records,
        download_raw=True,
        downloader=lambda url: xml_content,
    )

    assert result.status == "success"
    assert result.records_processed == 1
    assert result.parsed_count == 1
    assert result.failed_count == 0
    assert result.records[0]["xml_source_reference"] == "https://example.org/obj-1.xml"
    assert result.artifact_paths is None


def test_parse_form990_record_xml_emits_canonical_raw_filing_metadata():
    from infrastructure.verification.backend.ingest.federal.form990.ingest import parse_form990_record_xml
    from infrastructure.verification.backend.ingest.federal.form990.models import Form990IndexRecord

    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    parsed = parse_form990_record_xml(
        Form990IndexRecord(
            ein="123456789",
            tax_year="2023",
            filing_date="2024-05-15",
            return_type="990",
            irs_object_id="obj-1",
            xml_url="https://example.org/obj-1.xml",
            source_signature="sig-obj-1",
        ),
        xml_bytes=xml_content,
        source_reference="https://example.org/obj-1.xml",
    )

    assert parsed.canonical_raw_filing_record is not None
    assert parsed.canonical_raw_filing_record["source_record_id"] == "obj-1"
    assert parsed.canonical_raw_filing_record["source_signature"] == "sig-obj-1"
    assert parsed.canonical_raw_filing_record["xml_artifact_reference"] == "https://example.org/obj-1.xml"
    assert parsed.canonical_raw_filing_record["raw_filing_json"]["Return"]["ReturnData"]["IRS990"]["TotalRevenueAmt"] == "1000000"


def test_ingest_preserves_record_source_reference_when_source_archive_present():
    records = parse_index_records(
        [
            {
                "ein": "123456789",
                "tax_year": "2025",
                "filing_date": "2026-01-15",
                "return_type": "990",
                "irs_object_id": "obj-batch-1",
                "xml_url": "https://example.org/obj-batch-1.xml",
                "source_archive": "2025_TEOS_XML_01A",
            }
        ]
    )
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()

    result = ingest_form990_records(
        records=records,
        download_raw=True,
        downloader=lambda url: xml_content,
    )

    assert result.records[0]["xml_source_reference"] == "https://example.org/obj-batch-1.xml"
    assert result.records[0]["raw_file_reference"] == "https://example.org/obj-batch-1.xml"


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
    result = ingest_form990_records(
        records=records,
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
    result = ingest_form990_records(
        records=records,
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
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    result = ingest_form990_records(
        records=records,
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
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    result = ingest_form990_records(
        records=records,
        download_raw=True,
        record_downloader=lambda record: (
            xml_content,
            "workspace://form990/raw-sources/2024/zip_archive/a/2024_TEOS_XML_01A.zip#obj-zip-1.xml",
        ),
    )
    assert result.parsed_count == 1
    assert result.records[0]["xml_source_reference"].startswith("workspace://form990/raw-sources/")


def test_ingest_updates_progress_session_and_preserves_result_shape():
    records = parse_index_records(
        [
            {
                "ein": "123456789",
                "tax_year": "2024",
                "filing_date": "2025-01-01",
                "return_type": "990",
                "irs_object_id": "obj-ok",
                "xml_url": "https://example.org/obj-ok.xml",
            },
            {
                "ein": "123456789",
                "tax_year": "2024",
                "filing_date": "2025-01-02",
                "return_type": "990",
                "irs_object_id": "obj-bad",
                "xml_url": "https://example.org/obj-bad.xml",
            },
        ]
    )
    xml_content = pathlib.Path("tests/fixtures/form990/form990_sample.xml").read_bytes()
    progress_session = RecordingProgressSession()

    result = ingest_form990_records(
        records=records,
        download_raw=True,
        record_downloader=lambda record: xml_content if record.irs_object_id == "obj-ok" else b"<Return><bad></Return>",
        progress_session=progress_session,
    )

    assert result.status == "partial_success"
    assert result.records_processed == 2
    assert result.parsed_count == 1
    assert result.failed_count == 1
    assert progress_session.calls == [{"parsed": 1}, {"failed": 1}]
    assert progress_session.completed is True

