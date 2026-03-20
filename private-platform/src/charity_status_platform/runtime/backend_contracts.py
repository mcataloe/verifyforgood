"""Private-platform compatibility exports for shared backend transport contracts.

These contracts still live in the current ``charity_status.api`` package during
the monorepo transition. This module gives future private-platform entrypoints,
portal backends, and internal controllers a stable import root without changing
live runtime behavior yet.
"""

from charity_status.api import (
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
