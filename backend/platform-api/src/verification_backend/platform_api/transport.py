"""Backend HTTP transport helpers for the platform API runtime."""

from __future__ import annotations

from verification_backend.api.transport import (
    ApiRouteSpec,
    PLATFORM_API_ROUTE_SPECS,
    build_backend_request,
    runtime_response_to_http,
)


API_ROUTE_SPECS = PLATFORM_API_ROUTE_SPECS


__all__ = [
    "ApiRouteSpec",
    "API_ROUTE_SPECS",
    "build_backend_request",
    "runtime_response_to_http",
]
