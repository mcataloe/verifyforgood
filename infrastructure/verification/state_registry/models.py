from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from verification.state_registry.enums import MatchConfidence, StateRegistryEntityStatus, StateRegistrySourceType, StateRegistryStanding
from verification.state_registry.normalization import normalize_entity_name, normalize_entity_status, normalize_match_confidence, normalize_standing, normalize_state_code

@dataclass(frozen=True)
class RawPayloadRef:
    source_identifier: str
    retrieved_at: str
    raw_hash: str
    parser_version: str
    storage_locator: str | None = None

    def __post_init__(self) -> None:
        if not str(self.source_identifier or "").strip():
            raise ValueError("source_identifier is required")
        if not str(self.retrieved_at or "").strip():
            raise ValueError("retrieved_at is required")
        if not str(self.raw_hash or "").strip():
            raise ValueError("raw_hash is required")
        if not str(self.parser_version or "").strip():
            raise ValueError("parser_version is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_identifier": self.source_identifier,
            "retrieved_at": self.retrieved_at,
            "raw_hash": self.raw_hash,
            "parser_version": self.parser_version,
            "storage_locator": self.storage_locator,
        }


@dataclass(frozen=True)
class StateRegistryLookupRequest:
    organization_name: str
    state: str
    normalized_organization_name: str | None = None
    ein: str | None = None
    address_hint: str | None = None
    jurisdiction_hint: str | None = None
    city_hint: str | None = None
    postal_code_hint: str | None = None

    def __post_init__(self) -> None:
        organization_name = str(self.organization_name or "").strip()
        state = normalize_state_code(self.state)
        if not organization_name:
            raise ValueError("organization_name is required")
        if not state or len(state) != 2:
            raise ValueError("state must be a two-letter state code")
        object.__setattr__(self, "organization_name", organization_name)
        object.__setattr__(self, "state", state)
        object.__setattr__(
            self,
            "normalized_organization_name",
            normalize_entity_name(self.normalized_organization_name or organization_name),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_name": self.organization_name,
            "normalized_organization_name": self.normalized_organization_name,
            "state": self.state,
            "ein": self.ein,
            "address_hint": self.address_hint,
            "jurisdiction_hint": self.jurisdiction_hint,
            "city_hint": self.city_hint,
            "postal_code_hint": self.postal_code_hint,
        }


@dataclass(frozen=True)
class StateRegistryRecord:
    state_code: str
    source_name: str
    source_type: StateRegistrySourceType
    external_entity_id: str | None = None
    entity_name: str | None = None
    normalized_entity_name: str | None = None
    entity_type: str | None = None
    status: StateRegistryEntityStatus | None = None
    standing: StateRegistryStanding | None = None
    formation_date: str | None = None
    dissolution_date: str | None = None
    last_filing_date: str | None = None
    registry_url: str | None = None
    raw_fetched_at: str | None = None
    raw_hash: str | None = None
    parser_version: str | None = None
    matched_on: str | None = None
    confidence: MatchConfidence | None = None
    raw_payload_ref: RawPayloadRef | None = None

    def __post_init__(self) -> None:
        state_code = normalize_state_code(self.state_code)
        source_name = str(self.source_name or "").strip()
        if not state_code or len(state_code) != 2:
            raise ValueError("state_code must be a two-letter state code")
        if not source_name:
            raise ValueError("source_name is required")
        object.__setattr__(self, "state_code", state_code)
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "normalized_entity_name", normalize_entity_name(self.normalized_entity_name or self.entity_name))
        object.__setattr__(self, "status", self.status if isinstance(self.status, StateRegistryEntityStatus) or self.status is None else normalize_entity_status(self.status))
        object.__setattr__(self, "standing", self.standing if isinstance(self.standing, StateRegistryStanding) or self.standing is None else normalize_standing(self.standing))
        object.__setattr__(self, "confidence", self.confidence if isinstance(self.confidence, MatchConfidence) or self.confidence is None else normalize_match_confidence(self.confidence))
        if self.raw_payload_ref is not None:
            object.__setattr__(self, "raw_fetched_at", self.raw_fetched_at or self.raw_payload_ref.retrieved_at)
            object.__setattr__(self, "raw_hash", self.raw_hash or self.raw_payload_ref.raw_hash)
            object.__setattr__(self, "parser_version", self.parser_version or self.raw_payload_ref.parser_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_code": self.state_code,
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "external_entity_id": self.external_entity_id,
            "entity_name": self.entity_name,
            "normalized_entity_name": self.normalized_entity_name,
            "entity_type": self.entity_type,
            "status": self.status.value if self.status else None,
            "standing": self.standing.value if self.standing else None,
            "formation_date": self.formation_date,
            "dissolution_date": self.dissolution_date,
            "last_filing_date": self.last_filing_date,
            "registry_url": self.registry_url,
            "raw_fetched_at": self.raw_fetched_at,
            "raw_hash": self.raw_hash,
            "parser_version": self.parser_version,
            "matched_on": self.matched_on,
            "confidence": self.confidence.value if self.confidence else None,
            "raw_payload_ref": self.raw_payload_ref.to_dict() if self.raw_payload_ref else None,
        }

