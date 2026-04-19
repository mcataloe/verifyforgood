from __future__ import annotations

import logging
import urllib.request
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Callable

from verification.form990.extractors import (
    extract_financial_fields,
    extract_governance_fields,
    extract_metadata_fields,
    extract_narrative_fields,
)
from verification.form990.canonical import (
    CANONICAL_FORM990_CANONICALIZATION_VERSION,
    CANONICAL_FORM990_PARSER_VERSION,
    canonicalize_parsed_xml,
    compute_normalized_xml_content_hash,
)
from verification.form990.index import parse_index_records
from verification.form990.metrics import compute_derived_metrics
from verification.form990.models import (
    Form990CanonicalRawFilingRecord,
    Form990IndexRecord,
    Form990IngestResult,
    Form990MetadataRecord,
    Form990ParseStatus,
)
from verification.form990.parser import XmlParseError, parse_xml
from verification.form990.quality import compute_filing_quality
from verification.form990.relationships import extract_relationship_edges
from verification.ops import ProgressSession
from verification.runtime_logging import configure_runtime_logging, log_structured

SUPPORTED_RETURN_TYPES = {"990", "FORM_990", "990O", "990EZ", "990PF", "990T"}
LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(logger=LOGGER)


class Form990IngestService:
    def __init__(
        self,
        relationships_prefix: str = "form990/normalized/relationships/",
        nonprofit_persistence_service: Any | None = None,
    ):
        self.nonprofit_persistence_service = nonprofit_persistence_service

    def ingest_index_payload(
        self,
        payload: list[dict[str, Any]],
        download_raw: bool = False,
        record_downloader: Any | None = None,
    ) -> dict[str, Any]:
        records = parse_index_records(payload)
        result = ingest_form990_records(
            records=records,
            download_raw=download_raw,
            record_downloader=record_downloader,
            nonprofit_persistence_service=self.nonprofit_persistence_service,
        )
        return result.to_dict()


@dataclass(frozen=True)
class Form990DownloadedXml:
    xml_bytes: bytes
    source_reference: str


@dataclass(frozen=True)
class Form990ParsedRecord:
    filing_record: dict[str, Any]
    relationship_records: tuple[dict[str, Any], ...] = ()
    canonical_raw_filing_record: dict[str, Any] | None = None


def ingest_form990_records(
    records: list[Form990IndexRecord],
    relationships_prefix: str = "",
    download_raw: bool = False,
    downloader: Any | None = None,
    record_downloader: Any | None = None,
    nonprofit_persistence_service: Any | None = None,
    record_error_handler: Callable[[Form990IndexRecord, Exception, str], None] | None = None,
    record_cleanup_handler: Callable[[Form990IndexRecord], None] | None = None,
    persist_artifacts: bool = False,
    progress_session: ProgressSession | None = None,
) -> Form990IngestResult:
    started = datetime.now(timezone.utc)
    downloader = downloader or _download_raw_xml
    log_structured(
        LOGGER,
        "form990.ingest.records_parse_start",
        level=logging.DEBUG,
        record_count=len(records),
        download_raw=download_raw,
        persist_artifacts=False,
    )

    filing_records: list[dict[str, Any]] = []
    relationship_records: list[dict[str, Any]] = []
    canonical_raw_filing_records: list[dict[str, Any]] = []

    try:
        for record in records:
            metadata = _from_index_record(record)
            file_name = _record_file_name(record)
            progress_increments: dict[str, int] = {}

            if not _is_supported_return_type(record.return_type):
                filing = replace(metadata, parse_status=Form990ParseStatus.UNSUPPORTED_RETURN_TYPE).to_dict()
                filing_records.append(filing)
                if record_cleanup_handler is not None:
                    record_cleanup_handler(record)
                if progress_session is not None:
                    progress_session.item_completed(progress_increments)
                continue

            if not download_raw or not record.xml_url:
                filing = metadata.to_dict()
                filing_records.append(filing)
                if record_cleanup_handler is not None:
                    record_cleanup_handler(record)
                if progress_session is not None:
                    progress_session.item_completed(progress_increments)
                continue

            try:
                source_reference = record.xml_url or ""
                if record_downloader is not None:
                    downloaded = record_downloader(record)
                    if isinstance(downloaded, Form990DownloadedXml):
                        xml_bytes = downloaded.xml_bytes
                        source_reference = downloaded.source_reference or source_reference
                    elif isinstance(downloaded, tuple) and len(downloaded) == 2:
                        xml_bytes = downloaded[0]
                        source_reference = str(downloaded[1] or source_reference)
                    else:
                        xml_bytes = downloaded
                else:
                    xml_bytes = downloader(record.xml_url)
                parsed_record = parse_form990_record_xml(
                    record,
                    xml_bytes=xml_bytes,
                    source_reference=source_reference,
                    record_error_handler=record_error_handler,
                )
                filing_records.append(parsed_record.filing_record)
                relationship_records.extend(parsed_record.relationship_records)
                if parsed_record.canonical_raw_filing_record is not None:
                    canonical_raw_filing_records.append(parsed_record.canonical_raw_filing_record)
                progress_increments = _progress_increments_for_filing(parsed_record.filing_record)
            except Exception as exc:
                if record_error_handler is not None:
                    record_error_handler(record, exc, Form990ParseStatus.PARSE_ERROR.value)
                filing_records.append(
                    replace(
                        metadata,
                        parse_status=Form990ParseStatus.PARSE_ERROR,
                        parse_error=str(exc),
                    ).to_dict()
                )
                progress_increments = {"failed": 1}
            finally:
                if record_cleanup_handler is not None:
                    record_cleanup_handler(record)
                    # log_structured(
                    #     LOGGER,
                    #     "form990.ingest.xml_file_deleted",
                    #     level=logging.DEBUG,
                    #     file_name=file_name,
                    #     xml_source_reference=record.xml_url,
                    # )
                if progress_session is not None:
                    progress_session.item_completed(progress_increments)

        return finalize_form990_filing_records(
            filing_records,
            started=started,
            nonprofit_persistence_service=nonprofit_persistence_service,
            canonical_raw_filing_records=canonical_raw_filing_records,
        )
    finally:
        if progress_session is not None:
            progress_session.complete()


def parse_form990_record_xml(
    record: Form990IndexRecord,
    *,
    xml_bytes: bytes,
    source_reference: str | None = None,
    xml_content_hash: str | None = None,
    record_error_handler: Callable[[Form990IndexRecord, Exception, str], None] | None = None,
) -> Form990ParsedRecord:
    metadata = _from_index_record(record)
    file_name = _record_file_name(record)
    resolved_source_reference = str(source_reference or record.xml_url or "").strip()

    # log_structured(
    #     LOGGER,
    #     "form990.ingest.xml_parse_start",
    #     level=logging.DEBUG,
    #     file_name=file_name,
    #     irs_object_id=record.irs_object_id,
    #     xml_source_reference=resolved_source_reference,
    # )

    try:
        parsed = parse_xml(xml_bytes)
        resolved_content_hash = str(xml_content_hash or compute_normalized_xml_content_hash(xml_bytes)).strip()
        canonical_raw_filing_json = canonicalize_parsed_xml(parsed)
        extracted_meta = extract_metadata_fields(parsed)
        resolved_return_type = extracted_meta.get("return_type") or metadata.return_type
        if not _is_supported_return_type(resolved_return_type):
            filing = Form990MetadataRecord(
                ein=extracted_meta.get("ein") or metadata.ein,
                tax_year=extracted_meta.get("tax_year") or metadata.tax_year,
                tax_period_begin=extracted_meta.get("tax_period_begin"),
                tax_period_end=extracted_meta.get("tax_period_end"),
                filing_date=extracted_meta.get("filing_date") or metadata.filing_date,
                amended_return=extracted_meta.get("amended_return"),
                return_type=resolved_return_type,
                irs_object_id=metadata.irs_object_id,
                xml_source_reference=resolved_source_reference,
                raw_file_reference=resolved_source_reference,
                parse_status=Form990ParseStatus.UNSUPPORTED_RETURN_TYPE,
            ).to_dict()
            filing.update(_source_metadata_for_record(record))
            # log_structured(
            #     LOGGER,
            #     "form990.ingest.xml_parse_complete",
            #     level=logging.DEBUG,
            #     file_name=file_name,
            #     ein=filing.get("ein"),
            #     organization_name=_extract_organization_name(parsed),
            #     parse_status=filing.get("parse_status"),
            # )
            return Form990ParsedRecord(
                filing_record=filing,
                canonical_raw_filing_record=_canonical_raw_filing_record(
                    filing_record=filing,
                    record=record,
                    raw_filing_json=canonical_raw_filing_json,
                    xml_content_hash=resolved_content_hash,
                    xml_artifact_reference=resolved_source_reference,
                ),
            )

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
                return_type=resolved_return_type,
                irs_object_id=metadata.irs_object_id,
                xml_source_reference=resolved_source_reference,
                raw_file_reference=resolved_source_reference,
                parse_status=Form990ParseStatus.PARSED,
            ).to_dict(),
            **extracted_financials,
            **extracted_governance,
            **extracted_narratives,
            **_source_metadata_for_record(record),
        }
        # log_structured(
        #     LOGGER,
        #     "form990.ingest.xml_parse_complete",
        #     level=logging.DEBUG,
        #     file_name=file_name,
        #     ein=merged_filing.get("ein"),
        #     organization_name=_extract_organization_name(parsed),
        #     parse_status=merged_filing.get("parse_status"),
        # )
        return Form990ParsedRecord(
            filing_record=merged_filing,
            relationship_records=tuple(extract_relationship_edges(parsed, merged_filing)),
            canonical_raw_filing_record=_canonical_raw_filing_record(
                filing_record=merged_filing,
                record=record,
                raw_filing_json=canonical_raw_filing_json,
                xml_content_hash=resolved_content_hash,
                xml_artifact_reference=resolved_source_reference,
            ),
        )
    except XmlParseError as exc:
        if record_error_handler is not None:
            record_error_handler(record, exc, Form990ParseStatus.MALFORMED_XML.value)
        return Form990ParsedRecord(
            filing_record=replace(
                metadata,
                parse_status=Form990ParseStatus.MALFORMED_XML,
                parse_error=str(exc),
            ).to_dict()
        )
    except Exception as exc:
        if record_error_handler is not None:
            record_error_handler(record, exc, Form990ParseStatus.PARSE_ERROR.value)
        return Form990ParsedRecord(
            filing_record=replace(
                metadata,
                parse_status=Form990ParseStatus.PARSE_ERROR,
                parse_error=str(exc),
            ).to_dict()
        )


def finalize_form990_filing_records(
    filing_records: list[dict[str, Any]],
    *,
    started: datetime,
    nonprofit_persistence_service: Any | None = None,
    canonical_raw_filing_records: list[dict[str, Any]] | None = None,
) -> Form990IngestResult:
    grouped_filings: dict[str, list[dict[str, Any]]] = {}
    metrics_records: list[dict[str, Any]] = []
    governance_records: list[dict[str, Any]] = []
    quality_records: list[dict[str, Any]] = []

    for filing in filing_records:
        if not _should_group_filing_record(filing):
            continue
        grouped_filings.setdefault(str(filing.get("ein") or "unknown"), []).append(filing)

    for filings in grouped_filings.values():
        sorted_filings = sorted(filings, key=lambda item: item.get("tax_year") or "")
        for idx, filing in enumerate(sorted_filings):
            history = sorted_filings[:idx]
            metrics = compute_derived_metrics(filing, history=history)
            quality = compute_filing_quality(filing, history=history)

            metrics_records.append(
                {
                    "ein": filing.get("ein"),
                    "tax_year": filing.get("tax_year"),
                    **metrics,
                }
            )
            governance_records.append(
                {
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
            )
            quality_records.append(
                {
                    "ein": filing.get("ein"),
                    "tax_year": filing.get("tax_year"),
                    **quality,
                }
            )

    parsed_count = sum(1 for item in filing_records if item.get("parse_status") == Form990ParseStatus.PARSED.value)
    failed_count = sum(
        1
        for item in filing_records
        if item.get("parse_status") in {Form990ParseStatus.MALFORMED_XML.value, Form990ParseStatus.PARSE_ERROR.value}
    )
    status = "success" if failed_count == 0 else ("partial_success" if parsed_count > 0 else "failed")

    nonprofit_persistence = None
    if nonprofit_persistence_service is not None:
        nonprofit_persistence = nonprofit_persistence_service.persist_normalized_records(
            filing_records,
            canonical_raw_filing_records=canonical_raw_filing_records or [],
            persisted_at=started,
        ).to_dict()

    log_structured(
        LOGGER,
        "form990.ingest.records_parse_complete",
        level=logging.DEBUG,
        records_processed=len(filing_records),
        parsed_count=parsed_count,
        failed_count=failed_count,
        status=status,
    )

    return Form990IngestResult(
        status=status,
        records_processed=len(filing_records),
        parsed_count=parsed_count,
        failed_count=failed_count,
        records=filing_records,
        artifact_paths=None,
        nonprofit_persistence=nonprofit_persistence,
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
        raw_file_reference=None,
        parse_status=Form990ParseStatus.INDEX_ONLY,
    )


def _source_metadata_for_record(record: Form990IndexRecord) -> dict[str, Any]:
    return {
        "source_year": record.source_year,
        "source_archive": record.source_archive,
        "source_signature": record.source_signature,
    }


def _canonical_raw_filing_record(
    *,
    filing_record: dict[str, Any],
    record: Form990IndexRecord,
    raw_filing_json: dict[str, Any],
    xml_content_hash: str,
    xml_artifact_reference: str | None,
) -> dict[str, Any]:
    return Form990CanonicalRawFilingRecord(
        ein=_as_optional_text(filing_record.get("ein")),
        tax_year=_as_optional_text(filing_record.get("tax_year")),
        form_type=_as_optional_text(filing_record.get("return_type")),
        filing_date=_as_optional_text(filing_record.get("filing_date")),
        source_name="irs.form990",
        source_record_id=_as_optional_text(record.irs_object_id),
        source_signature=_as_optional_text(record.source_signature),
        xml_content_hash=xml_content_hash,
        xml_artifact_reference=_as_optional_text(xml_artifact_reference),
        parse_status=_as_optional_text(filing_record.get("parse_status")),
        parser_version=CANONICAL_FORM990_PARSER_VERSION,
        canonicalization_version=CANONICAL_FORM990_CANONICALIZATION_VERSION,
        raw_filing_json=raw_filing_json,
    ).to_dict()


def _as_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def _record_file_name(record: Form990IndexRecord) -> str:
    source_reference = str(record.xml_url or "").strip()
    if "#" in source_reference:
        return source_reference.rsplit("#", 1)[-1]
    return source_reference.rsplit("/", 1)[-1] if "/" in source_reference else source_reference


def _extract_organization_name(parsed: Any) -> str | None:
    root = getattr(parsed, "root", None)
    if root is None:
        return None
    for pattern in (
        ".//{*}BusinessName/{*}BusinessNameLine1Txt",
        ".//{*}ReturnHeader/{*}Filer/{*}BusinessName/{*}BusinessNameLine1Txt",
        ".//{*}BusinessNameLine1Txt",
    ):
        node = root.find(pattern)
        text = (node.text or "").strip() if node is not None and node.text is not None else ""
        if text:
            return text
    return None


def _progress_increments_for_filing(filing_record: dict[str, Any]) -> dict[str, int]:
    status = str(filing_record.get("parse_status") or "").strip().lower()
    if status == Form990ParseStatus.PARSED.value:
        return {"parsed": 1}
    if status in {Form990ParseStatus.MALFORMED_XML.value, Form990ParseStatus.PARSE_ERROR.value}:
        return {"failed": 1}
    return {}


def _should_group_filing_record(filing_record: dict[str, Any]) -> bool:
    status = str(filing_record.get("parse_status") or "").strip().lower()
    return status in {Form990ParseStatus.PARSED.value, Form990ParseStatus.INDEX_ONLY.value}

