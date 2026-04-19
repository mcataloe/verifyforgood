from __future__ import annotations

API_VERSION = "v1"
API_RELEASE = "1.0.0"
API_VERSION_PREFIX = f"/{API_VERSION}"


def version_path(path: str) -> str:
    normalized = _normalize_path(path)
    if normalized == "/":
        return API_VERSION_PREFIX
    if normalized == API_VERSION_PREFIX or normalized.startswith(f"{API_VERSION_PREFIX}/"):
        return normalized
    return f"{API_VERSION_PREFIX}{normalized}"


def strip_version_prefix(path: str) -> str:
    normalized = _normalize_path(path)
    if normalized == API_VERSION_PREFIX:
        return "/"
    if normalized.startswith(f"{API_VERSION_PREFIX}/"):
        stripped = normalized[len(API_VERSION_PREFIX) :]
        return stripped or "/"
    return normalized


def normalize_route_key(route_key: str) -> str:
    candidate = str(route_key or "").strip()
    if not candidate or " " not in candidate:
        return candidate
    method, path = candidate.split(" ", 1)
    method = method.strip().upper()
    return f"{method} {version_path(path.strip())}"


def _normalize_path(path: str) -> str:
    candidate = f"/{str(path or '').strip('/')}"
    return candidate if candidate != "//" else "/"
