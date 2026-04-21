"""Local and ECS-style EO/BMF runtime owned by backend/ingest-task."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import os
import queue
import threading
import time
import traceback
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from verification.form990.hardening import is_transient_network_error, retry_call
from verification.ingest.irs_files import IRS_FILES, source_url_for
from verification.ops import ProgressField, ProgressSession, build_progress_reporter, prepare_stream_for_external_write
from verification.runtime_logging import configure_runtime_logging, resolve_runtime_logging_config, sanitize_log_value

from .eo_bmf_ingest import ingest_eo_bmf_csv
from .orchestration.eo_bmf_workspace import build_eo_bmf_workspace_layout
from .persistence import build_eo_bmf_nonprofit_persistence_service


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_EO_BMF_WORKERS = 4
DEFAULT_EO_BMF_BATCH_SIZE = 500


@dataclass(frozen=True)
class EoBmfRunConfig:
    strict: bool = False
    keep_temp: bool = False
    workspace: str | None = None
    workers: int = 1
    batch_size: int = DEFAULT_EO_BMF_BATCH_SIZE
    log_level: str = DEFAULT_LOG_LEVEL
    log_stack_traces: bool | None = None


@dataclass(frozen=True)
class _EoBmfProgressEvent:
    type: str
    filename: str
    total_rows: int = 0
    processed: int = 0
    invalid: int = 0
    completed_items: int = 0
    last_item: str | None = None


class _AggregateEoBmfProgressCoordinator:
    def __init__(self, *, progress_session: ProgressSession) -> None:
        self._progress_session = progress_session
        self._event_queue: queue.Queue[_EoBmfProgressEvent | None] = queue.Queue()
        self._stop_requested = threading.Event()
        self._thread = threading.Thread(target=self._run, name="eo-bmf-progress", daemon=True)
        self._totals_by_file: dict[str, int] = {}
        self._completed_by_file: dict[str, int] = {}

    def start(self) -> None:
        self._thread.start()

    def emit(self, event: Mapping[str, Any]) -> None:
        self._event_queue.put(
            _EoBmfProgressEvent(
                type=str(event.get("type") or "").strip(),
                filename=str(event.get("filename") or "").strip(),
                total_rows=int(event.get("total_rows") or 0),
                processed=int(event.get("processed") or 0),
                invalid=int(event.get("invalid") or 0),
                completed_items=int(event.get("completed_items") or 0),
                last_item=str(event.get("last_item") or "").strip() or None,
            )
        )

    def stop(self) -> None:
        self._stop_requested.set()
        self._event_queue.put(None)
        self._thread.join()

    def file_failed(self, filename: str) -> None:
        normalized = str(filename or "").strip()
        if not normalized:
            return
        remaining_rows = max(0, self._totals_by_file.get(normalized, 0) - self._completed_by_file.get(normalized, 0))
        self._completed_by_file[normalized] = self._completed_by_file.get(normalized, 0) + remaining_rows
        self._progress_session.item_completed(
            {"failed_files": 1},
            last_item=normalized,
            completed_items=remaining_rows,
        )

    def _run(self) -> None:
        while not self._stop_requested.is_set() or not self._event_queue.empty():
            try:
                event = self._event_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if event is None:
                continue
            self._handle(event)

    def _handle(self, event: _EoBmfProgressEvent) -> None:
        if event.type == "rows_total":
            self._totals_by_file[event.filename] = max(0, int(event.total_rows))
            self._progress_session.set_total_items(sum(self._totals_by_file.values()))
            return
        if event.type != "row_progress":
            return
        self._completed_by_file[event.filename] = self._completed_by_file.get(event.filename, 0) + max(
            0, int(event.completed_items)
        )
        increments = {}
        if event.processed:
            increments["processed"] = int(event.processed)
        if event.invalid:
            increments["invalid"] = int(event.invalid)
        self._progress_session.item_completed(
            increments,
            last_item=event.last_item,
            completed_items=max(0, int(event.completed_items)),
        )


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
        prepare_stream_for_external_write()
        print(json.dumps(payload, sort_keys=True))


def resolve_eo_bmf_runtime_environment_aliases(env: Mapping[str, str] | None = None) -> dict[str, str]:
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

    if not str(resolved.get("EOBMF_WORKSPACE_DIR") or "").strip():
        workspace_path = str(source_env.get("WORKSPACE_PATH") or "").strip()
        if workspace_path:
            resolved["EOBMF_WORKSPACE_DIR"] = workspace_path

    resolved.setdefault("PLATFORM_NONPROFIT_STORE_BACKEND", "postgres")
    return resolved


def build_eo_bmf_run_config(
    *,
    env: Mapping[str, str] | None = None,
    strict: bool | None = None,
    keep_temp: bool | None = None,
    workspace: str | None = None,
    workers: int | None = None,
    batch_size: int | None = None,
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
        workers=_resolve_eo_bmf_workers(source_env, override=workers),
        batch_size=_resolve_eo_bmf_batch_size(source_env, override=batch_size),
        log_level=resolved_log_level,
        log_stack_traces=_env_optional_bool(source_env, "LOG_STACK_TRACES"),
    )


def run_local_eo_bmf_ingest(
    *,
    strict: bool,
    keep_temp: bool,
    workspace: str | None,
    workers: int | None = None,
    batch_size: int | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    config = build_eo_bmf_run_config(
        env=env,
        strict=strict,
        keep_temp=keep_temp,
        workspace=workspace,
        workers=workers,
        batch_size=batch_size,
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
    persistence_service = build_eo_bmf_nonprofit_persistence_service(env=source_env)
    if persistence_service is None:
        logger.log(
            component="eo_bmf.cli",
            level="ERROR",
            message="postgres nonprofit persistence service could not be built",
        )
        return 1

    layout = build_eo_bmf_workspace_layout(
        {**source_env, **({"EOBMF_WORKSPACE_DIR": config.workspace} if config.workspace else {})}
    ).ensure()
    progress_reporter = build_progress_reporter()
    multi_worker = max(1, int(config.workers or 1)) > 1
    progress_session = progress_reporter.start(
        total_items=0 if multi_worker else len(IRS_FILES),
        fields=[
            ProgressField(key="processed", label="processed", color="green"),
            *([ProgressField(key="invalid", label="invalid", color="red")] if multi_worker else []),
            ProgressField(key="failed_files" if multi_worker else "failed", label="failed" if not multi_worker else "failed_files", color="red"),
        ],
        update_every=1,
    )
    progress_coordinator = _AggregateEoBmfProgressCoordinator(progress_session=progress_session) if multi_worker else None
    if progress_coordinator is not None:
        progress_coordinator.start()
    logger.log(
        component="eo_bmf.cli",
        level="INFO",
        message="local eo_bmf ingest starting",
        extra={
            "workspace_root": str(layout.root),
            "workers": config.workers,
            "batch_size": config.batch_size,
        },
    )

    run_started_at = time.perf_counter()
    files: list[dict[str, Any]] = []
    rows_seen = 0
    nonprofits_upserted = 0
    filings_upserted = 0
    invalid_rows = 0
    failure_count = 0

    try:
        with ThreadPoolExecutor(
            max_workers=max(1, int(config.workers or 1)),
            thread_name_prefix="eo-bmf-file",
        ) as executor:
            future_to_filename = {}
            for filename in IRS_FILES:
                logger.log(
                    component="eo_bmf.file",
                    level="INFO",
                    message="processing file",
                    file_name=filename,
                    extra={"source_url": source_url_for(filename)},
                )
                future_to_filename[
                    executor.submit(
                    _process_eo_bmf_file,
                    filename=filename,
                    workspace_root=str(layout.root),
                    env=source_env,
                    batch_size=config.batch_size,
                    keep_temp=config.keep_temp,
                    enable_record_progress=not multi_worker,
                    progress_callback=progress_coordinator.emit if progress_coordinator is not None else None,
                    )
                ] = filename
            for future in as_completed(future_to_filename):
                filename = future_to_filename[future]
                try:
                    file_payload = future.result()
                    rows_seen += int(file_payload.get("rows_seen") or 0)
                    nonprofits_upserted += int(file_payload.get("nonprofits_upserted") or 0)
                    filings_upserted += int(file_payload.get("filings_upserted") or 0)
                    invalid_rows += int(file_payload.get("invalid_rows") or 0)
                    files.append(file_payload)
                    if file_payload.get("status") == "failed":
                        failure_count += 1
                        if progress_coordinator is not None:
                            progress_coordinator.file_failed(filename)
                        else:
                            progress_session.item_completed({"failed": 1}, last_item=filename)
                        logger.log(
                            component="eo_bmf.file",
                            level="ERROR",
                            message="file processing failed",
                            file_name=filename,
                            extra=file_payload,
                        )
                        if config.strict:
                            raise RuntimeError(f"eo_bmf file failed: {filename}")
                    else:
                        if progress_coordinator is None:
                            progress_session.item_completed({"processed": 1}, last_item=filename)
                        logger.log(
                            component="eo_bmf.file",
                            level="INFO",
                            message="file processed",
                            file_name=filename,
                            extra=file_payload,
                        )
                except Exception as exc:
                    failure_count += 1
                    files.append(_failed_file_payload(filename=filename, total_file_duration_ms=0, error=exc))
                    if progress_coordinator is not None:
                        progress_coordinator.file_failed(filename)
                    else:
                        progress_session.item_completed({"failed": 1}, last_item=filename)
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
        if progress_coordinator is not None:
            progress_coordinator.stop()
        progress_session.complete()

    files.sort(key=lambda item: str(item.get("filename") or ""))
    status = _result_status(files)
    total_run_duration_ms = _elapsed_ms(run_started_at)
    logger.log(
        component="eo_bmf.cli",
        level="INFO",
        message="local eo_bmf ingest completed",
        extra={
            "status": status,
            "files_processed": len(files),
            "total_run_duration_ms": total_run_duration_ms,
            "files_per_second": _items_per_second(len(files), total_run_duration_ms),
            "rows_seen": rows_seen,
            "nonprofits_upserted": nonprofits_upserted,
            "filings_upserted": filings_upserted,
            "invalid_rows": invalid_rows,
            "rows_per_second": _items_per_second(rows_seen, total_run_duration_ms),
            "nonprofit_upserts_per_second": _items_per_second(nonprofits_upserted, total_run_duration_ms),
            "filing_upserts_per_second": _items_per_second(filings_upserted, total_run_duration_ms),
            "invalid_row_rate": _ratio(invalid_rows, rows_seen),
        },
    )
    prepare_stream_for_external_write()
    print(
        json.dumps(
            {
                "status": status,
                "files_processed": len(files),
                "total_run_duration_ms": total_run_duration_ms,
                "workers": config.workers,
                "batch_size": config.batch_size,
                "files_per_second": _items_per_second(len(files), total_run_duration_ms),
                "rows_seen": rows_seen,
                "nonprofits_upserted": nonprofits_upserted,
                "filings_upserted": filings_upserted,
                "invalid_rows": invalid_rows,
                "rows_per_second": _items_per_second(rows_seen, total_run_duration_ms),
                "nonprofit_upserts_per_second": _items_per_second(nonprofits_upserted, total_run_duration_ms),
                "filing_upserts_per_second": _items_per_second(filings_upserted, total_run_duration_ms),
                "invalid_row_rate": _ratio(invalid_rows, rows_seen),
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


def _process_eo_bmf_file(
    *,
    filename: str,
    workspace_root: str,
    env: Mapping[str, str],
    batch_size: int,
    keep_temp: bool,
    enable_record_progress: bool,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    layout = build_eo_bmf_workspace_layout({**env, "EOBMF_WORKSPACE_DIR": workspace_root}).ensure()
    file_workspace = layout.for_filename(filename).ensure()
    file_started_at = time.perf_counter()
    try:
        url = source_url_for(filename)
        download_started_at = time.perf_counter()
        _download_file_to_path(
            url=url,
            destination=file_workspace.download_path,
            timeout_seconds=int(env.get("EO_BMF_DOWNLOAD_TIMEOUT_SECONDS") or "300"),
        )
        download_duration_ms = _elapsed_ms(download_started_at)
        persistence_service = build_eo_bmf_nonprofit_persistence_service(env=env)
        if persistence_service is None:
            raise RuntimeError("postgres nonprofit persistence service could not be built")
        stats = ingest_eo_bmf_csv(
            path=str(file_workspace.download_path),
            filename=filename,
            persistence_service=persistence_service,
            batch_size=batch_size,
            progress_reporter=build_progress_reporter() if enable_record_progress else None,
            progress_callback=progress_callback,
        )
        return {
            **stats.to_dict(),
            "download_duration_ms": download_duration_ms,
            "total_file_duration_ms": _elapsed_ms(file_started_at),
        }
    except Exception as exc:
        return _failed_file_payload(
            filename=filename,
            total_file_duration_ms=_elapsed_ms(file_started_at),
            error=exc,
        )
    finally:
        if not keep_temp:
            file_workspace.finalize_processed_file()


def _failed_file_payload(*, filename: str, total_file_duration_ms: int, error: Exception) -> dict[str, Any]:
    return {
        "filename": filename,
        "status": "failed",
        "rows_seen": 0,
        "nonprofits_upserted": 0,
        "filings_upserted": 0,
        "invalid_rows": 0,
        "map_duration_ms": 0,
        "nonprofit_upsert_duration_ms": 0,
        "filing_upsert_duration_ms": 0,
        "db_upsert_duration_ms": 0,
        "download_duration_ms": 0,
        "total_file_duration_ms": total_file_duration_ms,
        "rows_per_second": 0.0,
        "nonprofit_upserts_per_second": 0.0,
        "filing_upserts_per_second": 0.0,
        "invalid_row_rate": 0.0,
        "db_time_share": 0.0,
        "error": str(error),
    }


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


def _elapsed_ms(started_at: float) -> int:
    return max(0, int(round((time.perf_counter() - started_at) * 1000)))


def _items_per_second(count: int, duration_ms: int) -> float:
    if count <= 0 or duration_ms <= 0:
        return 0.0
    return round(count / (duration_ms / 1000.0), 2)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


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


def _env_optional_int(source_env: Mapping[str, str], key: str) -> int | None:
    raw = source_env.get(key)
    if raw is None or str(raw).strip() == "":
        return None
    return int(str(raw).strip())


def _resolve_eo_bmf_workers(source_env: Mapping[str, str], *, override: int | None = None) -> int:
    if override is not None:
        return max(1, int(override))
    configured = _env_optional_int(source_env, "EO_BMF_WORKERS")
    if configured is not None:
        return max(1, int(configured))
    cpu_count = os.cpu_count() or DEFAULT_MAX_EO_BMF_WORKERS
    return max(1, min(len(IRS_FILES), min(cpu_count, DEFAULT_MAX_EO_BMF_WORKERS)))


def _resolve_eo_bmf_batch_size(source_env: Mapping[str, str], *, override: int | None = None) -> int:
    if override is not None:
        return max(1, int(override))
    configured = _env_optional_int(source_env, "EO_BMF_BATCH_SIZE")
    if configured is not None:
        return max(1, int(configured))
    return DEFAULT_EO_BMF_BATCH_SIZE


__all__ = [
    "EoBmfRunConfig",
    "build_eo_bmf_run_config",
    "resolve_eo_bmf_runtime_environment_aliases",
    "run_local_eo_bmf_ingest",
    "run_local_eo_bmf_ingest_config",
]

