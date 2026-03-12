from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from charity_status.enrichments.base import EnrichmentProvider, ProviderError
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from charity_status.sources import ProviderCapability, SourceCategory


class StateRegistryAdapter(ABC):
    @abstractmethod
    def lookup(self, ein: str, organization_name: str | None = None) -> dict[str, Any] | None:
        raise NotImplementedError


class StateRegistryProvider(EnrichmentProvider):
    def __init__(self, enabled: bool, adapter: StateRegistryAdapter | None = None) -> None:
        self._enabled = enabled
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "state_registry"

    def is_enabled(self) -> bool:
        return self._enabled and self._adapter is not None

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.COMPLIANCE], source_ids=["state_registry.compliance"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()

        fetched_at = now_utc_iso()
        try:
            raw = self._adapter.lookup(ein=ein, organization_name=organization_name)
        except Exception as exc:
            raise ProviderError(f"State registry lookup failed: {exc}") from exc

        fields = self._normalize(raw or {})
        status = EnrichmentStatus.MATCHED if fields else EnrichmentStatus.NO_MATCH
        return EnrichmentProviderResult(
            name=self.name,
            status=status,
            provider_record_id=(raw or {}).get("record_id") if isinstance(raw, dict) else None,
            fetched_at=fetched_at,
            fields=fields,
            source_payload=raw if isinstance(raw, dict) else None,
            source={
                "record_id": (raw or {}).get("record_id") if isinstance(raw, dict) else None,
                "fetched_at": fetched_at,
                "licensed": True,
                "notes": "State registry provider scaffold via adapter pattern",
            },
            source_records=(
                [
                    self.build_normalized_source_record(
                        ein=ein,
                        source_id="state_registry.compliance",
                        category=SourceCategory.COMPLIANCE,
                        description="State registry compliance source",
                        fetched_at=fetched_at,
                        fields=fields,
                        record_id=(raw or {}).get("record_id") if isinstance(raw, dict) else None,
                        expires_at=fields.get("registration_expiration_date"),
                    )
                ]
                if fields
                else []
            ),
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )

    @staticmethod
    def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "registration_status": payload.get("registration_status"),
            "registration_jurisdiction": payload.get("registration_jurisdiction"),
            "registration_expiration_date": payload.get("registration_expiration_date"),
            "solicitation_permitted": payload.get("solicitation_permitted"),
            "compliance_flags": payload.get("compliance_flags") or [],
        }
