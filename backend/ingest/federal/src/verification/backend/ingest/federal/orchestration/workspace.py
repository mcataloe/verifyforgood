"""Workspace layout helpers for local-first Form 990 ingest execution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Mapping

from ..cleanup import remove_file_if_present, remove_tree_if_present


FORM990_WORKSPACE_DIR_ENV = "FORM990_WORKSPACE_DIR"
FORM990_WORKSPACE_MAX_BYTES_ENV = "FORM990_WORKSPACE_MAX_BYTES"
DEFAULT_FORM990_WORKSPACE_MAX_BYTES = 32 * 1024 * 1024 * 1024


def resolve_workspace_root(
    env: Mapping[str, str] | None = None,
    *,
    default_root: Path | None = None,
) -> Path:
    values = env or os.environ
    configured = values.get(FORM990_WORKSPACE_DIR_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    if default_root is not None:
        return default_root.resolve()
    return (Path(tempfile.gettempdir()) / "charity-status" / "form990").resolve()


@dataclass(frozen=True)
class WorkspaceLayout:
    root: Path
    archives_dir: Path
    extracted_dir: Path
    logs_dir: Path
    state_dir: Path
    max_bytes: int = DEFAULT_FORM990_WORKSPACE_MAX_BYTES

    def ensure(self) -> "WorkspaceLayout":
        for path in (
            self.root,
            self.archives_dir,
            self.extracted_dir,
            self.logs_dir,
            self.state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def archive_path(self, archive_name: str) -> Path:
        return self.archives_dir / f"{archive_name}.zip"

    def extracted_archive_dir(self, archive_name: str) -> Path:
        return self.extracted_dir / archive_name

    def log_path(self, archive_name: str) -> Path:
        return self.logs_dir / f"{archive_name}.log"

    def state_path(self, archive_name: str) -> Path:
        return self.state_dir / f"{archive_name}.json"

    def for_archive(self, archive_name: str) -> "ArchiveWorkspace":
        return ArchiveWorkspace(
            layout=self,
            archive_name=archive_name,
            archive_path=self.archive_path(archive_name),
            extracted_dir=self.extracted_archive_dir(archive_name),
            log_path=self.log_path(archive_name),
            state_path=self.state_path(archive_name),
        )


@dataclass(frozen=True)
class ArchiveWorkspace:
    layout: WorkspaceLayout
    archive_name: str
    archive_path: Path
    extracted_dir: Path
    log_path: Path
    state_path: Path

    def ensure(self) -> "ArchiveWorkspace":
        self.layout.ensure()
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        return self

    def cleanup_extracted(self) -> None:
        remove_tree_if_present(self.extracted_dir)

    def cleanup_archive(self) -> None:
        remove_file_if_present(self.archive_path)

    def finalize_processed_archive(self) -> None:
        self.cleanup_extracted()
        self.cleanup_archive()


def build_workspace_layout(
    env: Mapping[str, str] | None = None,
    *,
    root: Path | None = None,
) -> WorkspaceLayout:
    values = env or os.environ
    workspace_root = root.resolve() if root is not None else resolve_workspace_root(values)
    raw_max_bytes = values.get(FORM990_WORKSPACE_MAX_BYTES_ENV)
    max_bytes = int(raw_max_bytes) if raw_max_bytes else DEFAULT_FORM990_WORKSPACE_MAX_BYTES
    return WorkspaceLayout(
        root=workspace_root,
        archives_dir=workspace_root / "archives",
        extracted_dir=workspace_root / "extracted",
        logs_dir=workspace_root / "logs",
        state_dir=workspace_root / "state",
        max_bytes=max_bytes,
    )


__all__ = [
    "DEFAULT_FORM990_WORKSPACE_MAX_BYTES",
    "FORM990_WORKSPACE_DIR_ENV",
    "FORM990_WORKSPACE_MAX_BYTES_ENV",
    "ArchiveWorkspace",
    "WorkspaceLayout",
    "build_workspace_layout",
    "resolve_workspace_root",
]
