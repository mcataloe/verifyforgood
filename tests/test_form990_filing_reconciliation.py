import json

from infrastructure.charity_status.form990.filing_reconciliation import (
    filing_signature,
    filing_record_to_state_entry,
    load_csv_catalog_records,
    reconcile_filing_catalog,
    update_filing_state_from_ingest_result,
)
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


class _Body:
    def __init__(self, value):
        self._value = value

    def read(self):
        if isinstance(self._value, bytes):
            return self._value
        return str(self._value).encode("utf-8")


def test_load_csv_catalog_records_supports_multiple_irs_csv_shapes():
    s3 = FakeS3()
    s3.put_object(
        Bucket="test-bucket",
        Key="raw/index_2024.csv",
        Body=b"EIN,TAX_YR,FILING_DT,RETURN_TYPE,OBJECT_ID,XML_URL\n630809530,2024,2025-02-14,990,93492348,https://example.org/93492348_public.xml\n",
    )
    s3.put_object(
        Bucket="test-bucket",
        Key="raw/index_2025.csv",
        Body=b".EFILE,852780739,202312,2024,MISSION FLIGHT ACADEMY,990EZ,93492348002084,202433489349200208,2024_TEOS_XML_12A\n",
    )
    records = load_csv_catalog_records(
        s3,
        "test-bucket",
        [
            {
                "source_year": "2024",
                "source_kind": "csv_index",
                "source_url": "https://example.org/index_2024.csv",
                "source_archive_key": "index_2024",
                "raw_source_s3_key": "raw/index_2024.csv",
            },
            {
                "source_year": "2025",
                "source_kind": "csv_index",
                "source_url": "https://example.org/index_2025.csv",
                "source_archive_key": "index_2025",
                "raw_source_s3_key": "raw/index_2025.csv",
            },
        ],
    )
    assert len(records) == 2
    assert {item.irs_object_id for item in records} == {"93492348", "202433489349200208"}


def test_reconcile_filing_catalog_selects_new_changed_and_incomplete_and_preserves_uninspected_years():
    s3 = FakeS3()
    csv_key = "form990/raw-sources/2024/csv_index/index_2024/sig/index_2024.csv"
    same_record = Form990IndexRecord(
        ein="111111111",
        tax_year="2024",
        filing_date="2025-01-01",
        return_type="990",
        irs_object_id="obj-same",
        xml_url="https://example.org/obj-same.xml",
        source_year="2024",
        source_archive="index_2024",
    )
    incomplete_record = Form990IndexRecord(
        ein="333333333",
        tax_year="2024",
        filing_date="2025-01-03",
        return_type="990",
        irs_object_id="obj-incomplete",
        xml_url="https://example.org/obj-incomplete.xml",
        source_year="2024",
        source_archive="index_2024",
    )
    s3.put_object(
        Bucket="test-bucket",
        Key=csv_key,
        Body=(
            b"EIN,TaxYr,FilingDt,ReturnType,ObjectId,URL\n"
            b"111111111,2024,2025-01-01,990,obj-same,https://example.org/obj-same.xml\n"
            b"222222222,2024,2025-01-02,990,obj-change,https://example.org/obj-change.xml\n"
            b"333333333,2024,2025-01-03,990,obj-incomplete,https://example.org/obj-incomplete.xml\n"
            b"444444444,2024,2025-01-04,990,obj-new,https://example.org/obj-new.xml\n"
        ),
    )
    previous = [
        {
            **filing_record_to_state_entry(
                same_record
            ),
            "filing_signature": filing_signature(same_record),
            "raw_s3_key": "form990/raw/111111111/2024/obj-same.xml",
            "parse_status": "parsed",
            "completed_at": "2026-01-01T00:00:00+00:00",
            "normalized_complete": True,
            "completion_status": "parsed",
            "manifest_s3_key": "m",
            "filing_records_s3_key": "f",
            "metrics_s3_key": "met",
            "governance_s3_key": "gov",
            "quality_s3_key": "q",
            "relationships_s3_key": "rel",
        },
        {
            **filing_record_to_state_entry(
                Form990IndexRecord(
                    ein="222222222",
                    tax_year="2024",
                    filing_date="2025-01-02",
                    return_type="990",
                    irs_object_id="obj-change",
                    xml_url="https://example.org/old-change.xml",
                    source_year="2024",
                    source_archive="index_2024",
                    source_signature="old-signature",
                )
            ),
            "raw_s3_key": "form990/raw/222222222/2024/obj-change.xml",
            "parse_status": "parsed",
            "completed_at": "2026-01-01T00:00:00+00:00",
            "normalized_complete": True,
            "completion_status": "parsed",
            "manifest_s3_key": "m",
            "filing_records_s3_key": "f",
            "metrics_s3_key": "met",
            "governance_s3_key": "gov",
            "quality_s3_key": "q",
            "relationships_s3_key": "rel",
        },
        {
            **filing_record_to_state_entry(
                incomplete_record
            ),
            "filing_signature": filing_signature(incomplete_record),
            "parse_status": "index_only",
            "normalized_complete": False,
            "completion_status": "incomplete",
        },
        {
            "filing_id": "irs_object_id:obj-2022",
            "filing_signature": "legacy",
            "source_year": "2022",
            "source_archive": "index_2022",
            "normalized_complete": True,
            "parse_status": "parsed",
            "completion_status": "parsed",
            "completed_at": "2025-01-01T00:00:00+00:00",
            "raw_s3_key": "form990/raw/2022/obj-2022.xml",
            "manifest_s3_key": "m",
            "filing_records_s3_key": "f",
            "metrics_s3_key": "met",
            "governance_s3_key": "gov",
            "quality_s3_key": "q",
            "relationships_s3_key": "rel",
        },
    ]
    s3.put_object(
        Bucket="test-bucket",
        Key="form990/normalized/manifests/state/latest_filing_manifest.json",
        Body=json.dumps({"filings": previous}).encode("utf-8"),
    )
    result = reconcile_filing_catalog(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        run_id="run1",
        csv_sources=[
            {
                "source_year": "2024",
                "source_kind": "csv_index",
                "source_url": "https://example.org/index_2024.csv",
                "source_archive_key": "index_2024",
                "raw_source_s3_key": csv_key,
            }
        ],
    )
    assert result.new_count == 1
    assert result.changed_count == 1
    assert result.incomplete_count == 1
    assert result.unchanged_count == 1
    assert {item.irs_object_id for item in result.selected_records} == {"obj-change", "obj-incomplete", "obj-new"}
    latest = json.loads(s3.store[("test-bucket", result.state_key)]["Body"].decode("utf-8"))
    assert any(item.get("source_year") == "2022" for item in latest["filings"])


def test_update_filing_state_from_ingest_result_marks_parsed_complete():
    s3 = FakeS3()
    update_filing_state_from_ingest_result(
        s3_client=s3,
        bucket="test-bucket",
        manifest_prefix="form990/normalized/manifests/",
        input_records=[
            {
                "ein": "123456789",
                "tax_year": "2024",
                "filing_date": "2025-01-10",
                "return_type": "990",
                "irs_object_id": "obj-1",
                "xml_url": "https://example.org/obj-1.xml",
                "source_year": "2024",
                "source_archive": "index_2024",
                "source_signature": "sig-1",
            }
        ],
        ingest_result={
            "manifest_s3_key": "m",
            "filing_records_s3_key": "f",
            "metrics_s3_key": "met",
            "governance_s3_key": "gov",
            "quality_s3_key": "q",
            "relationships_s3_key": "rel",
            "records": [
                {
                    "parse_status": "parsed",
                    "raw_s3_key": "form990/raw/123456789/2024/obj-1.xml",
                }
            ],
        },
    )
    latest = json.loads(s3.store[("test-bucket", "form990/normalized/manifests/state/latest_filing_manifest.json")]["Body"].decode("utf-8"))
    entry = latest["filings"][0]
    assert entry["filing_id"] == "irs_object_id:obj-1"
    assert entry["normalized_complete"] is True
    assert entry["completion_status"] == "parsed"
