from .contracts import RawStateRegistryRecord, StateRegistryAdapter
from .enums import MatchConfidence, StateRegistryEntityStatus, StateRegistrySourceType, StateRegistryStanding
from .errors import (
    StateRegistryAdapterOperationNotSupportedError,
    StateRegistryAdapterRegistrationError,
    StateRegistryError,
    StateRegistryLookupFailedError,
    UnsupportedStateRegistryError,
)
from .matching import NameMatchResult, classify_name_match
from .models import (
    RawPayloadRef,
    StateRegistryLookupRequest,
    StateRegistryRecord,
)
from .normalization import (
    normalize_entity_name,
    normalize_entity_status,
    normalize_match_confidence,
    normalize_standing,
    normalize_state_code,
    stable_payload_hash,
)
from .registry import StateRegistryAdapterRegistry, build_state_registry_adapter_registry
from .repository import (
    InMemoryStateRegistryRecordRepository,
    NoopStateRegistryRecordRepository,
    StateRegistryRecordRepository,
    build_state_registry_record_item,
)
from .service import StateRegistryLookupFailure, StateRegistryLookupOutcome, StateRegistryLookupService
from .traceability import build_raw_payload_ref, now_utc_iso

__all__ = [
    "RawStateRegistryRecord",
    "StateRegistryAdapter",
    "StateRegistryError",
    "UnsupportedStateRegistryError",
    "StateRegistryAdapterRegistrationError",
    "StateRegistryAdapterOperationNotSupportedError",
    "StateRegistryLookupFailedError",
    "StateRegistrySourceType",
    "StateRegistryEntityStatus",
    "StateRegistryStanding",
    "MatchConfidence",
    "RawPayloadRef",
    "StateRegistryLookupRequest",
    "StateRegistryRecord",
    "normalize_state_code",
    "normalize_entity_name",
    "normalize_entity_status",
    "normalize_standing",
    "normalize_match_confidence",
    "stable_payload_hash",
    "build_raw_payload_ref",
    "now_utc_iso",
    "NameMatchResult",
    "classify_name_match",
    "StateRegistryAdapterRegistry",
    "build_state_registry_adapter_registry",
    "StateRegistryRecordRepository",
    "NoopStateRegistryRecordRepository",
    "InMemoryStateRegistryRecordRepository",
    "build_state_registry_record_item",
    "StateRegistryLookupFailure",
    "StateRegistryLookupOutcome",
    "StateRegistryLookupService",
]
