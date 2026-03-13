from __future__ import annotations

import json
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

import boto3

from charity_status.form990.extractors import (
    extract_financial_fields,
    extract_governance_fields,
    extract_metadata_fields,
    extract_narrative_fields,
)
from charity_status.form990.index import parse_index_records
from charity_status.form990.metrics import compute_derived_metrics
from charity_status.form990.models import (
    Form990IndexRecord,
    Form990IngestResult,
    Form990MetadataRecord,
    Form990ParseStatus,
)
from charity_status.form990.parser import XmlParseError, parse_xml
from charity_status.form990.quality import compute_filing_quality
from charity_status.form990.relationships import extract_relationship_edges
from charity_status.form990.storage import manifest_key, normalized_dataset_key, raw_xml_key, to_jsonl

SUPPORTED_RETURN_TYPES = {"990", "FORM_990", "990O", "990EZ", "990PF", "990T"}


class Form990IngestService:
    def __init__(
        self,
        bucket: str,
        raw_prefix: str,
        metadata_prefix: str,
        manifest_prefix: str,
        metrics_prefix: str,
        governance_prefix: str,
        quality_prefix: str,
        relationships_prefix: str = "form990/normalized/relationships/",
        s3_client: Any | None = None,
    ):
        self.bucket = bucket
        self.raw_prefix = raw_prefix
        self.metadata_prefix = metadata_prefix
        self.manifest_prefix = manifest_prefix
        self.metrics_prefix = metrics_prefix
        self.governance_prefix = governance_prefix
        self.quality_prefix = quality_prefix
        self.relationships_prefix = relationships_prefix
        self.s3 = s3_client or boto3.client("s3")

    def ingest_index_payload(self, payload: list[dict[str, Any]], download_raw: bool = False) -> dict[str, Any]:
        records = parse_index_records(payload)
        result = ingest_form990_records(
            records=records,
            bucket=self.bucket,
            raw_prefix=self.raw_prefix,
            metadata_prefix=self.metadata_prefix,
            manifest_prefix=self.manifest_prefix,
            metrics_prefix=self.metrics_prefix,
            governance_prefix=self.governance_prefix,
            quality_prefix=self.quality_prefix,
            relationships_prefix=self.relationships_prefix,
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
    metrics_prefix: str,
    governance_prefix: str,
    quality_prefix: str,
    relationships_prefix: str,
    s3_client: Any,
    download_raw: bool = False,
    downloader: Any | None = None,
) -> Form990IngestResult:
    started = datetime.now(timezone.utc)
    downloader = downloader or _download_raw_xml

    filing_records: list[dict[str, Any]] = []
    metrics_records: list[dict[str, Any]] = []
    governance_records: list[dict[str, Any]] = []
    quality_records: list[dict[str, Any]] = []
    relationship_records: list[dict[str, Any]] = []

    grouped_filings: dict[str, list[dict[str, Any]]] = {}

    for record in records:
        metadata = _from_index_record(record)

        if not _is_supported_return_type(record.return_type):
            filing = replace(metadata, parse_status=Form990ParseStatus.UNSUPPORTED_RETURN_TYPE).to_dict()
            filing_records.append(filing)
            continue

        if not download_raw or not record.xml_url:
            filing = metadata.to_dict()
            filing_records.append(filing)
            grouped_filings.setdefault(metadata.ein or "unknown", []).append(filing)
            continue

        try:
            xml_bytes = downloader(record.xml_url)
            raw_key = raw_xml_key(raw_prefix, metadata.ein, metadata.tax_year, metadata.irs_object_id)
            s3_client.put_object(Bucket=bucket, Key=raw_key, Body=xml_bytes)

            parsed = parse_xml(xml_bytes)
            extracted_meta = extract_metadata_fields(parsed)
            extracted_financials = extract_financial_fields(parsed)
            extracted_governance = extract_governance_fields(parsed)
            extracted_narratives = extract_narrative_fields(parsed)

            merged_filing = {
                **Form990MetadataRecord(
                    ein=extracted_meta.get("ein") or metadata.ein,
                    tax_year=extracted_meta.get("tax_year") or metadata.tax_year,
                    tax_period_begin=extracted_meta.get("tax_period_begin"),
                    tax_period_end=extracted_meta.get("tax_period_end"),
                    filing_date=extracted_meta.get("filing_date") or metadata.filing_date,
                    amended_return=extracted_meta.get("amended_return"),
                    return_type=extracted_meta.get("return_type") or metadata.return_type,
                    irs_object_id=metadata.irs_object_id,
                    xml_source_reference=metadata.xml_source_reference,
                    raw_s3_key=raw_key,
                    parse_status=Form990ParseStatus.PARSED,
                ).to_dict(),
                **extracted_financials,
                **extracted_governance,
                **extracted_narratives,
            }
            filing_records.append(merged_filing)
            grouped_filings.setdefault(merged_filing.get("ein") or "unknown", []).append(merged_filing)
            relationship_records.extend(extract_relationship_edges(parsed, merged_filing))

        except XmlParseError as exc:
            filing_records.append(
                replace(
                    metadata,
                    parse_status=Form990ParseStatus.MALFORMED_XML,
                    parse_error=str(exc),
                ).to_dict()
            )
        except Exception as exc:
            filing_records.append(
                replace(
                    metadata,
                    parse_status=Form990ParseStatus.PARSE_ERROR,
                    parse_error=str(exc),
                ).to_dict()
            )

    for ein, filings in grouped_filings.items():
        sorted_filings = sorted(filings, key=lambda item: item.get("tax_year") or "")
        for idx, filing in enumerate(sorted_filings):
            history = sorted_filings[:idx]
            metrics = compute_derived_metrics(filing, history=history)
            quality = compute_filing_quality(filing, history=history)

            metrics_record = {
                "ein": filing.get("ein"),
                "tax_year": filing.get("tax_year"),
                **metrics,
            }
            governance_record = {
                "ein": filing.get("ein"),
                "tax_year": filing.get("tax_year"),
                "independent_board_majority": filing.get("independent_board_majority"),
                "conflict_of_interest_policy": filing.get("conflict_of_interest_policy"),
                "whistleblower_policy": filing.get("whistleblower_policy"),
                "records_retention_policy": filing.get("records_retention_policy"),
                "contemporaneous_board_minutes": filing.get("contemporaneous_board_minutes"),
                "material_diversion_reported": filing.get("material_diversion_reported"),
                "compensation_review_process": filing.get("compensation_review_process"),
                "public_disclosure_available": filing.get("public_disclosure_available"),
                "audited_financials_indicator": filing.get("audited_financials_indicator"),
            }
            quality_record = {
                "ein": filing.get("ein"),
                "tax_year": filing.get("tax_year"),
                **quality,
            }

            metrics_records.append(metrics_record)
            governance_records.append(governance_record)
            quality_records.append(quality_record)

    filing_key = normalized_dataset_key(metadata_prefix, "filings", now=started)
    metrics_key = normalized_dataset_key(metrics_prefix, "metrics", now=started)
    governance_key = normalized_dataset_key(governance_prefix, "governance", now=started)
    quality_key = normalized_dataset_key(quality_prefix, "quality", now=started)
    relationships_key = normalized_dataset_key(relationships_prefix, "relationships", now=started)

    s3_client.put_object(Bucket=bucket, Key=filing_key, Body=to_jsonl(filing_records))
    s3_client.put_object(Bucket=bucket, Key=metrics_key, Body=to_jsonl(metrics_records))
    s3_client.put_object(Bucket=bucket, Key=governance_key, Body=to_jsonl(governance_records))
    s3_client.put_object(Bucket=bucket, Key=quality_key, Body=to_jsonl(quality_records))
    s3_client.put_object(Bucket=bucket, Key=relationships_key, Body=to_jsonl(relationship_records))

    parsed_count = sum(1 for item in filing_records if item.get("parse_status") == Form990ParseStatus.PARSED.value)
    failed_count = sum(
        1
        for item in filing_records
        if item.get("parse_status") in {Form990ParseStatus.MALFORMED_XML.value, Form990ParseStatus.PARSE_ERROR.value}
    )
    status = "success" if failed_count == 0 else ("partial_success" if parsed_count > 0 else "failed")

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records_processed": len(filing_records),
        "parsed_count": parsed_count,
        "failed_count": failed_count,
        "status": status,
        "filing_records_s3_key": filing_key,
        "metrics_s3_key": metrics_key,
        "governance_s3_key": governance_key,
        "quality_s3_key": quality_key,
        "relationships_s3_key": relationships_key,
    }
    manifest_s3 = manifest_key(manifest_prefix, now=started)
    s3_client.put_object(Bucket=bucket, Key=manifest_s3, Body=json.dumps(manifest, sort_keys=True).encode("utf-8"))

    return Form990IngestResult(
        status=status,
        records_processed=len(filing_records),
        parsed_count=parsed_count,
        failed_count=failed_count,
        manifest_s3_key=manifest_s3,
        filing_records_s3_key=filing_key,
        metrics_s3_key=metrics_key,
        governance_s3_key=governance_key,
        quality_s3_key=quality_key,
        relationships_s3_key=relationships_key,
        records=filing_records,
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
