"""Backend API runtime package."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[5]
INFRASTRUCTURE_SRC = ROOT / "infrastructure"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

for path in (INFRASTRUCTURE_SRC, PRIVATE_PLATFORM_SRC, BACKEND_SHARED_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


RUNTIME_NAME = "api"
CURRENT_COMPATIBILITY_SOURCE = "infrastructure.lambda_query.handler"

from .runtime import handle_api_event, handler


def create_app():
    from .app import create_app as _create_app

    return _create_app()


def __getattr__(name: str):
    if name == "app":
        from .app import app as _app

        return _app
    if name == "create_app":
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "RUNTIME_NAME",
    "CURRENT_COMPATIBILITY_SOURCE",
    "app",
    "create_app",
    "handle_api_event",
    "handler",
]
