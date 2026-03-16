from __future__ import annotations

from enum import Enum


class StateRegistrySourceType(str, Enum):
    SEARCH_PORTAL = "search_portal"
    BULK_DATASET = "bulk_dataset"
    API = "api"


class StateRegistryEntityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISSOLVED = "dissolved"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class StateRegistryStanding(str, Enum):
    GOOD_STANDING = "good_standing"
    NOT_IN_GOOD_STANDING = "not_in_good_standing"
    UNKNOWN = "unknown"


class MatchConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
