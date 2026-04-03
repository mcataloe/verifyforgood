"""Local archive-at-a-time Form 990 runner for deterministic debugging."""

from __future__ import annotations

import json
import os
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from charity_status.form990.hardening import retry_call, is_transient_network_error
from charity_status.form990.irs_page_discovery import discover_irs_form990_sources
from charity_status.form990.monthly_processing import (
    MonthlyIngestSourceObject,
    process_form990_archive,
)
from charity_status.form990.source_catalog import (
    SOURCE_KIND_ZIP_ARCHIVE,
    build_source_artifact,
    derive_source_archive_key,
    derive_source_filename,
    derive_source_year,
    normalize_configured_sources,
)
from charity_status.form990.static_source_discovery import discover_static_form990_sources
from charity_status.ingest.workflow import workflow_artifact_index_key, workflow_manifest_key, workflow_summary_key

from .orchestration import build_workspace_layout
from .persistence import build_form990_archive_metadata_service, build_form990_nonprofit_persistence_service


DEFAULT_SOURCE_MODE = "static_manifest"
DEFAULT_IRS_DOWNLOADS_PAGE_URL = "https://www.irs.gov/charities-non-profits/form-990-series-downloads"


class _ConsoleStructuredLogger:
    def __init__(self, *, strict: bool):
        self._strict = strict

    def log(
        self,
        *,
        component: str,
        level: str,
        message: str,
        archive: str = "",
        file_name: str = "",
        error: Exception | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "archive": archive,
            "file": file_name,
            "level": level,
            "message": message,
        }
        if error is not None:
            payload["error"] = str(error)
            payload["error_type"] = type(error).__name__
            if self._strict:
                payload["traceback"] = traceback.format_exc()
        print(json.dumps(payload, sort_keys=True))


def run_local_form990_ingest(
    *,
    archive_url: str | None,
    single_archive: bool,
    strict: bool,
    keep_temp: bool,
    workspace: str | None,
    limit: int | None,
    env: Mapping[str, str] | None = None,
) -> int:
    source_env = dict(os.environ if env is None else env)
    logger = _ConsoleStructuredLogger(strict=strict)
    layout = build_workspace_layout(
        {**source_env, **({"FORM990_WORKSPACE_DIR": workspace} if workspace else {})}
    ).ensure()
    logger.log(
        component="form990.cli",
        level="INFO",
        message="local form990 ingest starting",
        archive="",
        file_name="",
    )
    bucket = str(source_env.get("BUCKET") or "").strip()
    if not bucket:
        raise ValueError("BUCKET is required for local Form 990 ingest")

    archive_metadata_service = _build_archive_metadata_service(env=source_env, logger=logger)
    nonprofit_persistence_service = build_form990_nonprofit_persistence_service(env=source_env)
    artifacts = _resolve_archive_sources(source_env, archive_url=archive_url)
    zip_artifacts = [artifact for artifact in artifacts if artifact.source_kind == SOURCE_KIND_ZIP_ARCHIVE]
    if single_archive:
        zip_artifacts = zip_artifacts[:1]
    if limit is not None and limit >= 0:
        zip_artifacts = zip_artifacts[:limit]
    if not zip_artifacts:
        logger.log(
            component="form990.cli",
            level="WARNING",
            message="no zip archives selected for local ingest",
        )
        return 0

    failure_count = 0
    for artifact in zip_artifacts:
        archive_name = artifact.source_archive_key
        archive_workspace = layout.for_archive(archive_name).ensure()
        try:
            logger.log(
                component="form990.archive",
                level="INFO",
                message="processing archive",
                archive=archive_name,
            )
            _download_archive_to_path(
                url=artifact.source_url,
                destination=archive_workspace.archive_path,
                timeout_seconds=int(source_env.get("FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS") or "300"),
            )
            run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            processing_context = {
                "source_bucket": bucket,
                "source_key": _local_source_key(artifact),
                "destination_bucket": bucket,
                "destination_prefix": str(source_env.get("FORM990_MANIFEST_PREFIX") or "form990/normalized/manifests/"),
                "job_id": f"local-cli-{run_id}-{archive_name}",
                "correlation_id": f"local-cli-{run_id}",
                "workflow_version": "local-cli",
                "source_url": artifact.source_url,
                "workspace_root": str(layout.root),
            }
            artifact_keys = {
                "manifest_s3_key": workflow_manifest_key(processing_context["destination_prefix"], processing_context["job_id"]),
                "artifact_index_s3_key": workflow_artifact_index_key(processing_context["destination_prefix"], processing_context["job_id"]),
                "summary_s3_key": workflow_summary_key(processing_context["destination_prefix"], processing_context["job_id"]),
            }
            source_object = MonthlyIngestSourceObject(
                source_year=artifact.source_year,
                source_kind=artifact.source_kind,
                source_archive_key=artifact.source_archive_key,
                source_signature=artifact.source_signature,
                source_filename=artifact.source_filename,
            )
            result = process_form990_archive(
                archive_path=str(archive_workspace.archive_path),
                extracted_workdir=str(archive_workspace.extracted_dir),
                processing_context=processing_context,
                source_object=source_object,
                artifact_keys=artifact_keys,
                started_at=datetime.now(timezone.utc),
                archive_metadata_service=archive_metadata_service,
                nonprofit_persistence_service=nonprofit_persistence_service,
                max_xml_file_size_bytes=int(source_env.get("FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES") or str(20 * 1024 * 1024)),
                xml_error_handler=lambda file_name, exc, status: logger.log(
                    component="form990.xml",
                    level="ERROR",
                    message=f"{status}: {exc}",
                    archive=archive_name,
                    file_name=file_name or "",
                    error=exc,
                ),
            )
            logger.log(
                component="form990.archive",
                level="INFO",
                message=(
                    f"archive completed status={result['status']} "
                    f"records_processed={result['records_processed']} parsed_count={result['parsed_count']} "
                    f"failed_count={result['failed_count']}"
                ),
                archive=archive_name,
            )
            if str(result.get("status") or "").strip().lower() == "failed":
                failure_count += 1
                if strict:
                    raise RuntimeError(
                        f"archive {archive_name} failed with {int(result.get('failed_count') or 0)} failed file(s)"
                    )
        except Exception as exc:
            failure_count += 1
            logger.log(
                component="form990.archive",
                level="ERROR",
                message="archive processing failed",
                archive=archive_name,
                error=exc,
            )
            if strict:
                raise
        finally:
            if not keep_temp:
                archive_workspace.finalize_processed_archive()

    logger.log(
        component="form990.cli",
        level="INFO",
        message=f"local form990 ingest completed failure_count={failure_count}",
    )
    return 0 if failure_count == 0 else 1


def _resolve_archive_sources(env: Mapping[str, str], *, archive_url: str | None) -> list[Any]:
    now = datetime.now(timezone.utc)
    if archive_url:
        source_url = archive_url.strip()
        filename = derive_source_filename(source_url)
        year = derive_source_year(f"{source_url} {filename}") or str(now.year)
        return [
            build_source_artifact(
                source_year=year,
                source_kind=SOURCE_KIND_ZIP_ARCHIVE,
                source_url=source_url,
                source_filename=filename,
                source_archive_key=derive_source_archive_key(filename),
                discovered_at=now.isoformat(),
                page_url="local://archive-url",
            )
        ]

    source_mode = str(env.get("FORM990_SOURCE_MODE") or DEFAULT_SOURCE_MODE).strip().lower()
    if source_mode == "configured":
        payload = json.loads(str(env.get("FORM990_SOURCE_CATALOG_JSON") or "[]"))
        if not isinstance(payload, list):
            raise ValueError("FORM990_SOURCE_CATALOG_JSON must decode to a JSON array")
        return normalize_configured_sources(payload, now=now)
    if source_mode == "irs_page":
        page_url = str(env.get("FORM990_IRS_DOWNLOADS_PAGE_URL") or DEFAULT_IRS_DOWNLOADS_PAGE_URL).strip()
        return discover_irs_form990_sources(
            page_url,
            timeout_seconds=int(env.get("FORM990_INDEX_FETCH_TIMEOUT_SECONDS") or "60"),
            now=now,
        )
    return discover_static_form990_sources(
        now=now,
        enable_next_year_generation=str(env.get("FORM990_ENABLE_NEXT_YEAR_GENERATION") or "true").lower() == "true",
    )


def _download_archive_to_path(*, url: str, destination: Path, timeout_seconds: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    def _download() -> None:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response, destination.open("wb") as handle:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

    retry_call(
        _download,
        max_attempts=3,
        is_retryable=is_transient_network_error,
    )


def _local_source_key(artifact: Any) -> str:
    return (
        f"form990/raw-sources/{artifact.source_year}/zip_archive/"
        f"{artifact.source_archive_key}/{artifact.source_signature}/{artifact.source_filename}"
    )


def _build_archive_metadata_service(*, env: Mapping[str, str], logger: _ConsoleStructuredLogger) -> Any | None:
    try:
        return build_form990_archive_metadata_service(env=env)
    except Exception as exc:
        logger.log(
            component="form990.cli",
            level="WARNING",
            message="archive metadata tracking disabled for local run",
            error=exc,
        )
    return None
