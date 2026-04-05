"""Workspace layout helpers for local-first EO/BMF ingest execution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
from typing import Mapping

from ..cleanup import remove_file_if_present, remove_tree_if_present


EOBMF_WORKSPACE_DIR_ENV = "EOBMF_WORKSPACE_DIR"
EOBMF_WORKSPACE_MAX_BYTES_ENV = "EOBMF_WORKSPACE_MAX_BYTES"
DEFAULT_EOBMF_WORKSPACE_MAX_BYTES = 2 * 1024 * 1024 * 1024


def resolve_eo_bmf_workspace_root(
    env: Mapping[str, str] | None = None,
    *,
    default_root: Path | None = None,
) -> Path:
    values = env or os.environ
    configured = values.get(EOBMF_WORKSPACE_DIR_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    if default_root is not None:
        return default_root.resolve()
    return (Path(tempfile.gettempdir()) / "charity-status" / "eo_bmf").resolve()


@dataclass(frozen=True)
class EoBmfWorkspaceLayout:
    root: Path
    downloads_dir: Path
    logs_dir: Path
    state_dir: Path
    max_bytes: int = DEFAULT_EOBMF_WORKSPACE_MAX_BYTES

    def ensure(self) -> "EoBmfWorkspaceLayout":
        for path in (self.root, self.downloads_dir, self.logs_dir, self.state_dir):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def download_path(self, filename: str) -> Path:
        return self.downloads_dir / filename

    def log_path(self, filename: str) -> Path:
        return self.logs_dir / f"{filename}.log"

    def state_path(self, filename: str) -> Path:
        return self.state_dir / f"{filename}.json"

    def for_filename(self, filename: str) -> "EoBmfFileWorkspace":
        return EoBmfFileWorkspace(
            layout=self,
            filename=filename,
            download_path=self.download_path(filename),
            log_path=self.log_path(filename),
            state_path=self.state_path(filename),
        )


@dataclass(frozen=True)
class EoBmfFileWorkspace:
    layout: EoBmfWorkspaceLayout
    filename: str
    download_path: Path
    log_path: Path
    state_path: Path

    def ensure(self) -> "EoBmfFileWorkspace":
        self.layout.ensure()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        return self

    def cleanup_download(self) -> None:
        remove_file_if_present(self.download_path)

    def cleanup_state(self) -> None:
        remove_file_if_present(self.state_path)

    def finalize_processed_file(self) -> None:
        self.cleanup_download()
        self.cleanup_state()


def build_eo_bmf_workspace_layout(
    env: Mapping[str, str] | None = None,
    *,
    root: Path | None = None,
) -> EoBmfWorkspaceLayout:
    values = env or os.environ
    workspace_root = root.resolve() if root is not None else resolve_eo_bmf_workspace_root(values)
    raw_max_bytes = values.get(EOBMF_WORKSPACE_MAX_BYTES_ENV)
    max_bytes = int(raw_max_bytes) if raw_max_bytes else DEFAULT_EOBMF_WORKSPACE_MAX_BYTES
    return EoBmfWorkspaceLayout(
        root=workspace_root,
        downloads_dir=workspace_root / "downloads",
        logs_dir=workspace_root / "logs",
        state_dir=workspace_root / "state",
        max_bytes=max_bytes,
    )


__all__ = [
    "DEFAULT_EOBMF_WORKSPACE_MAX_BYTES",
    "EOBMF_WORKSPACE_DIR_ENV",
    "EOBMF_WORKSPACE_MAX_BYTES_ENV",
    "EoBmfFileWorkspace",
    "EoBmfWorkspaceLayout",
    "build_eo_bmf_workspace_layout",
    "resolve_eo_bmf_workspace_root",
]
