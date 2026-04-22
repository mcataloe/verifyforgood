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

from verification.backend.ingest.federal.form990.hardening import retry_call, is_transient_network_error
from verification.backend.ingest.federal.form990.irs_page_discovery import discover_irs_form990_sources
from verification.backend.ingest.federal.form990.monthly_processing import (
    MonthlyIngestSourceObject,
    process_form990_archive,
)
from verification.backend.ingest.federal.form990.source_catalog import (
    SOURCE_KIND_ZIP_ARCHIVE,
    build_source_artifact,
    derive_source_archive_key,
    derive_source_filename,
    derive_source_year,
    normalize_configured_sources,
)
from verification.backend.ingest.federal.form990.static_source_discovery import discover_static_form990_sources
from verification.backend.shared.ops import InMemoryRunStore, build_progress_reporter, prepare_stream_for_external_write
from verification.backend.shared.ops.run_store import safe_error_summary
from verification.backend.shared.runtime_logging import configure_runtime_logging, resolve_runtime_logging_config, sanitize_log_value

from .orchestration import build_workspace_layout
from .persistence import build_form990_archive_metadata_service, build_form990_nonprofit_persistence_service


DEFAULT_SOURCE_MODE = "static_manifest"
DEFAULT_IRS_DOWNLOADS_PAGE_URL = "https://www.irs.gov/charities-non-profits/form-990-series-downloads"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_XML_PARSER_WORKERS = 4


@dataclass(frozen=True)
class LocalIngestRunConfig:
    archive_url: str | None = None
    single_archive: bool = False
    strict: bool = False
    keep_temp: bool = False
    workspace: str | None = None
    limit: int | None = None
    xml_parser_workers: int = 1
    log_level: str = DEFAULT_LOG_LEVEL
    log_stack_traces: bool | None = None


@dataclass(frozen=True)
class Form990RunContext:
    run_id: str | None = None
    mode: str = "incremental"
    execution_mode: str = "inline"
    target_years: tuple[str, ...] = ()
    triggered_at: str | None = None


class _ConsoleStructuredLogger:
    _LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    def __init__(self, *, strict: bool, level: str = DEFAULT_LOG_LEVEL, include_traceback: bool | None = None):
        self._strict = strict
        normalized = str(level or DEFAULT_LOG_LEVEL).strip().upper() or DEFAULT_LOG_LEVEL
        self._min_level = self._LEVELS.get(normalized, self._LEVELS[DEFAULT_LOG_LEVEL])
        self._include_traceback = include_traceback if include_traceback is not None else strict

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
            payload["error"] = sanitize_log_value(str(error), key="error")
            payload["error_type"] = type(error).__name__
            if self._strict or self._include_traceback:
                payload["traceback"] = traceback.format_exc()
        prepare_stream_for_external_write()
        print(json.dumps(payload, sort_keys=True))


def resolve_runtime_environment_aliases(env: Mapping[str, str] | None = None) -> dict[str, str]:
    source_env = dict(os.environ if env is None else env)
    resolved = dict(source_env)

    if not str(resolved.get("PLATFORM_POSTGRES_URL") or "").strip():
        database_url = str(source_env.get("DATABASE_URL") or "").strip()
        if database_url:
            resolved["PLATFORM_POSTGRES_URL"] = database_url
            resolved.setdefault("PLATFORM_POSTGRES_ENABLED", "true")
    if not str(resolved.get("PLATFORM_NONPROFIT_POSTGRES_URL") or "").strip():
        database_url = str(source_env.get("DATABASE_URL") or "").strip()
        if database_url:
            resolved["PLATFORM_NONPROFIT_POSTGRES_URL"] = database_url
            resolved.setdefault("PLATFORM_NONPROFIT_POSTGRES_ENABLED", "true")

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
    xml_parser_workers: int | None = None,
    log_level: str | None = None,
) -> LocalIngestRunConfig:
    source_env = resolve_runtime_environment_aliases(env)
    resolved_log_level = (
        str(log_level).strip().upper()
        if log_level is not None and str(log_level).strip()
        else str(source_env.get("LOG_LEVEL") or "").strip().upper()
    )
    if not resolved_log_level:
        resolved_log_level = resolve_runtime_logging_config(source_env).log_level_name
    return LocalIngestRunConfig(
        archive_url=archive_url,
        single_archive=bool(single_archive) if single_archive is not None else False,
        strict=_env_bool(source_env, "STRICT_MODE", default=False) if strict is None else bool(strict),
        keep_temp=bool(keep_temp) if keep_temp is not None else False,
        workspace=workspace or _env_text(source_env, "FORM990_WORKSPACE_DIR") or None,
        limit=_env_optional_int(source_env, "MAX_ARCHIVES") if limit is None else limit,
        xml_parser_workers=_resolve_xml_parser_workers(source_env, override=xml_parser_workers),
        log_level=resolved_log_level,
        log_stack_traces=_env_optional_bool(source_env, "LOG_STACK_TRACES"),
    )


def run_local_form990_ingest(
    *,
    archive_url: str | None,
    single_archive: bool,
    strict: bool,
    keep_temp: bool,
    workspace: str | None,
    limit: int | None,
    xml_parser_workers: int | None = None,
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
        xml_parser_workers=xml_parser_workers,
    )
    return run_local_form990_ingest_config(config=config, env=env)


def run_local_form990_ingest_config(
    config: LocalIngestRunConfig,
    *,
    env: Mapping[str, str] | None = None,
) -> int:
    source_env = resolve_runtime_environment_aliases(env)
    runtime_logging = configure_runtime_logging(
        {
            **source_env,
            "LOG_LEVEL": config.log_level,
            **({"LOG_STACK_TRACES": str(config.log_stack_traces).lower()} if config.log_stack_traces is not None else {}),
        }
    )
    logger = _ConsoleStructuredLogger(
        strict=config.strict,
        level=runtime_logging.log_level_name,
        include_traceback=config.log_stack_traces if config.log_stack_traces is not None else runtime_logging.include_stack_traces,
    )
    progress_reporter = build_progress_reporter()
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

    run_context = _resolve_form990_run_context(source_env)
    started_at = datetime.now(timezone.utc)
    archive_metadata_service = _build_archive_metadata_service(env=source_env, logger=logger)
    nonprofit_persistence_service = build_form990_nonprofit_persistence_service(env=source_env)
    ops_run_store = _build_ops_run_store(source_env)
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
    records_processed = 0
    parsed_count = 0
    failed_record_count = 0
    filing_summaries: list[dict[str, Any]] = []
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
            logger.log(
                component="form990.archive",
                level="DEBUG",
                message=f"about to download zip archive url={artifact.source_url} destination={archive_workspace.archive_path}",
                archive=archive_name,
            )
            logger.log(
                component="form990.archive",
                level="DEBUG",
                message=f"downloading zip archive to {archive_workspace.archive_path}",
                archive=archive_name,
            )
            _download_archive_to_path(
                url=artifact.source_url,
                destination=archive_workspace.archive_path,
                timeout_seconds=int(source_env.get("FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS") or "300"),
            )
            logger.log(
                component="form990.archive",
                level="DEBUG",
                message=(
                    f"zip archive downloaded path={archive_workspace.archive_path} "
                    f"size_bytes={archive_workspace.archive_path.stat().st_size}"
                ),
                archive=archive_name,
            )
            archive_run_id = run_context.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            processing_context = {
                "archive_identity": _local_archive_identity(artifact),
                "job_id": archive_run_id,
                "correlation_id": archive_run_id,
                "workflow_version": run_context.execution_mode,
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
                progress_reporter=progress_reporter,
                xml_parser_workers=config.xml_parser_workers,
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
            records_processed += int(result.get("records_processed") or 0)
            parsed_count += int(result.get("parsed_count") or 0)
            failed_record_count += int(result.get("failed_count") or 0)
            filing_summaries.extend(_build_filing_summaries(result))
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
                logger.log(
                    component="form990.archive",
                    level="DEBUG",
                    message=f"deleting extracted workspace directory {archive_workspace.extracted_dir}",
                    archive=archive_name,
                )
                logger.log(
                    component="form990.archive",
                    level="DEBUG",
                    message=f"deleting temporary zip file {archive_workspace.archive_path}",
                    archive=archive_name,
                )
                archive_workspace.finalize_processed_archive()
                logger.log(
                    component="form990.archive",
                    level="DEBUG",
                    message=f"temporary extracted directory deleted path={archive_workspace.extracted_dir}",
                    archive=archive_name,
                )
                logger.log(
                    component="form990.archive",
                    level="DEBUG",
                    message=f"temporary zip file deleted path={archive_workspace.archive_path}",
                    archive=archive_name,
                )
                logger.log(
                    component="form990.archive",
                    level="DEBUG",
                    message=f"temporary workspace cleanup completed extracted_dir={archive_workspace.extracted_dir} zip_path={archive_workspace.archive_path}",
                    archive=archive_name,
                )

    _write_ops_ingest_run(
        env=source_env,
        store=ops_run_store,
        run_context=run_context,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        archive_count=len(zip_artifacts),
        failure_count=failure_count,
        records_processed=records_processed,
        parsed_count=parsed_count,
        failed_record_count=failed_record_count,
        filings=filing_summaries,
    )
    logger.log(
        component="form990.cli",
        level="INFO",
        message=f"local form990 ingest completed failure_count={failure_count}",
    )
    logger.log(
        component="form990.cli",
        level="DEBUG",
        message=f"whole procedure completed workspace_root={layout.root} failure_count={failure_count}",
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


def _local_archive_identity(artifact: Any) -> str:
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


def _env_optional_bool(source_env: Mapping[str, str], key: str) -> bool | None:
    raw = source_env.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip().lower() == "true"


def _parse_json_string_list(source_env: Mapping[str, str], key: str) -> tuple[str, ...]:
    raw = _env_text(source_env, key)
    if not raw:
        return ()
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError(f"{key} must decode to a JSON array")
    values: list[str] = []
    for item in payload:
        if not isinstance(item, str):
            raise ValueError(f"{key} entries must be strings")
        value = item.strip()
        if value:
            values.append(value)
    return tuple(values)


def _resolve_form990_run_context(source_env: Mapping[str, str]) -> Form990RunContext:
    return Form990RunContext(
        run_id=_env_text(source_env, "FORM990_RUN_ID")
        or _env_text(source_env, "FORM990_MANUAL_RUN_ID")
        or _env_text(source_env, "MONTHLY_INGEST_JOB_ID")
        or None,
        mode=_env_text(source_env, "FORM990_RUN_MODE", _env_text(source_env, "FORM990_MANUAL_MODE", "incremental")) or "incremental",
        execution_mode=_env_text(source_env, "FORM990_EXECUTION_MODE", "inline") or "inline",
        target_years=_parse_json_string_list(source_env, "FORM990_MANUAL_TARGET_YEARS"),
        triggered_at=_env_text(source_env, "FORM990_TRIGGERED_AT") or None,
    )


def _build_ops_run_store(source_env: Mapping[str, str]) -> InMemoryRunStore | None:
    del source_env
    return InMemoryRunStore()


def _build_filing_summaries(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = result.get("records")
    if not isinstance(records, list):
        return []
    summaries: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        summaries.append(
            {
                "ein": item.get("ein"),
                "tax_year": item.get("tax_year"),
                "return_type": item.get("return_type"),
                "filing_date": item.get("filing_date"),
                "parse_status": item.get("parse_status"),
            }
        )
    return summaries


def _write_ops_ingest_run(
    *,
    env: Mapping[str, str],
    store: InMemoryRunStore | None,
    run_context: Form990RunContext,
    started_at: datetime,
    completed_at: datetime,
    archive_count: int,
    failure_count: int,
    records_processed: int,
    parsed_count: int,
    failed_record_count: int,
    filings: list[dict[str, Any]],
) -> None:
    if store is None or not run_context.run_id:
        return
    status = "success" if failure_count == 0 and failed_record_count == 0 else ("partial_success" if parsed_count > 0 else "failed")
    payload = {
        "ingest_run_id": run_context.run_id,
        "status": status,
        "execution_mode": run_context.execution_mode,
        "mode": run_context.mode,
        "target_years": list(run_context.target_years),
        "triggered_at": run_context.triggered_at or started_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "started_at": started_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "completed_at": completed_at.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "archive_count": archive_count,
        "records_processed": records_processed,
        "parsed_count": parsed_count,
        "failed_count": failed_record_count,
        "archive_failure_count": failure_count,
    }
    try:
        store.write_ingest_run(run_context.run_id, payload)
        store.write_ingest_filings(run_context.run_id, filings)
    except Exception as exc:
        _ConsoleStructuredLogger(strict=False, level=_env_text(env, "LOG_LEVEL", DEFAULT_LOG_LEVEL)).log(
            component="form990.ops",
            level="WARNING",
            message=f"failed to publish ingest run metadata summary={safe_error_summary([{'code': 'ops_run_store_write_failed', 'error': str(exc)}])}",
            error=exc,
        )


def _resolve_xml_parser_workers(source_env: Mapping[str, str], *, override: int | None = None) -> int:
    if override is not None:
        return max(1, int(override))
    configured = _env_optional_int(source_env, "FORM990_XML_PARSER_WORKERS")
    if configured is not None:
        return max(1, configured)
    available_cpu = _available_cpu_count()
    return min(DEFAULT_MAX_XML_PARSER_WORKERS, max(1, available_cpu - 1))


def _available_cpu_count() -> int:
    try:
        affinity = os.sched_getaffinity(0)
    except AttributeError:
        affinity = None
    if affinity:
        return max(1, len(affinity))
    cgroup_count = _available_cpu_count_from_cgroup()
    if cgroup_count is not None:
        return cgroup_count
    return max(1, int(os.cpu_count() or 1))


def _available_cpu_count_from_cgroup() -> int | None:
    cpu_max_path = Path("/sys/fs/cgroup/cpu.max")
    if cpu_max_path.exists():
        try:
            quota_text, period_text = cpu_max_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
            if quota_text != "max":
                quota = int(quota_text)
                period = int(period_text)
                if quota > 0 and period > 0:
                    return max(1, (quota + period - 1) // period)
        except (OSError, ValueError):
            pass

    quota_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period_path = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota_path.exists() and period_path.exists():
        try:
            quota = int(quota_path.read_text(encoding="utf-8").strip())
            period = int(period_path.read_text(encoding="utf-8").strip())
            if quota > 0 and period > 0:
                return max(1, (quota + period - 1) // period)
        except (OSError, ValueError):
            pass
    return None

