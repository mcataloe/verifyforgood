from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


STAGING_RESULT_REQUIRED_FIELDS: tuple[str, ...] = (
    "archive_identity",
    "archive_url",
    "job_id",
    "correlation_id",
)


@dataclass(frozen=True)
class MonthlyIngestStagingResult:
    archive_identity: str
    archive_url: str
    job_id: str
    correlation_id: str
    size: int | None = None
    checksum: str | None = None
    checksum_algorithm: str | None = None
    source_timestamp: str | None = None
    workflow_version: str | None = None
    status: str = "staged"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "archive_identity": self.archive_identity,
            "archive_url": self.archive_url,
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "status": self.status,
        }
        if self.size is not None:
            payload["size"] = self.size
        if _clean_text(self.checksum):
            payload["checksum"] = self.checksum
        if _clean_text(self.checksum_algorithm):
            payload["checksum_algorithm"] = self.checksum_algorithm
        if _clean_text(self.source_timestamp):
            payload["source_timestamp"] = self.source_timestamp
        if _clean_text(self.workflow_version):
            payload["workflow_version"] = self.workflow_version
        return payload

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "MonthlyIngestStagingResult":
        errors = validate_staging_result_payload(payload)
        if errors:
            raise ValueError("; ".join(errors))
        size_raw = payload.get("size")
        size = None if size_raw is None else int(size_raw)
        return cls(
            archive_identity=_clean_text(payload.get("archive_identity")) or "",
            archive_url=_clean_text(payload.get("archive_url")) or "",
            job_id=_clean_text(payload.get("job_id")) or "",
            correlation_id=_clean_text(payload.get("correlation_id")) or "",
            size=size,
            checksum=_clean_text(payload.get("checksum")),
            checksum_algorithm=_clean_text(payload.get("checksum_algorithm")),
            source_timestamp=_clean_text(payload.get("source_timestamp")),
            workflow_version=_clean_text(payload.get("workflow_version")),
            status=_clean_text(payload.get("status")) or "staged",
        )


def shape_staging_result(
    *,
    archive_identity: str,
    archive_url: str,
    job_id: str,
    correlation_id: str,
    size: int | None = None,
    checksum: str | None = None,
    checksum_algorithm: str | None = None,
    source_timestamp: str | None = None,
    workflow_version: str | None = None,
    status: str = "staged",
) -> MonthlyIngestStagingResult:
    return MonthlyIngestStagingResult.from_mapping(
        {
            "archive_identity": archive_identity,
            "archive_url": archive_url,
            "job_id": job_id,
            "correlation_id": correlation_id,
            "size": size,
            "checksum": checksum,
            "checksum_algorithm": checksum_algorithm,
            "source_timestamp": source_timestamp,
            "workflow_version": workflow_version,
            "status": status,
        }
    )


def validate_staging_result_payload(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return ["staging result payload must be an object"]
    errors: list[str] = []
    archive_identity = _clean_text(payload.get("archive_identity"))
    archive_url = _clean_text(payload.get("archive_url"))
    if not archive_identity:
        errors.append("archive_identity is required")
    if not archive_url:
        errors.append("archive_url is required")
    for field_name in ("job_id", "correlation_id"):
        if not _clean_text(payload.get(field_name)):
            errors.append(f"{field_name} is required")
    size = payload.get("size")
    if size is not None:
        try:
            parsed_size = int(size)
        except (TypeError, ValueError):
            errors.append("size must be an integer when provided")
        else:
            if parsed_size < 0:
                errors.append("size must be >= 0 when provided")
    return errors


def _clean_text(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


__all__ = [
    "MonthlyIngestStagingResult",
    "STAGING_RESULT_REQUIRED_FIELDS",
    "shape_staging_result",
    "validate_staging_result_payload",
]
