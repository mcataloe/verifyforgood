"""Cleanup helpers for deterministic Form 990 workspace lifecycle management."""

from __future__ import annotations

import shutil
from pathlib import Path


def remove_file_if_present(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()


def remove_tree_if_present(path: Path) -> None:
    if path.exists() and path.is_dir():
        shutil.rmtree(path)


__all__ = ["remove_file_if_present", "remove_tree_if_present"]
