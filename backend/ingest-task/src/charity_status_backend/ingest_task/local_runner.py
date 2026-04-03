"""Local archive-at-a-time Form 990 runner for deterministic debugging."""

from __future__ import annotations

import json
import logging
import os
import traceback
import urllib.request
from dataclasses import dataclass
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

from .orchestration import build_workspace_layout
from .persistence import build_form990_archive_metadata_service, build_form990_nonprofit_persistence_service


DEFAULT_SOURCE_MODE = "static_manifest"
DEFAULT_IRS_DOWNLOADS_PAGE_URL = "https://www.irs.gov/charities-non-profits/form-990-series-downloads"
DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True)
class LocalIngestRunConfig:
    archive_url: str | None = None
    single_archive: bool = False
    strict: bool = False
    keep_temp: bool = False
    workspace: str | None = None
    limit: int | None = None
    log_level: str = DEFAULT_LOG_LEVEL


class _ConsoleStructuredLogger:
    _LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(self, *, strict: bool, level: str = DEFAULT_LOG_LEVEL):
        self._strict = strict
        normalized = str(level or DEFAULT_LOG_LEVEL).strip().upper() or DEFAULT_LOG_LEVEL
        self._min_level = self._LEVELS.get(normalized, self._LEVELS[DEFAULT_LOG_LEVEL])

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
        current_level = self._LEVELS.get(str(level or "INFO").strip().upper(), self._LEVELS["INFO"])
        if current_level < self._min_level:
            return
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


def resolve_runtime_environment_aliases(env: Mapping[str, str] | None = None) -> dict[str, str]:
    source_env = dict(os.environ if env is None else env)
    resolved = dict(source_env)

    if not str(resolved.get("PLATFORM_POSTGRES_URL") or "").strip():
        database_url = str(source_env.get("DATABASE_URL") or "").strip()
        if database_url:
            resolved["PLATFORM_POSTGRES_URL"] = database_url
            resolved.setdefault("PLATFORM_POSTGRES_ENABLED", "true")

    if not str(resolved.get("FORM990_WORKSPACE_DIR") or "").strip():
        workspace_path = str(source_env.get("WORKSPACE_PATH") or "").strip()
        if workspace_path:
            resolved["FORM990_WORKSPACE_DIR"] = workspace_path

    return resolved


def build_local_ingest_run_config(
    *,
    env: Mapping[str, str] | None = None,
    archive_url: str | None = None,
    single_archive: bool | None = None,
    strict: bool | None = None,
    keep_temp: bool | None = None,
    workspace: str | None = None,
    limit: int | None = None,
    log_level: str | None = None,
) -> LocalIngestRunConfig:
    source_env = resolve_runtime_environment_aliases(env)
    return LocalIngestRunConfig(
        archive_url=archive_url,
        single_archive=bool(single_archive) if single_archive is not None else False,
        strict=_env_bool(source_env, "STRICT_MODE", default=False) if strict is None else bool(strict),
        keep_temp=bool(keep_temp) if keep_temp is not None else False,
        workspace=workspace or _env_text(source_env, "FORM990_WORKSPACE_DIR") or None,
        limit=_env_optional_int(source_env, "MAX_ARCHIVES") if limit is None else limit,
        log_level=log_level or _env_text(source_env, "LOG_LEVEL", DEFAULT_LOG_LEVEL) or DEFAULT_LOG_LEVEL,
    )


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
    config = build_local_ingest_run_config(
        env=env,
        archive_url=archive_url,
        single_archive=single_archive,
        strict=strict,
        keep_temp=keep_temp,
        workspace=workspace,
        limit=limit,
    )
    return run_local_form990_ingest_config(config=config, env=env)


def run_local_form990_ingest_config(
    config: LocalIngestRunConfig,
    *,
    env: Mapping[str, str] | None = None,
) -> int:
    source_env = resolve_runtime_environment_aliases(env)
    logging.getLogger().setLevel(_logging_level(config.log_level))
    logger = _ConsoleStructuredLogger(strict=config.strict, level=config.log_level)
    layout = build_workspace_layout(
        {**source_env, **({"FORM990_WORKSPACE_DIR": config.workspace} if config.workspace else {})}
    ).ensure()
    logger.log(
        component="form990.cli",
        level="INFO",
        message="local form990 ingest starting",
        archive="",
        file_name="",
    )

    archive_metadata_service = _build_archive_metadata_service(env=source_env, logger=logger)
    nonprofit_persistence_service = build_form990_nonprofit_persistence_service(env=source_env)
    artifacts = _resolve_archive_sources(source_env, archive_url=config.archive_url)
    zip_artifacts = [artifact for artifact in artifacts if artifact.source_kind == SOURCE_KIND_ZIP_ARCHIVE]
    if config.single_archive:
        zip_artifacts = zip_artifacts[:1]
    if config.limit is not None and config.limit >= 0:
        zip_artifacts = zip_artifacts[: config.limit]
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
                "source_bucket": "",
                "source_key": _local_source_key(artifact),
                "destination_bucket": "",
                "destination_prefix": "",
                "job_id": f"local-cli-{run_id}-{archive_name}",
                "correlation_id": f"local-cli-{run_id}",
                "workflow_version": "local-cli",
                "source_url": artifact.source_url,
                "workspace_root": str(layout.root),
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
                artifact_keys=None,
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
                if config.strict:
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
            if config.strict:
                raise
        finally:
            if not config.keep_temp:
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


def _env_text(source_env: Mapping[str, str], key: str, default: str = "") -> str:
    return str(source_env.get(key) or default).strip()


def _env_bool(source_env: Mapping[str, str], key: str, *, default: bool) -> bool:
    raw = source_env.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _env_optional_int(source_env: Mapping[str, str], key: str) -> int | None:
    raw = _env_text(source_env, key)
    if not raw:
        return None
    return int(raw)


def _logging_level(level: str) -> int:
    return getattr(logging, str(level or DEFAULT_LOG_LEVEL).strip().upper(), logging.INFO)
