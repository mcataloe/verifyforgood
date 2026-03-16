from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from charity_status.state_registry.enums import MatchConfidence, StateRegistryEntityStatus, StateRegistryStanding

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9 ]+")

_ACTIVE_STATUS_VALUES = {
    "ACTIVE",
    "GOOD STANDING",
    "EXISTING",
    "REGISTERED",
    "IN GOOD STANDING",
}
_INACTIVE_STATUS_VALUES = {
    "INACTIVE",
    "FORFEITED",
    "WITHDRAWN",
    "MERGED",
    "CANCELLED",
}
_DISSOLVED_STATUS_VALUES = {
    "DISSOLVED",
    "ADMINISTRATIVELY DISSOLVED",
    "VOLUNTARILY DISSOLVED",
}
_REVOKED_STATUS_VALUES = {
    "REVOKED",
    "VOID",
}
_SUSPENDED_STATUS_VALUES = {
    "SUSPENDED",
    "NOT IN GOOD STANDING",
    "DELINQUENT",
}

_GOOD_STANDING_VALUES = {
    "GOOD STANDING",
    "IN GOOD STANDING",
    "GOOD",
    "ACTIVE",
}
_NOT_GOOD_STANDING_VALUES = {
    "NOT IN GOOD STANDING",
    "DELINQUENT",
    "INACTIVE",
    "SUSPENDED",
    "REVOKED",
    "BAD",
}


def normalize_state_code(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    if not cleaned:
        return None
    return cleaned


def normalize_entity_name(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    if not cleaned:
        return None
    cleaned = _NON_ALNUM_RE.sub(" ", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned or None


def normalize_entity_status(value: object | None) -> StateRegistryEntityStatus | None:
    normalized = normalize_entity_name(value)
    if not normalized:
        return None
    if normalized in _ACTIVE_STATUS_VALUES:
        return StateRegistryEntityStatus.ACTIVE
    if normalized in _DISSOLVED_STATUS_VALUES:
        return StateRegistryEntityStatus.DISSOLVED
    if normalized in _REVOKED_STATUS_VALUES:
        return StateRegistryEntityStatus.REVOKED
    if normalized in _SUSPENDED_STATUS_VALUES:
        return StateRegistryEntityStatus.SUSPENDED
    if normalized in _INACTIVE_STATUS_VALUES:
        return StateRegistryEntityStatus.INACTIVE
    return StateRegistryEntityStatus.UNKNOWN


def normalize_standing(value: object | None) -> StateRegistryStanding | None:
    normalized = normalize_entity_name(value)
    if not normalized:
        return None
    if normalized in _GOOD_STANDING_VALUES:
        return StateRegistryStanding.GOOD_STANDING
    if normalized in _NOT_GOOD_STANDING_VALUES:
        return StateRegistryStanding.NOT_IN_GOOD_STANDING
    return StateRegistryStanding.UNKNOWN


def normalize_match_confidence(value: object | None) -> MatchConfidence | None:
    normalized = normalize_entity_name(value)
    if not normalized:
        return None
    if normalized == "HIGH":
        return MatchConfidence.HIGH
    if normalized == "MEDIUM":
        return MatchConfidence.MEDIUM
    if normalized == "LOW":
        return MatchConfidence.LOW
    return None


def stable_payload_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
