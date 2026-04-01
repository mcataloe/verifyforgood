"""Backend API runtime package."""

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

from .app import app, create_app
from .runtime import handle_api_event, handler

__all__ = [
    "RUNTIME_NAME",
    "CURRENT_COMPATIBILITY_SOURCE",
    "app",
    "create_app",
    "handle_api_event",
    "handler",
]
