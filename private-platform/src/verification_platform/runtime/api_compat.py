"""Compatibility import root for the backend-owned API ASGI app."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
BACKEND_API_SRC = ROOT / "backend" / "api" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

for path in (BACKEND_API_SRC, BACKEND_SHARED_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from verification_backend.api.app import app, create_app  # noqa: E402
from verification_backend.api.transport import (  # noqa: E402
    API_ROUTE_SPECS,
    ApiRouteSpec,
    build_backend_request,
    runtime_response_to_http,
)


__all__ = [
    "app",
    "create_app",
    "API_ROUTE_SPECS",
    "ApiRouteSpec",
    "build_backend_request",
    "runtime_response_to_http",
]

