from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse

import boto3

from charity_status.form990.hardening import is_transient_network_error, retry_call
from charity_status.form990.monthly_workflow import Form990MonthlyWorkflowBinding, load_form990_monthly_workflow_binding
from charity_status.form990.source_downloads import download_source_bytes
from charity_status.ingest import MonthlyIngestWorkflowInput, shape_staging_result
from charity_status.runtime_logging import configure_runtime_logging, log_structured

LOGGER = logging.getLogger(__name__)
LOGGING_CONFIG = configure_runtime_logging(os.environ, logger=LOGGER)

DEFAULT_SOURCE_KIND = "zip_archive"


@dataclass(frozen=True)
class Form990MonthlyStagingSource:
    source_url: str
    source_year: str
    source_kind: str
    source_archive_key: str
    source_filename: str
    source_signature: str | None = None
    source_timestamp: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not _clean_text(self.source_url):
            errors.append("schedule_context.source_url is required")
        if not _clean_text(self.source_year):
            errors.append("schedule_context.source_year is required")
        if not _clean_text(self.source_kind):
            errors.append("schedule_context.source_kind is required")
        if not _clean_text(self.source_archive_key):
            errors.append("schedule_context.source_archive_key is required")
        if not _clean_text(self.source_filename):
            errors.append("schedule_context.source_filename is required")
        return errors

    @classmethod
    def from_schedule_context(
        cls,
        schedule_context: Mapping[str, Any] | None,
        *,
        now: datetime | None = None,
    ) -> "Form990MonthlyStagingSource":
        source = _staging_context(schedule_context)
        source_url = _clean_text(source.get("source_url") or source.get("vendor_zip_url") or source.get("upstream_url")) or ""
        source_timestamp = _clean_text(source.get("source_timestamp") or source.get("vendor_timestamp"))
        source_filename = _clean_text(source.get("source_filename")) or _filename_from_url(source_url)
        source_archive_key = _clean_text(source.get("source_archive_key")) or _derive_archive_key(source_filename)
        source_year = (
            _clean_text(source.get("source_year"))
            or _year_from_text(source_filename)
            or _year_from_text(source_archive_key)
            or _year_from_text(source_timestamp)
            or str((now or datetime.now(timezone.utc)).year)
        )
        instance = cls(
            source_url=source_url,
            source_year=source_year,
            source_kind=_clean_text(source.get("source_kind")) or DEFAULT_SOURCE_KIND,
            source_archive_key=source_archive_key,
            source_filename=source_filename,
            source_signature=_clean_text(source.get("source_signature")),
            source_timestamp=source_timestamp,
        )
        errors = instance.validate()
        if errors:
            raise ValueError("; ".join(errors))
        return instance


def stage_form990_monthly_source(
    event: Mapping[str, Any] | None,
    *,
    env: Mapping[str, str] | None = None,
    s3_client: Any | None = None,
    downloader: Any | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    binding = load_form990_monthly_workflow_binding(env)
    config_errors = binding.validate()
    if config_errors:
        raise ValueError("; ".join(config_errors))

    payload = dict(event or {})
    workflow_input = _resolve_workflow_input(payload)
    schedule_context = _resolve_schedule_context(payload)
    if _skip_staging_requested(payload):
        return shape_staging_result(
            bucket=workflow_input.source_bucket,
            key=workflow_input.source_key,
            job_id=workflow_input.job_id,
            correlation_id=workflow_input.correlation_id,
            workflow_version=workflow_input.workflow_version,
            status="skipped",
        ).to_dict()

    staged_source = Form990MonthlyStagingSource.from_schedule_context(schedule_context, now=now)
    _log_structured(
        "form990.monthly_staging.start",
        job_id=workflow_input.job_id,
        correlation_id=workflow_input.correlation_id,
        source_url=staged_source.source_url,
        source_year=staged_source.source_year,
        source_archive_key=staged_source.source_archive_key,
    )
    body, content_type = retry_call(
        lambda: (downloader or download_source_bytes)(
            staged_source.source_url,
            timeout_seconds=binding.source_download_timeout_seconds,
        ),
        max_attempts=3,
        is_retryable=is_transient_network_error,
    )
    checksum = hashlib.sha256(body).hexdigest()
    source_signature = staged_source.source_signature or f"sha256-{checksum}"
    bucket = workflow_input.source_bucket or binding.bucket
    key = binding.build_staged_source_key(
        source_year=staged_source.source_year,
        source_kind=staged_source.source_kind,
        source_archive_key=staged_source.source_archive_key,
        source_signature=source_signature,
        source_filename=staged_source.source_filename,
    )
    put_kwargs = {
        "Bucket": bucket,
        "Key": key,
        "Body": body,
        "Metadata": _s3_metadata(
            workflow_input=workflow_input,
            staged_source=staged_source,
            checksum=checksum,
            downloaded_at=(now or datetime.now(timezone.utc)).isoformat(),
        ),
    }
    if _clean_text(content_type):
        put_kwargs["ContentType"] = content_type
    (s3_client or boto3.client("s3")).put_object(**put_kwargs)

    result = shape_staging_result(
        bucket=bucket,
        key=key,
        job_id=workflow_input.job_id,
        correlation_id=workflow_input.correlation_id,
        size=len(body),
        checksum=checksum,
        checksum_algorithm="sha256",
        source_timestamp=staged_source.source_timestamp,
        workflow_version=workflow_input.workflow_version,
    ).to_dict()
    result.update(
        {
            "content_type": content_type,
            "source_url": staged_source.source_url,
            "source_year": staged_source.source_year,
            "source_kind": staged_source.source_kind,
            "source_archive_key": staged_source.source_archive_key,
            "source_filename": staged_source.source_filename,
            "source_signature": source_signature,
        }
    )
    _log_structured(
        "form990.monthly_staging.completed",
        job_id=workflow_input.job_id,
        correlation_id=workflow_input.correlation_id,
        bucket=bucket,
        key=key,
        size=len(body),
        checksum=checksum,
    )
    return result


def _resolve_workflow_input(payload: Mapping[str, Any]) -> MonthlyIngestWorkflowInput:
    if isinstance(payload.get("resolved_input"), Mapping):
        return MonthlyIngestWorkflowInput.from_mapping(payload["resolved_input"])
    if isinstance(payload.get("input"), Mapping):
        return MonthlyIngestWorkflowInput.from_mapping(payload["input"])
    return MonthlyIngestWorkflowInput.from_mapping(payload)


def _resolve_schedule_context(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if isinstance(payload.get("input"), Mapping):
        schedule_context = payload["input"].get("schedule_context")
        if isinstance(schedule_context, Mapping):
            return schedule_context
    schedule_context = payload.get("schedule_context")
    if isinstance(schedule_context, Mapping):
        return schedule_context
    return None


def _staging_context(schedule_context: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(schedule_context, Mapping):
        return {}
    nested = schedule_context.get("staging")
    if isinstance(nested, Mapping):
        return nested
    return schedule_context


def _skip_staging_requested(payload: Mapping[str, Any]) -> bool:
    if bool(payload.get("skip_staging")):
        return True
    nested = payload.get("input")
    if isinstance(nested, Mapping):
        return bool(nested.get("skip_staging"))
    return False


def _s3_metadata(
    *,
    workflow_input: MonthlyIngestWorkflowInput,
    staged_source: Form990MonthlyStagingSource,
    checksum: str,
    downloaded_at: str,
) -> dict[str, str]:
    metadata = {
        "job_id": workflow_input.job_id[:128],
        "correlation_id": workflow_input.correlation_id[:128],
        "workflow_version": workflow_input.workflow_version[:64],
        "source_url": staged_source.source_url[:1024],
        "source_kind": staged_source.source_kind[:128],
        "source_year": staged_source.source_year[:32],
        "source_archive_key": staged_source.source_archive_key[:256],
        "source_filename": staged_source.source_filename[:256],
        "downloaded_at": downloaded_at[:64],
        "checksum_sha256": checksum[:64],
    }
    if _clean_text(staged_source.source_timestamp):
        metadata["source_timestamp"] = str(staged_source.source_timestamp)[:64]
    if _clean_text(staged_source.source_signature):
        metadata["source_signature"] = str(staged_source.source_signature)[:256]
    return metadata


def _filename_from_url(source_url: str) -> str:
    path = urlparse(source_url or "").path
    candidate = path.rstrip("/").split("/")[-1]
    return candidate or "source.zip"


def _derive_archive_key(source_filename: str) -> str:
    stem = source_filename.rsplit(".", 1)[0]
    normalized = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    return normalized or "monthly_source"


def _year_from_text(value: str | None) -> str | None:
    match = re.search(r"(20\d{2})", str(value or ""))
    return match.group(1) if match else None


def _clean_text(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _log_structured(event: str, **fields: Any) -> None:
    log_structured(LOGGER, event, **fields)


__all__ = [
    "DEFAULT_SOURCE_KIND",
    "Form990MonthlyStagingSource",
    "stage_form990_monthly_source",
]
