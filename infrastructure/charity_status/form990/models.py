from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Form990ParseStatus(str, Enum):
    INDEX_ONLY = "index_only"
    PARSED = "parsed"
    MALFORMED_XML = "malformed_xml"
    PARSE_ERROR = "parse_error"
    UNSUPPORTED_RETURN_TYPE = "unsupported_return_type"


@dataclass(frozen=True)
class Form990MetadataRecord:
    ein: str | None
    tax_year: str | None
    tax_period_begin: str | None
    tax_period_end: str | None
    filing_date: str | None
    amended_return: bool | None
    return_type: str | None
    irs_object_id: str | None
    xml_source_reference: str | None
    raw_s3_key: str | None
    parse_status: Form990ParseStatus
    parse_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parse_status"] = self.parse_status.value
        return payload


@dataclass(frozen=True)
class Form990IndexRecord:
    ein: str | None
    tax_year: str | None
    filing_date: str | None
    return_type: str | None
    irs_object_id: str | None
    xml_url: str | None
    source_year: str | None = None
    source_archive: str | None = None
    source_signature: str | None = None


@dataclass(frozen=True)
class Form990IngestResult:
    status: str
    records_processed: int
    parsed_count: int
    failed_count: int
    manifest_s3_key: str | None
    filing_records_s3_key: str | None
    metrics_s3_key: str | None
    governance_s3_key: str | None
    quality_s3_key: str | None
    relationships_s3_key: str | None
    records: list[dict[str, Any]]
    nonprofit_persistence: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
