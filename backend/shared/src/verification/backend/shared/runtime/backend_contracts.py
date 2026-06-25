"""Shared backend transport contracts."""

from verification.backend.shared.api import (
    API_RELEASE,
    API_VERSION,
    API_VERSION_PREFIX,
    DeprecationMetadata,
    ResponseContext,
    build_response_context,
    error_response,
    json_response,
    normalize_route_key,
    strip_version_prefix,
    version_path,
)

__all__ = [
    "API_RELEASE",
    "API_VERSION",
    "API_VERSION_PREFIX",
    "DeprecationMetadata",
    "ResponseContext",
    "build_response_context",
    "error_response",
    "json_response",
    "normalize_route_key",
    "strip_version_prefix",
    "version_path",
]
