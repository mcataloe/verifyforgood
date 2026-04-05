"""Local and ECS-style EO/BMF runtime owned by backend/ingest-task."""

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

from charity_status.form990.hardening import is_transient_network_error, retry_call
from charity_status.ingest.irs_files import IRS_FILES, source_url_for
from charity_status.ops import ProgressField, build_progress_reporter
from charity_status.runtime_logging import configure_runtime_logging, resolve_runtime_logging_config, sanitize_log_value
from charity_status_platform.runtime import build_nonprofit_postgres_repository

from .eo_bmf_ingest import ingest_eo_bmf_csv
from .orchestration.eo_bmf_workspace import build_eo_bmf_workspace_layout


DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True)
class EoBmfRunConfig:
    strict: bool = False
    keep_temp: bool = False
    workspace: str | None = None
    log_level: str = DEFAULT_LOG_LEVEL
    log_stack_traces: bool | None = None


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
        file_name: str = "",
        error: Exception | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        current_level = self._LEVELS.get(str(level or "INFO").strip().upper(), self._LEVELS["INFO"])
        if current_level < self._min_level:
            return
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "file": file_name,
            "level": level,
            "message": message,
        }
        payload.update(dict(extra or {}))
        if error is not None:
            payload["error"] = sanitize_log_value(str(error), key="error")
            payload["error_type"] = type(error).__name__
            if self._strict or self._include_traceback:
                payload["traceback"] = traceback.format_exc()
        print(json.dumps(payload, sort_keys=True))


def resolve_eo_bmf_runtime_environment_aliases(env: Mapping[str, str] | None = None) -> dict[str, str]:
    source_env = dict(os.environ if env is None else env)
    resolved = dict(source_env)

    if not str(resolved.get("PLATFORM_POSTGRES_URL") or "").strip():
        database_url = str(source_env.get("DATABASE_URL") or "").strip()
        if database_url:
            resolved["PLATFORM_POSTGRES_URL"] = database_url
            resolved.setdefault("PLATFORM_POSTGRES_ENABLED", "true")

    if not str(resolved.get("EOBMF_WORKSPACE_DIR") or "").strip():
        workspace_path = str(source_env.get("WORKSPACE_PATH") or "").strip()
        if workspace_path:
            resolved["EOBMF_WORKSPACE_DIR"] = workspace_path

    resolved.setdefault("PLATFORM_NONPROFIT_STORE_BACKEND", "postgres")
    resolved.setdefault("PLATFORM_NONPROFIT_QUERY_BACKEND", "postgres")
    return resolved


def build_eo_bmf_run_config(
    *,
    env: Mapping[str, str] | None = None,
    strict: bool | None = None,
    keep_temp: bool | None = None,
    workspace: str | None = None,
    log_level: str | None = None,
) -> EoBmfRunConfig:
    source_env = resolve_eo_bmf_runtime_environment_aliases(env)
    resolved_log_level = (
        str(log_level).strip().upper()
        if log_level is not None and str(log_level).strip()
        else str(source_env.get("LOG_LEVEL") or "").strip().upper()
    )
    if not resolved_log_level:
        resolved_log_level = resolve_runtime_logging_config(source_env).log_level_name
    return EoBmfRunConfig(
        strict=_env_bool(source_env, "STRICT_MODE", default=False) if strict is None else bool(strict),
        keep_temp=bool(keep_temp) if keep_temp is not None else False,
        workspace=workspace or _env_text(source_env, "EOBMF_WORKSPACE_DIR") or None,
        log_level=resolved_log_level,
        log_stack_traces=_env_optional_bool(source_env, "LOG_STACK_TRACES"),
    )


def run_local_eo_bmf_ingest(
    *,
    strict: bool,
    keep_temp: bool,
    workspace: str | None,
    env: Mapping[str, str] | None = None,
) -> int:
    config = build_eo_bmf_run_config(
        env=env,
        strict=strict,
        keep_temp=keep_temp,
        workspace=workspace,
    )
    return run_local_eo_bmf_ingest_config(config=config, env=env)


def run_local_eo_bmf_ingest_config(
    config: EoBmfRunConfig,
    *,
    env: Mapping[str, str] | None = None,
) -> int:
    source_env = resolve_eo_bmf_runtime_environment_aliases(env)
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
    repository = build_nonprofit_postgres_repository(env=source_env)
    if repository is None:
        logger.log(
            component="eo_bmf.cli",
            level="ERROR",
            message="postgres nonprofit repository could not be built",
        )
        return 1

    layout = build_eo_bmf_workspace_layout(
        {**source_env, **({"EOBMF_WORKSPACE_DIR": config.workspace} if config.workspace else {})}
    ).ensure()
    progress_reporter = build_progress_reporter()
    progress_session = progress_reporter.start(
        total_items=len(IRS_FILES),
        fields=[
            ProgressField(key="processed", label="processed", color="green"),
            ProgressField(key="failed", label="failed", color="red"),
        ],
        update_every=1,
    )
    logger.log(
        component="eo_bmf.cli",
        level="INFO",
        message="local eo_bmf ingest starting",
        extra={"workspace_root": str(layout.root)},
    )

    files: list[dict[str, Any]] = []
    rows_seen = 0
    nonprofits_upserted = 0
    filings_upserted = 0
    invalid_rows = 0
    failure_count = 0

    try:
        for filename in IRS_FILES:
            file_workspace = layout.for_filename(filename).ensure()
            try:
                url = source_url_for(filename)
                logger.log(
                    component="eo_bmf.file",
                    level="INFO",
                    message="processing file",
                    file_name=filename,
                    extra={"source_url": url},
                )
                _download_file_to_path(
                    url=url,
                    destination=file_workspace.download_path,
                    timeout_seconds=int(source_env.get("EO_BMF_DOWNLOAD_TIMEOUT_SECONDS") or "300"),
                )
                stats = ingest_eo_bmf_csv(
                    path=str(file_workspace.download_path),
                    filename=filename,
                    repository=repository,
                )
                rows_seen += stats.rows_seen
                nonprofits_upserted += stats.nonprofits_upserted
                filings_upserted += stats.filings_upserted
                invalid_rows += stats.invalid_rows
                files.append(stats.to_dict())
                progress_session.item_completed({"processed": 1})
                logger.log(
                    component="eo_bmf.file",
                    level="INFO",
                    message="file processed",
                    file_name=filename,
                    extra=stats.to_dict(),
                )
                if stats.status == "failed":
                    failure_count += 1
                    if config.strict:
                        raise RuntimeError(f"eo_bmf file failed: {filename}")
            except Exception as exc:
                failure_count += 1
                files.append(
                    {
                        "filename": filename,
                        "status": "failed",
                        "rows_seen": 0,
                        "nonprofits_upserted": 0,
                        "filings_upserted": 0,
                        "invalid_rows": 0,
                        "error": str(exc),
                    }
                )
                progress_session.item_completed({"failed": 1})
                logger.log(
                    component="eo_bmf.file",
                    level="ERROR",
                    message="file processing failed",
                    file_name=filename,
                    error=exc,
                )
                if config.strict:
                    raise
            finally:
                if not config.keep_temp:
                    file_workspace.finalize_processed_file()
    finally:
        progress_session.complete()

    status = _result_status(files)
    logger.log(
        component="eo_bmf.cli",
        level="INFO",
        message="local eo_bmf ingest completed",
        extra={
            "status": status,
            "files_processed": len(files),
            "rows_seen": rows_seen,
            "nonprofits_upserted": nonprofits_upserted,
            "filings_upserted": filings_upserted,
            "invalid_rows": invalid_rows,
        },
    )
    print(
        json.dumps(
            {
                "status": status,
                "files_processed": len(files),
                "rows_seen": rows_seen,
                "nonprofits_upserted": nonprofits_upserted,
                "filings_upserted": filings_upserted,
                "invalid_rows": invalid_rows,
                "files": files,
            },
            sort_keys=True,
        )
    )
    return 0 if failure_count == 0 else 1


def _download_file_to_path(*, url: str, destination: Path, timeout_seconds: int) -> None:
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


def _result_status(files: list[dict[str, Any]]) -> str:
    if not files:
        return "failed"
    failed = [item for item in files if item.get("status") == "failed"]
    succeeded = [item for item in files if item.get("status") != "failed"]
    if failed and succeeded:
        return "partial_success"
    if failed:
        return "failed"
    return "success"


def _env_text(source_env: Mapping[str, str], key: str, default: str = "") -> str:
    return str(source_env.get(key) or default).strip()


def _env_bool(source_env: Mapping[str, str], key: str, *, default: bool) -> bool:
    raw = source_env.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() == "true"


def _env_optional_bool(source_env: Mapping[str, str], key: str) -> bool | None:
    raw = source_env.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip().lower() == "true"


__all__ = [
    "EoBmfRunConfig",
    "build_eo_bmf_run_config",
    "resolve_eo_bmf_runtime_environment_aliases",
    "run_local_eo_bmf_ingest",
    "run_local_eo_bmf_ingest_config",
]
