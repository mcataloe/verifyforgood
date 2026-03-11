from __future__ import annotations

import json
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import boto3

from charity_status.form990.extractors import extract_metadata_fields
from charity_status.form990.index import parse_index_records
from charity_status.form990.models import (
    Form990IndexRecord,
    Form990IngestResult,
    Form990MetadataRecord,
    Form990ParseStatus,
)
from charity_status.form990.parser import XmlParseError, parse_xml
from charity_status.form990.storage import manifest_key, normalized_metadata_key, raw_xml_key, to_jsonl

SUPPORTED_RETURN_TYPES = {"990", "FORM_990", "990O"}


class Form990IngestService:
    def __init__(self, bucket: str, raw_prefix: str, metadata_prefix: str, manifest_prefix: str, s3_client: Any | None = None):
        self.bucket = bucket
        self.raw_prefix = raw_prefix
        self.metadata_prefix = metadata_prefix
        self.manifest_prefix = manifest_prefix
        self.s3 = s3_client or boto3.client("s3")

    def ingest_index_payload(self, payload: list[dict[str, Any]], download_raw: bool = False) -> dict[str, Any]:
        records = parse_index_records(payload)
        result = ingest_form990_records(
            records=records,
            bucket=self.bucket,
            raw_prefix=self.raw_prefix,
            metadata_prefix=self.metadata_prefix,
            manifest_prefix=self.manifest_prefix,
            s3_client=self.s3,
            download_raw=download_raw,
        )
        return result.to_dict()


def ingest_form990_records(
    records: list[Form990IndexRecord],
    bucket: str,
    raw_prefix: str,
    metadata_prefix: str,
    manifest_prefix: str,
    s3_client: Any,
    download_raw: bool = False,
    downloader: Any | None = None,
) -> Form990IngestResult:
    started = datetime.now(timezone.utc)
    downloader = downloader or _download_raw_xml

    metadata_records: list[Form990MetadataRecord] = []
    for record in records:
        metadata = _from_index_record(record)

        if not _is_supported_return_type(record.return_type):
            metadata_records.append(replace(metadata, parse_status=Form990ParseStatus.UNSUPPORTED_RETURN_TYPE))
            continue

        if not download_raw or not record.xml_url:
            metadata_records.append(metadata)
            continue

        try:
            xml_bytes = downloader(record.xml_url)
            raw_key = raw_xml_key(raw_prefix, metadata.ein, metadata.tax_year, metadata.irs_object_id)
            s3_client.put_object(Bucket=bucket, Key=raw_key, Body=xml_bytes)

            extracted = extract_metadata_fields(parse_xml(xml_bytes))
            metadata_records.append(
                Form990MetadataRecord(
                    ein=extracted.get("ein") or metadata.ein,
                    tax_year=extracted.get("tax_year") or metadata.tax_year,
                    tax_period_begin=extracted.get("tax_period_begin"),
                    tax_period_end=extracted.get("tax_period_end"),
                    filing_date=extracted.get("filing_date") or metadata.filing_date,
                    amended_return=extracted.get("amended_return"),
                    return_type=extracted.get("return_type") or metadata.return_type,
                    irs_object_id=metadata.irs_object_id,
                    xml_source_reference=metadata.xml_source_reference,
                    raw_s3_key=raw_key,
                    parse_status=Form990ParseStatus.PARSED,
                )
            )
        except XmlParseError as exc:
            metadata_records.append(
                replace(
                    metadata,
                    parse_status=Form990ParseStatus.MALFORMED_XML,
                    parse_error=str(exc),
                )
            )
        except Exception as exc:
            metadata_records.append(
                replace(
                    metadata,
                    parse_status=Form990ParseStatus.PARSE_ERROR,
                    parse_error=str(exc),
                )
            )

    metadata_payload = [item.to_dict() for item in metadata_records]
    metadata_key = normalized_metadata_key(metadata_prefix, now=started)
    s3_client.put_object(Bucket=bucket, Key=metadata_key, Body=to_jsonl(metadata_payload))

    parsed_count = sum(1 for item in metadata_records if item.parse_status == Form990ParseStatus.PARSED)
    failed_count = sum(
        1
        for item in metadata_records
        if item.parse_status in {Form990ParseStatus.MALFORMED_XML, Form990ParseStatus.PARSE_ERROR}
    )
    status = "success" if failed_count == 0 else ("partial_success" if parsed_count > 0 else "failed")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_processed": len(metadata_records),
        "parsed_count": parsed_count,
        "failed_count": failed_count,
        "status": status,
        "metadata_s3_key": metadata_key,
    }
    manifest_s3 = manifest_key(manifest_prefix, now=started)
    s3_client.put_object(Bucket=bucket, Key=manifest_s3, Body=json.dumps(manifest, sort_keys=True).encode("utf-8"))

    return Form990IngestResult(
        status=status,
        records_processed=len(metadata_records),
        parsed_count=parsed_count,
        failed_count=failed_count,
        manifest_s3_key=manifest_s3,
        metadata_s3_key=metadata_key,
        records=metadata_payload,
    )


def _from_index_record(record: Form990IndexRecord) -> Form990MetadataRecord:
    return Form990MetadataRecord(
        ein=record.ein,
        tax_year=record.tax_year,
        tax_period_begin=None,
        tax_period_end=None,
        filing_date=record.filing_date,
        amended_return=None,
        return_type=record.return_type,
        irs_object_id=record.irs_object_id,
        xml_source_reference=record.xml_url,
        raw_s3_key=None,
        parse_status=Form990ParseStatus.INDEX_ONLY,
    )


def _is_supported_return_type(return_type: str | None) -> bool:
    if not return_type:
        return False
    normalized = return_type.upper().replace("-", "_")
    return normalized in SUPPORTED_RETURN_TYPES


def _download_raw_xml(url: str) -> bytes:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status >= 400:
            raise RuntimeError(f"download failed with status {response.status}")
        return response.read()
