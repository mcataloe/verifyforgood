"""Shared CLI helpers for scaffolded backend runtimes."""

from __future__ import annotations


def scaffold_only_message(*, runtime_name: str, current_source: str, target_directory: str) -> str:
    return (
        f"The backend {runtime_name} runtime is scaffolded only in this phase. "
        f"Live runtime behavior still runs from {current_source}. "
        f"Use {target_directory} as the runtime home for future extraction work."
    )
