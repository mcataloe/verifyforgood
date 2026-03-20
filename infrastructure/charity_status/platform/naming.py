from __future__ import annotations

import re

DEFAULT_NAMESPACE = "n8x4"
DEFAULT_PLATFORM = "verification"
DEFAULT_REGION = "use1"
_RESOURCE_NAME_PATTERN = re.compile(r"^(?!\d+\.\d+\.\d+\.\d+$)[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$")
_TOKEN_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def build_resource_name(
    *,
    purpose: str,
    environment: str,
    namespace: str = DEFAULT_NAMESPACE,
    platform: str = DEFAULT_PLATFORM,
    region: str = DEFAULT_REGION,
) -> str:
    parts = {
        "namespace": namespace,
        "platform": platform,
        "purpose": purpose,
        "environment": environment,
        "region": region,
    }
    normalized = [_validate_part(name, value) for name, value in parts.items()]
    resource_name = "-".join(normalized)
    if not validate_resource_name(resource_name):
        raise ValueError(
            "resource name must be lowercase, hyphen-separated, start and end with an alphanumeric character, "
            "and remain within S3-compatible length constraints"
        )
    return resource_name


def validate_resource_name(name: str) -> bool:
    if not isinstance(name, str):
        return False
    return bool(_RESOURCE_NAME_PATTERN.fullmatch(name))


def _validate_part(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a non-empty lowercase string")
    candidate = value.strip()
    if not candidate:
        raise ValueError(f"{name} must be provided")
    if not _TOKEN_PATTERN.fullmatch(candidate):
        raise ValueError(
            f"{name} must contain only lowercase letters, numbers, and internal hyphens without leading or trailing hyphens"
        )
    return candidate


buildResourceName = build_resource_name
validateResourceName = validate_resource_name

__all__ = [
    "DEFAULT_NAMESPACE",
    "DEFAULT_PLATFORM",
    "DEFAULT_REGION",
    "build_resource_name",
    "validate_resource_name",
    "buildResourceName",
    "validateResourceName",
]
